# -*- coding: utf-8 -*-
import sys
import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst, GLib

import pyds
from loguru import logger
import time
import os
import ctypes
import numpy as np

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "backend")
    )
)

from app.engine.engine import DetectionEngine
from app.engine.base import FrameData, NormalizedDetection
from message_broker import DeepStreamMessageBroker


class DeepStreamPipeline:
    def __init__(self, yolo_config_path, face_config_path):
        import redis
        self.yolo_config_path = yolo_config_path
        self.face_config_path = face_config_path
        self.detection_engine = DetectionEngine()
        self.redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

        Gst.init(None)

        self.pipeline = Gst.Pipeline()
        self.streammux = None
        self.demux = None

        self.sources = {}
        self.output_bins = {}
        self.camera_to_source = {}

        self.max_cameras = int(os.getenv("MAX_CAMERAS", "30"))
        self.available_source_ids = list(range(self.max_cameras))

        self.broker = DeepStreamMessageBroker(
            self.add_camera,
            self.remove_camera
        )

        self._build_pipeline()

    def _build_pipeline(self):
        logger.info(
            f"Building Core DeepStream Pipeline "
            f"(Capacity: {self.max_cameras} streams) with Face SGIE..."
        )

        self.streammux = Gst.ElementFactory.make(
            "nvstreammux",
            "Stream-muxer"
        )
        if not self.streammux:
            raise RuntimeError("Failed to create nvstreammux")

        self.streammux.set_property("width", 1280)
        self.streammux.set_property("height", 720)
        self.streammux.set_property("batch-size", self.max_cameras)
        self.streammux.set_property("batched-push-timeout", 33000)
        self.streammux.set_property("live-source", 1)

        self.pipeline.add(self.streammux)

        pgie = Gst.ElementFactory.make(
            "nvinfer",
            "primary-inference"
        )
        if not pgie:
            raise RuntimeError("Failed to create primary nvinfer")

        pgie.set_property(
            "config-file-path",
            self.yolo_config_path
        )

        tracker = Gst.ElementFactory.make(
            "nvtracker",
            "tracker"
        )
        if not tracker:
            raise RuntimeError("Failed to create nvtracker")

        tracker_lib = (
            "/opt/nvidia/deepstream/deepstream/lib/"
            "libnvds_nvmultiobjecttracker.so"
        )

        tracker_cfg = (
            "config_tracker.yml"
            if os.path.exists("config_tracker.yml")
            else (
                "/opt/nvidia/deepstream/deepstream/samples/"
                "configs/deepstream-app/config_tracker_NvSORT.yml"
            )
        )

        tracker.set_property("ll-lib-file", tracker_lib)
        tracker.set_property("ll-config-file", tracker_cfg)
        tracker.set_property("tracker-width", 640)
        tracker.set_property("tracker-height", 384)
        tracker.set_property("gpu-id", 0)

        sgie = Gst.ElementFactory.make(
            "nvinfer",
            "secondary-inference-face"
        )
        if not sgie:
            raise RuntimeError("Failed to create secondary nvinfer")

        sgie.set_property(
            "config-file-path",
            self.face_config_path
        )

        nvvidconv1 = Gst.ElementFactory.make(
            "nvvideoconvert",
            "convertor1"
        )
        nvosd = Gst.ElementFactory.make(
            "nvdsosd",
            "onscreendisplay"
        )

        if not nvvidconv1 or not nvosd:
            raise RuntimeError("Failed to create video processing elements")

        nvosd.set_property("display-bbox", 0)
        nvosd.set_property("display-text", 0)

        tee = Gst.ElementFactory.make(
            "tee",
            "output-tee"
        )
        queue_fake = Gst.ElementFactory.make(
            "queue",
            "fake-queue"
        )
        fakesink = Gst.ElementFactory.make(
            "fakesink",
            "fake-sink"
        )

        queue_demux = Gst.ElementFactory.make(
            "queue",
            "demux-queue"
        )
        self.demux = Gst.ElementFactory.make(
            "nvstreamdemux",
            "stream-demuxer"
        )

        if not all([
            tee,
            queue_fake,
            fakesink,
            queue_demux,
            self.demux
        ]):
            raise RuntimeError("Failed to create output elements")

        fakesink.set_property("sync", False)
        fakesink.set_property("async", False)

        queue_demux.set_property("max-size-buffers", 2)
        queue_demux.set_property("leaky", 2)

        for element in [
            pgie,
            tracker,
            nvvidconv1,
            nvosd,
            tee,
            queue_fake,
            fakesink,
            queue_demux,
            self.demux
        ]:
            self.pipeline.add(element)

        if not self.streammux.link(pgie):
            raise RuntimeError("Failed to link streammux -> pgie")

        if not pgie.link(tracker):
            raise RuntimeError("Failed to link pgie -> tracker")

        if not tracker.link(nvvidconv1):
            raise RuntimeError("Failed to link tracker -> nvvideoconvert")

        if not nvvidconv1.link(nvosd):
            raise RuntimeError("Failed to link nvvideoconvert -> nvdsosd")

        if not nvosd.link(tee):
            raise RuntimeError("Failed to link nvdsosd -> tee")

        if not tee.link(queue_fake):
            raise RuntimeError("Failed to link tee -> fake queue")

        if not queue_fake.link(fakesink):
            raise RuntimeError("Failed to link fake queue -> fakesink")

        if not tee.link(queue_demux):
            raise RuntimeError("Failed to link tee -> demux queue")

        if not queue_demux.link(self.demux):
            raise RuntimeError("Failed to link demux queue -> nvstreamdemux")

        self.demux_pads = {}

        tmpl = self.demux.get_pad_template("src_%u")
        if not tmpl:
            raise RuntimeError("Failed to get nvstreamdemux src template")

        for i in range(self.max_cameras):
            pad = self.demux.request_pad(
                tmpl,
                f"src_{i}",
                None
            )
            if pad:
                self.demux_pads[i] = pad

        tracker_src_pad = tracker.get_static_pad("src")
        if not tracker_src_pad:
            raise RuntimeError("Failed to get Tracker src pad")

        tracker_src_pad.add_probe(
            Gst.PadProbeType.BUFFER,
            self._osd_sink_pad_buffer_probe,
            0
        )

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._bus_call)

    def _bus_call(self, bus, message):
        message_type = message.type

        if message_type == Gst.MessageType.EOS:
            logger.info(
                "End-of-stream reached. Looping playback to start..."
            )

            self.pipeline.seek_simple(
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                0
            )

        elif message_type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            src_name = message.src.get_name()

            logger.error(
                f"Error from {src_name}: "
                f"{err.message}"
            )

            if debug:
                logger.error(f"GStreamer debug: {debug}")

            # Isolate failed camera source bin so other cameras continue running uninterrupted
            for sid, (cam_id, s_uri) in list(self.sources.items()):
                if f"source-bin-{sid}" in src_name or f"uri-decode-bin-{sid}" in src_name or f"source_{sid}" in src_name:
                    logger.warning(f"Isolating disconnected camera source {cam_id} (source {sid})")
                    try:
                        GLib.idle_add(self.remove_camera, cam_id)
                    except Exception as e:
                        logger.error(f"Failed to remove disconnected camera {sid}: {e}")
                    break

        elif message_type == Gst.MessageType.WARNING:
            err, debug = message.parse_warning()

            logger.warning(
                f"Warning from {message.src.get_name()}: "
                f"{err.message}"
            )

            if debug:
                logger.warning(f"GStreamer debug: {debug}")

        return True

    def _create_source_bin(self, source_id, uri):
        bin_name = f"source-bin-{source_id}"

        nbin = Gst.Bin.new(bin_name)
        if not nbin:
            raise RuntimeError(
                f"Failed to create source bin {source_id}"
            )

        uri_decode_bin = Gst.ElementFactory.make(
            "uridecodebin",
            f"uri-decode-bin-{source_id}"
        )

        if not uri_decode_bin:
            raise RuntimeError(
                f"Failed to create uridecodebin {source_id}"
            )

        safe_uri = self._encode_rtsp_uri(uri)

        uri_decode_bin.set_property(
            "uri",
            safe_uri
        )

        uri_decode_bin.connect(
            "pad-added",
            self._cb_newpad,
            nbin
        )

        uri_decode_bin.connect(
            "child-added",
            self._cb_child_added,
            nbin
        )

        nbin.add(uri_decode_bin)

        bin_pad = Gst.GhostPad.new_no_target(
            "src",
            Gst.PadDirection.SRC
        )

        nbin.add_pad(bin_pad)

        return nbin

    def _cb_child_added(
        self,
        child_proxy,
        Object,
        name,
        user_data
    ):
        if name.find("decodebin") != -1:
            Object.connect(
                "child-added",
                self._cb_child_added,
                user_data
            )

        if name.find("nvv4l2decoder") != -1:
            if Object.find_property("drop-on-latency") is not None:
                Object.set_property(
                    "drop-on-latency",
                    True
                )

        if name.find("source") != -1:
            if Object.find_property("protocols") is not None:
                Object.set_property(
                    "protocols",
                    4
                )

    @staticmethod
    def _encode_rtsp_uri(uri):
        """
        Format and validate URI for uridecodebin.

        Supports RTSP URLs and local video files.
        """

        if not uri:
            return uri

        if uri.startswith("file://"):
            return uri

        if os.path.exists(uri) or uri.endswith(
            (".mp4", ".avi", ".mkv", ".mov")
        ):
            abs_path = os.path.abspath(uri)
            return f"file://{abs_path}"

        if not uri.startswith("rtsp://"):
            return uri

        from urllib.parse import quote

        body = uri[7:]

        if "@" not in body:
            return uri

        creds, host_path = body.rsplit("@", 1)

        if ":" in creds:
            username, password = creds.split(":", 1)

            return (
                f"rtsp://"
                f"{quote(username, safe='')}:"
                f"{quote(password, safe='')}@"
                f"{host_path}"
            )

        return uri

    def _cb_newpad(
        self,
        decodebin,
        decoder_src_pad,
        data
    ):
        caps = decoder_src_pad.get_current_caps()

        if not caps:
            caps = decoder_src_pad.query_caps(None)

        if not caps or caps.get_size() == 0:
            return

        gststruct = caps.get_structure(0)
        gstname = gststruct.get_name()

        source_bin = data

        if gstname.find("video") != -1:
            bin_ghost_pad = source_bin.get_static_pad("src")

            if not bin_ghost_pad:
                logger.error(
                    "Source ghost pad does not exist"
                )
                return

            if not bin_ghost_pad.set_target(
                decoder_src_pad
            ):
                logger.error(
                    "Failed to link decoder src pad "
                    "to source bin ghost pad"
                )

    def _create_output_bin(
        self,
        source_id,
        camera_id
    ):
        """
        Create a per-camera RTSP output bin.

        IMPORTANT:
        rtspclientsink is an RTSP publishing sink and its request
        pads accept elementary encoded media. Do NOT put rtph264pay
        before rtspclientsink.

        Correct path:

            queue
              -> nvvideoconvert
              -> nvv4l2h264enc
              -> h264parse
              -> rtspclientsink request pad

        rtspclientsink creates/manages the RTP payloader internally.
        """

        bin_name = f"output-bin-{source_id}"

        obin = Gst.Bin.new(bin_name)
        if not obin:
            logger.error(
                f"Failed to create output bin for {camera_id}"
            )
            return None

        queue = Gst.ElementFactory.make(
            "queue",
            f"out-queue-{source_id}"
        )

        nvvidconv = Gst.ElementFactory.make(
            "nvvideoconvert",
            f"out-conv-{source_id}"
        )

        encoder = Gst.ElementFactory.make(
            "nvv4l2h264enc",
            f"out-enc-{source_id}"
        )

        h264parse = Gst.ElementFactory.make(
            "h264parse",
            f"out-parse-{source_id}"
        )

        sink = Gst.ElementFactory.make(
            "rtspclientsink",
            f"out-sink-{source_id}"
        )

        if not all([
            queue,
            nvvidconv,
            encoder,
            h264parse,
            sink
        ]):
            logger.error(
                f"Failed to create RTSP output elements "
                f"for camera {camera_id}"
            )
            return None

        encoder.set_property(
            "bitrate",
            4000000
        )

        if encoder.find_property("insert-sps-pps") is not None:
            encoder.set_property(
                "insert-sps-pps",
                True
            )

        if encoder.find_property("iframeinterval") is not None:
            encoder.set_property(
                "iframeinterval",
                30
            )

        sink.set_property(
            "location",
            f"rtsp://localhost:8554/{camera_id}"
        )

        sink.set_property(
            "protocols",
            4
        )

        for element in [
            queue,
            nvvidconv,
            encoder,
            h264parse,
            sink
        ]:
            obin.add(element)

        if not queue.link(nvvidconv):
            logger.error(
                f"Failed to link queue -> nvvideoconvert "
                f"for camera {camera_id}"
            )
            return None

        if not nvvidconv.link(encoder):
            logger.error(
                f"Failed to link nvvideoconvert -> encoder "
                f"for camera {camera_id}"
            )
            return None

        if not encoder.link(h264parse):
            logger.error(
                f"Failed to link encoder -> h264parse "
                f"for camera {camera_id}"
            )
            return None

        # rtspclientsink has request pads named sink_%u.
        # Link H264 elementary stream directly to the request pad.
        sink_pad = sink.get_request_pad("sink_%u")

        if not sink_pad:
            logger.error(
                f"Failed to request rtspclientsink sink pad "
                f"for camera {camera_id}"
            )
            return None

        parse_src_pad = h264parse.get_static_pad("src")

        if not parse_src_pad:
            logger.error(
                f"Failed to get h264parse src pad "
                f"for camera {camera_id}"
            )
            sink.release_request_pad(sink_pad)
            return None

        link_result = parse_src_pad.link(sink_pad)

        if link_result != Gst.PadLinkReturn.OK:
            logger.error(
                f"Failed to link h264parse -> rtspclientsink "
                f"for camera {camera_id}: {link_result}"
            )

            sink.release_request_pad(sink_pad)
            return None

        logger.info(
            f"RTSP H264 stream linked successfully "
            f"for camera {camera_id}"
        )

        queue_sink_pad = queue.get_static_pad("sink")

        if not queue_sink_pad:
            logger.error(
                f"Failed to get queue sink pad "
                f"for camera {camera_id}"
            )
            return None

        ghost_pad = Gst.GhostPad.new(
            "sink",
            queue_sink_pad
        )

        if not obin.add_pad(ghost_pad):
            logger.error(
                f"Failed to add ghost sink pad "
                f"for camera {camera_id}"
            )
            return None

        logger.info(
            f"Created RTSP output bin for camera "
            f"{camera_id}"
        )

        return obin

    def add_camera(
        self,
        camera_id,
        rtsp_url
    ):
        if camera_id in self.camera_to_source:
            logger.warning(
                f"Camera {camera_id} is already running."
            )
            return False

        if not self.available_source_ids:
            logger.error(
                f"Maximum capacity of "
                f"{self.max_cameras} streams reached."
            )
            return False

        logger.info(
            f"Dynamically adding camera "
            f"{camera_id}: {rtsp_url}"
        )

        self.available_source_ids.sort()
        source_id = self.available_source_ids.pop(0)

        source_bin = None
        output_bin = None
        source_sinkpad = None

        try:
            # ---------------------------------------------------------
            # 1. Add input source
            # ---------------------------------------------------------
            source_bin = self._create_source_bin(
                source_id,
                rtsp_url
            )

            self.pipeline.add(source_bin)

            srcpad = source_bin.get_static_pad("src")

            if not srcpad:
                raise RuntimeError(
                    f"Source ghost pad missing "
                    f"for source {source_id}"
                )

            sink_tmpl = self.streammux.get_pad_template(
                "sink_%u"
            )

            if sink_tmpl:
                source_sinkpad = self.streammux.request_pad(
                    sink_tmpl,
                    f"sink_{source_id}",
                    None
                )
            else:
                source_sinkpad = (
                    self.streammux.request_pad_simple(
                        f"sink_{source_id}"
                    )
                )

            if not source_sinkpad:
                raise RuntimeError(
                    f"Failed to request streammux sink pad "
                    f"for source {source_id}"
                )

            link_result = srcpad.link(
                source_sinkpad
            )

            if link_result != Gst.PadLinkReturn.OK:
                raise RuntimeError(
                    f"Failed to link source {source_id} "
                    f"to streammux: {link_result}"
                )

            source_bin.sync_state_with_parent()

            # ---------------------------------------------------------
            # 2. Create RTSP output bin
            # ---------------------------------------------------------
            output_bin = self._create_output_bin(
                source_id,
                camera_id
            )

            if output_bin is None:
                raise RuntimeError(
                    f"Failed to create output bin "
                    f"for camera {camera_id}"
                )

            self.pipeline.add(output_bin)

            # ---------------------------------------------------------
            # 3. Link demux -> output bin
            # ---------------------------------------------------------
            demux_srcpad = self.demux_pads.get(
                source_id
            )

            if not demux_srcpad:
                tmpl = self.demux.get_pad_template(
                    "src_%u"
                )

                if not tmpl:
                    raise RuntimeError(
                        "Failed to get demux src template"
                    )

                demux_srcpad = self.demux.request_pad(
                    tmpl,
                    f"src_{source_id}",
                    None
                )

            if not demux_srcpad:
                raise RuntimeError(
                    f"Failed to obtain demux pad "
                    f"for source {source_id}"
                )

            output_sink_pad = output_bin.get_static_pad(
                "sink"
            )

            if not output_sink_pad:
                raise RuntimeError(
                    f"Output ghost sink pad missing "
                    f"for camera {camera_id}"
                )

            link_result = demux_srcpad.link(
                output_sink_pad
            )

            if link_result != Gst.PadLinkReturn.OK:
                raise RuntimeError(
                    f"Failed to link demux -> output bin "
                    f"for camera {camera_id}: "
                    f"{link_result}"
                )

            output_bin.sync_state_with_parent()

            # ---------------------------------------------------------
            # 4. Store state
            # ---------------------------------------------------------
            self.sources[source_id] = (
                camera_id,
                source_bin
            )

            self.output_bins[source_id] = output_bin
            self.camera_to_source[camera_id] = source_id

            try:
                self.broker.r.set(
                    f"camera_state:{camera_id}",
                    "Connected"
                )
            except Exception as exc:
                logger.error(
                    f"Failed to publish camera state: {exc}"
                )

            logger.info(
                f"Camera {camera_id} output successfully "
                f"streaming to "
                f"rtsp://localhost:8554/{camera_id}"
            )

            return True

        except Exception as exc:
            logger.exception(
                f"Failed to add camera "
                f"{camera_id}: {exc}"
            )

            # ---------------------------------------------------------
            # Cleanup output side
            # ---------------------------------------------------------
            if output_bin is not None:
                try:
                    output_bin.set_state(
                        Gst.State.NULL
                    )
                except Exception:
                    pass

                try:
                    self.pipeline.remove(
                        output_bin
                    )
                except Exception:
                    pass

            # ---------------------------------------------------------
            # Cleanup input side
            # ---------------------------------------------------------
            if source_bin is not None:
                try:
                    srcpad = source_bin.get_static_pad(
                        "src"
                    )

                    if srcpad:
                        peer = srcpad.get_peer()

                        if peer:
                            srcpad.unlink(peer)

                            try:
                                self.streammux.release_request_pad(
                                    peer
                                )
                            except Exception:
                                pass
                except Exception:
                    pass

                try:
                    source_bin.set_state(
                        Gst.State.NULL
                    )
                except Exception:
                    pass

                try:
                    self.pipeline.remove(
                        source_bin
                    )
                except Exception:
                    pass

            self.available_source_ids.append(
                source_id
            )
            self.available_source_ids.sort()

            return False

    def remove_camera(
        self,
        camera_id
    ):
        if camera_id not in self.camera_to_source:
            logger.warning(
                f"Camera {camera_id} is not running."
            )
            return False

        logger.info(
            f"Dynamically removing camera "
            f"{camera_id}"
        )

        source_id = self.camera_to_source.pop(
            camera_id
        )

        _, source_bin = self.sources.pop(
            source_id,
            (None, None)
        )

        output_bin = self.output_bins.pop(
            source_id,
            None
        )

        # -------------------------------------------------------------
        # Remove output side
        # -------------------------------------------------------------
        if output_bin:
            try:
                ghost_sink = output_bin.get_static_pad(
                    "sink"
                )

                demux_srcpad = self.demux_pads.get(
                    source_id
                )

                if ghost_sink and demux_srcpad:
                    try:
                        demux_srcpad.unlink(
                            ghost_sink
                        )
                    except Exception:
                        pass

                output_bin.set_state(
                    Gst.State.NULL
                )

                self.pipeline.remove(
                    output_bin
                )

            except Exception as exc:
                logger.error(
                    f"Failed removing output bin "
                    f"for {camera_id}: {exc}"
                )

        # -------------------------------------------------------------
        # Remove input side
        # -------------------------------------------------------------
        if source_bin:
            try:
                srcpad = source_bin.get_static_pad(
                    "src"
                )

                if srcpad:
                    sinkpad = srcpad.get_peer()

                    if sinkpad:
                        try:
                            srcpad.unlink(
                                sinkpad
                            )
                        except Exception:
                            pass

                        try:
                            self.streammux.release_request_pad(
                                sinkpad
                            )
                        except Exception:
                            pass

                source_bin.set_state(
                    Gst.State.NULL
                )

                self.pipeline.remove(
                    source_bin
                )

            except Exception as exc:
                logger.error(
                    f"Failed removing source bin "
                    f"for {camera_id}: {exc}"
                )

        try:
            self.broker.r.set(
                f"camera_state:{camera_id}",
                "Stopped"
            )
        except Exception as exc:
            logger.error(
                f"Failed to publish camera state: {exc}"
            )

        self.available_source_ids.append(
            source_id
        )
        self.available_source_ids.sort()

        return True

    def _osd_sink_pad_buffer_probe(
        self,
        pad,
        info,
        u_data
    ):
        gst_buffer = info.get_buffer()

        if not gst_buffer:
            return Gst.PadProbeReturn.OK

        batch_meta = pyds.gst_buffer_get_nvds_batch_meta(
            hash(gst_buffer)
        )

        if not batch_meta:
            return Gst.PadProbeReturn.OK

        l_frame = batch_meta.frame_meta_list

        while l_frame is not None:
            try:
                frame_meta = pyds.NvDsFrameMeta.cast(
                    l_frame.data
                )
            except StopIteration:
                break
            except Exception as exc:
                logger.error(
                    f"Failed to cast frame metadata: {exc}"
                )
                break

            source_id = frame_meta.source_id

            if source_id not in self.sources:
                try:
                    l_frame = l_frame.next
                except StopIteration:
                    break

                continue

            camera_id, _ = self.sources[
                source_id
            ]

            detections = []
            extracted_faces = []

            l_obj = frame_meta.obj_meta_list

            while l_obj is not None:
                try:
                    obj_meta = pyds.NvDsObjectMeta.cast(
                        l_obj.data
                    )
                except StopIteration:
                    break
                except Exception as exc:
                    logger.error(
                        f"Failed to cast object metadata: "
                        f"{exc}"
                    )
                    break

                rect_params = obj_meta.rect_params
                track_id = obj_meta.object_id

                # -----------------------------------------------------
                # SGIE tensor output
                # -----------------------------------------------------
                l_user = obj_meta.obj_user_meta_list

                while l_user is not None:
                    try:
                        user_meta = pyds.NvDsUserMeta.cast(
                            l_user.data
                        )
                    except StopIteration:
                        break
                    except Exception as exc:
                        logger.error(
                            f"Failed to cast user metadata: "
                            f"{exc}"
                        )
                        break

                    if (
                        user_meta.base_meta.meta_type
                        == pyds.NvDsMetaType.NVDSINFER_TENSOR_OUTPUT_META
                    ):
                        try:
                            tensor_meta = (
                                pyds.NvDsInferTensorMeta.cast(
                                    user_meta.user_meta_data
                                )
                            )

                            layer = pyds.get_nvds_LayerInfo(
                                tensor_meta,
                                0
                            )

                            ptr = ctypes.cast(
                                pyds.get_ptr(layer.buffer),
                                ctypes.POINTER(
                                    ctypes.c_float
                                )
                            )

                            face_embedding = (
                                np.ctypeslib.as_array(
                                    ptr,
                                    shape=(512,)
                                ).copy()
                            )

                            extracted_faces.append(
                                {
                                    "track_id": track_id,
                                    "bbox": [
                                        rect_params.left,
                                        rect_params.top,
                                        (
                                            rect_params.left
                                            + rect_params.width
                                        ),
                                        (
                                            rect_params.top
                                            + rect_params.height
                                        )
                                    ],
                                    "embedding": face_embedding,
                                    "confidence": (
                                        obj_meta.confidence
                                    )
                                }
                            )

                        except Exception as exc:
                            logger.error(
                                f"Failed to extract face tensor: "
                                f"{exc}"
                            )

                    try:
                        l_user = l_user.next
                    except StopIteration:
                        break

                x1 = float(rect_params.left)
                y1 = float(rect_params.top)
                w = float(rect_params.width)
                h = float(rect_params.height)
                x2 = x1 + w
                y2 = y1 + h

                # Filter out tiny noise / artifacts
                if int(obj_meta.class_id) == 0 and (w < 25 or h < 50):
                    try:
                        l_obj = l_obj.next
                    except StopIteration:
                        break
                    continue

                # Clean confidence score (DeepStream defaults to -0.1 when unassigned)
                conf = float(obj_meta.confidence)
                if conf <= 0.0:
                    conf = 0.92

                det = NormalizedDetection(
                    bbox=[x1, y1, x2, y2],
                    confidence=conf,
                    class_id=int(obj_meta.class_id),
                    track_id=track_id
                )

                detections.append(det)

                try:
                    l_obj = l_obj.next
                except StopIteration:
                    break

            if detections:
                frame_surface = None
                try:
                    if any(int(d.class_id) in [0, 2, 3, 5, 7] for d in detections):
                        n_frame = pyds.get_nvds_buf_surface(hash(gst_buffer), frame_meta.batch_id)
                        frame_surface = np.array(n_frame, copy=True, order='C')
                except Exception:
                    pass

                frame_data = FrameData(
                    frame=frame_surface,
                    detections=detections,
                    camera_id=camera_id,
                    timestamp=time.time(),
                    faces=extracted_faces,
                    camera_url=""
                )

                try:
                    events = self.detection_engine.run_plugins(frame_data)
                    
                    import json
                    from core.utils import clean_numpy
                    
                    det_payload = [
                        {
                            "class_id": int(d.class_id),
                            "confidence": float(d.confidence),
                            "bbox": [float(b) for b in d.bbox],
                            "track_id": int(d.track_id) if d.track_id is not None else None
                        }
                        for d in detections
                    ]
                    
                    cleaned_events = clean_numpy(events) if events else {}
                    
                    payload = {
                        "camera_id": camera_id,
                        "sensor": {"id": camera_id},
                        "detections": det_payload,
                        "events": cleaned_events,
                        "timestamp": time.time(),
                        "fps": 30.0
                    }
                    
                    self.redis_client.publish("inference_result_ds", json.dumps(payload))
                except Exception as exc:
                    logger.error(f"[{camera_id}] DeepStream publish/engine error: {exc}")

            try:
                l_frame = l_frame.next
            except StopIteration:
                break

        return Gst.PadProbeReturn.OK

    def run(self):
        logger.info(
            "Starting DeepStream Pipeline Loop..."
        )

        self.broker.start()

        state_change = self.pipeline.set_state(
            Gst.State.PLAYING
        )

        if state_change == Gst.StateChangeReturn.FAILURE:
            logger.error(
                "Failed to set DeepStream pipeline "
                "to PLAYING"
            )
            self.broker.stop()
            return

        try:
            loop = GLib.MainLoop()
            loop.run()

        except KeyboardInterrupt:
            logger.info(
                "Keyboard interrupt received."
            )

        except Exception as exc:
            logger.exception(
                f"Pipeline crashed: {exc}"
            )

        finally:
            self.broker.stop()

            self.pipeline.set_state(
                Gst.State.NULL
            )


if __name__ == "__main__":
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    yolo_config = os.path.join(base_dir, "deepstream", "config_infer_yolo.txt")
    face_config = os.path.join(base_dir, "deepstream", "config_infer_face.txt")

    pipeline = DeepStreamPipeline(
        yolo_config,
        face_config
    )

    pipeline.run()
