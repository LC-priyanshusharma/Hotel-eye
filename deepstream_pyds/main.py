import sys
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import pyds
from loguru import logger
import time
import os
import ctypes
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))
from app.engine.engine import DetectionEngine
from app.engine.base import FrameData, NormalizedDetection
from message_broker import DeepStreamMessageBroker

class DeepStreamPipeline:
    def __init__(self, yolo_config_path, face_config_path):
        self.yolo_config_path = yolo_config_path
        self.face_config_path = face_config_path
        self.detection_engine = DetectionEngine()
        
        Gst.init(None)
        self.pipeline = Gst.Pipeline()
        self.streammux = None
        self.demux = None
        self.sources = {} # source_id -> (camera_id, source_bin)
        self.output_bins = {} # source_id -> output_bin
        self.camera_to_source = {} # camera_id -> source_id
        self.available_source_ids = [0, 1, 2, 3] # Pre-allocated slots
        
        self.broker = DeepStreamMessageBroker(self.add_camera, self.remove_camera)
        
        self._build_pipeline()

    def _build_pipeline(self):
        logger.info("Building Core DeepStream Pipeline with Face SGIE...")
        
        self.streammux = Gst.ElementFactory.make("nvstreammux", "Stream-muxer")
        self.streammux.set_property('width', 1280)
        self.streammux.set_property('height', 720)
        self.streammux.set_property('batch-size', 4) # Max 4 concurrent dynamic cameras
        self.streammux.set_property('batched-push-timeout', 40000)
        self.streammux.set_property('live-source', 1)
        self.pipeline.add(self.streammux)

        pgie = Gst.ElementFactory.make("nvinfer", "primary-inference")
        pgie.set_property('config-file-path', self.yolo_config_path)
        
        tracker = Gst.ElementFactory.make("nvtracker", "tracker")
        tracker.set_property('ll-lib-file', '/opt/nvidia/deepstream/deepstream/lib/libnvds_nvmultiobjecttracker.so')
        tracker.set_property('ll-config-file', 'config_tracker.yml')
        
        # Face Embeddings Secondary Engine (SGIE)
        sgie = Gst.ElementFactory.make("nvinfer", "secondary-inference-face")
        sgie.set_property('config-file-path', self.face_config_path)
        
        nvvidconv1 = Gst.ElementFactory.make("nvvideoconvert", "convertor1")
        nvosd = Gst.ElementFactory.make("nvdsosd", "onscreendisplay")
        nvosd.set_property('display-bbox', 0)
        nvosd.set_property('display-text', 0)
        
        # Tee splits the annotated output into two branches:
        # 1. fakesink — keeps pipeline alive when no cameras are connected
        # 2. nvstreamdemux — splits batched frames back into per-camera streams
        tee = Gst.ElementFactory.make("tee", "output-tee")
        queue_fake = Gst.ElementFactory.make("queue", "fake-queue")
        fakesink = Gst.ElementFactory.make("fakesink", "fake-sink")
        fakesink.set_property("sync", False)
        fakesink.set_property("async", False)
        
        queue_demux = Gst.ElementFactory.make("queue", "demux-queue")
        self.demux = Gst.ElementFactory.make("nvstreamdemux", "stream-demuxer")
        
        self.pipeline.add(pgie)
        self.pipeline.add(tracker)
        self.pipeline.add(sgie)
        self.pipeline.add(nvvidconv1)
        self.pipeline.add(nvosd)
        self.pipeline.add(tee)
        self.pipeline.add(queue_fake)
        self.pipeline.add(fakesink)
        self.pipeline.add(queue_demux)
        self.pipeline.add(self.demux)

        self.streammux.link(pgie)
        pgie.link(tracker)
        tracker.link(sgie)
        sgie.link(nvvidconv1)
        nvvidconv1.link(nvosd)
        nvosd.link(tee)
        tee.link(queue_fake)
        queue_fake.link(fakesink)
        tee.link(queue_demux)
        queue_demux.link(self.demux)

        # Pre-allocate 4 output branches since nvstreamdemux does not support
        # dynamic pad requests while in the PLAYING state.
        for i in range(4):
            pad_name = f"src_{i}"
            tmpl = self.demux.get_pad_template("src_%u")
            demux_pad = self.demux.request_pad(tmpl, pad_name, None)
            
            obin = self._create_output_bin(i, f"cam_{i}")
            self.pipeline.add(obin)
            self.output_bins[i] = obin
            demux_pad.link(obin.get_static_pad("sink"))

        # Attach Probe to extract metadata AFTER sgie
        sgie_src_pad = sgie.get_static_pad("src")
        sgie_src_pad.add_probe(Gst.PadProbeType.BUFFER, self._osd_sink_pad_buffer_probe, 0)
        
        # Add a bus watch for errors
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._bus_call)

    def _bus_call(self, bus, message):
        t = message.type
        if t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error(f"Error from {message.src.get_name()}: {err.message}")
            src_name = message.src.get_name()
            if src_name.startswith("uri-decode-bin"):
                logger.error(f"Source {src_name} failed. Attempting to isolate and remove.")
        elif t == Gst.MessageType.WARNING:
            err, debug = message.parse_warning()
            logger.warning(f"Warning from {message.src.get_name()}: {err.message}")
        return True

    def _create_source_bin(self, source_id, uri):
        bin_name = f"source-bin-{source_id}"
        nbin = Gst.Bin.new(bin_name)
        uri_decode_bin = Gst.ElementFactory.make("uridecodebin", f"uri-decode-bin-{source_id}")
        
        # Encode credentials for uridecodebin URI parsing.
        # Passwords with special chars like @ confuse the URI parser.
        safe_uri = self._encode_rtsp_uri(uri)
        uri_decode_bin.set_property("uri", safe_uri)
        
        uri_decode_bin.connect("pad-added", self._cb_newpad, nbin)
        uri_decode_bin.connect("source-setup", self._cb_source_setup)
        
        Gst.Bin.add(nbin, uri_decode_bin)
        bin_pad = Gst.GhostPad.new_no_target("src", Gst.PadDirection.SRC)
        nbin.add_pad(bin_pad)
        return nbin

    def _cb_source_setup(self, element, source):
        # Force TCP on the underlying rtspsrc to pass through SSH tunnels
        if source.get_factory().get_name() == "rtspsrc":
            source.set_property("protocols", 4)

    @staticmethod
    def _encode_rtsp_uri(uri):
        """Encode only the username:password portion of an RTSP URI for safe parsing."""
        if not uri or not uri.startswith("rtsp://"):
            return uri
        from urllib.parse import quote
        body = uri[7:]  # strip rtsp://
        if "@" not in body:
            return uri
        # rsplit on @ with maxsplit=1 to separate creds from host
        creds, host_path = body.rsplit("@", 1)
        if ":" in creds:
            username, password = creds.split(":", 1)
            return f"rtsp://{quote(username, safe='')}:{quote(password, safe='')}@{host_path}"
        return uri

    def _cb_newpad(self, decodebin, decoder_src_pad, data):
        caps = decoder_src_pad.get_current_caps()
        gststruct = caps.get_structure(0)
        gstname = gststruct.get_name()
        source_bin = data
        if gstname.find("video") != -1:
            bin_ghost_pad = source_bin.get_static_pad("src")
            if not bin_ghost_pad.set_target(decoder_src_pad):
                logger.error("Failed to link decoder src pad to source bin ghost pad")

    def _create_output_bin(self, source_id, camera_id):
        """Create a per-camera RTSP output bin that publishes to MediaMTX."""
        bin_name = f"output-bin-{source_id}"
        obin = Gst.Bin.new(bin_name)
        
        queue = Gst.ElementFactory.make("queue", f"out-queue-{source_id}")
        nvvidconv = Gst.ElementFactory.make("nvvideoconvert", f"out-conv-{source_id}")
        encoder = Gst.ElementFactory.make("nvv4l2h264enc", f"out-enc-{source_id}")
        encoder.set_property('bitrate', 4000000)
        h264parse = Gst.ElementFactory.make("h264parse", f"out-parse-{source_id}")
        rtppay = Gst.ElementFactory.make("rtph264pay", f"out-rtppay-{source_id}")
        sink = Gst.ElementFactory.make("rtspclientsink", f"out-sink-{source_id}")
        sink.set_property("location", f"rtsp://localhost:8554/{camera_id}")
        sink.set_property("protocols", 4)  # TCP
        
        for el in [queue, nvvidconv, encoder, h264parse, rtppay, sink]:
            obin.add(el)
        
        queue.link(nvvidconv)
        nvvidconv.link(encoder)
        encoder.link(h264parse)
        h264parse.link(rtppay)
        rtppay.link(sink)
        
        ghost_pad = Gst.GhostPad.new("sink", queue.get_static_pad("sink"))
        obin.add_pad(ghost_pad)
        return obin

    def add_camera(self, camera_id, rtsp_url):
        if camera_id in self.camera_to_source:
            logger.warning(f"Camera {camera_id} is already running.")
            return False
            
        if not self.available_source_ids:
            logger.error("Maximum number of cameras (4) reached.")
            return False
            
        logger.info(f"Dynamically adding camera {camera_id}: {rtsp_url}")
        # Pop the lowest available source ID
        self.available_source_ids.sort()
        source_id = self.available_source_ids.pop(0)
        
        # --- Input side: RTSP source → streammux ---
        source_bin = self._create_source_bin(source_id, rtsp_url)
        self.pipeline.add(source_bin)
        
        srcpad = source_bin.get_static_pad("src")
        sinkpad = self.streammux.request_pad_simple(f"sink_{source_id}")
        srcpad.link(sinkpad)
        source_bin.sync_state_with_parent()
        
        # Output side: Re-point the existing pre-allocated rtspclientsink to this camera's UUID
        output_bin = self.output_bins[source_id]
        sink_el = output_bin.get_by_name(f"out-sink-{source_id}")
        if sink_el:
            sink_el.set_state(Gst.State.NULL)
            sink_el.set_property("location", f"rtsp://localhost:8554/{camera_id}")
            sink_el.set_state(Gst.State.PLAYING)
        
        self.sources[source_id] = (camera_id, source_bin)
        self.camera_to_source[camera_id] = source_id
        
        # Notify backend that this camera stream is now live
        try:
            self.broker.r.set(f"camera_state:{camera_id}", "Connected")
        except Exception as e:
            logger.error(f"Failed to publish camera state: {e}")
        
        logger.info(f"Camera {camera_id} output published to rtsp://localhost:8554/{camera_id}")
        return False

    def remove_camera(self, camera_id):
        if camera_id not in self.camera_to_source:
            logger.warning(f"Camera {camera_id} is not running.")
            return False
            
        logger.info(f"Dynamically removing camera {camera_id}")
        source_id = self.camera_to_source.pop(camera_id)
        _, source_bin = self.sources.pop(source_id)
        
        # --- Tear down input side ---
        srcpad = source_bin.get_static_pad("src")
        sinkpad = srcpad.get_peer()
        if sinkpad:
            srcpad.unlink(sinkpad)
            self.streammux.release_request_pad(sinkpad)
        source_bin.set_state(Gst.State.NULL)
        self.pipeline.remove(source_bin)
        
        # Output side: Stop pushing to the UUID path to free MediaMTX resources
        output_bin = self.output_bins.get(source_id)
        if output_bin:
            sink_el = output_bin.get_by_name(f"out-sink-{source_id}")
            if sink_el:
                sink_el.set_state(Gst.State.NULL)
                sink_el.set_property("location", f"rtsp://localhost:8554/idle_{source_id}")
                sink_el.set_state(Gst.State.PLAYING)
        
        # Notify backend that this camera stream is stopped
        try:
            self.broker.r.set(f"camera_state:{camera_id}", "Stopped")
        except Exception as e:
            logger.error(f"Failed to publish camera state: {e}")
            
        # Recycle the source ID for future cameras
        self.available_source_ids.append(source_id)
        
        return False

    def _osd_sink_pad_buffer_probe(self, pad, info, u_data):
        gst_buffer = info.get_buffer()
        if not gst_buffer:
            return Gst.PadProbeReturn.OK

        batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
        l_frame = batch_meta.frame_meta_list
        
        while l_frame is not None:
            try:
                frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
            except StopIteration:
                break
                
            source_id = frame_meta.source_id
            if source_id not in self.sources:
                try:
                    l_frame = l_frame.next
                except StopIteration:
                    break
                continue
                
            camera_id, _ = self.sources[source_id]

            detections = []
            extracted_faces = []
            
            l_obj = frame_meta.obj_meta_list
            while l_obj is not None:
                try:
                    obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
                except StopIteration:
                    break
                
                rect_params = obj_meta.rect_params
                track_id = obj_meta.object_id
                
                # Check for SGIE tensor output (Face Embeddings)
                l_user = obj_meta.obj_user_meta_list
                while l_user is not None:
                    try:
                        user_meta = pyds.NvDsUserMeta.cast(l_user.data)
                    except StopIteration:
                        break
                    
                    if user_meta.base_meta.meta_type == pyds.NvDsMetaType.NVDSINFER_TENSOR_OUTPUT_META:
                        try:
                            tensor_meta = pyds.NvDsInferTensorMeta.cast(user_meta.user_meta_data)
                            layer = pyds.get_nvds_LayerInfo(tensor_meta, 0)
                            ptr = ctypes.cast(pyds.get_ptr(layer.buffer), ctypes.POINTER(ctypes.c_float))
                            face_embedding = np.ctypeslib.as_array(ptr, shape=(512,)).copy()
                            
                            # Append to extracted faces to send to the FaceWorker database matcher
                            extracted_faces.append({
                                "track_id": track_id,
                                "bbox": [rect_params.left, rect_params.top, rect_params.left+rect_params.width, rect_params.top+rect_params.height],
                                "embedding": face_embedding,
                                "confidence": obj_meta.confidence
                            })
                        except Exception as e:
                            logger.error(f"Failed to extract face tensor: {e}")
                            
                    try:
                        l_user = l_user.next
                    except StopIteration:
                        break
                
                det = NormalizedDetection(
                    box=[rect_params.left, rect_params.top, rect_params.width, rect_params.height],
                    score=obj_meta.confidence,
                    class_id=obj_meta.class_id,
                    track_id=track_id
                )
                detections.append(det)
                
                try:
                    l_obj = l_obj.next
                except StopIteration:
                    break

            if detections:
                frame_data = FrameData(
                    frame=None,
                    detections=detections,
                    camera_id=camera_id,
                    timestamp=time.time(),
                    faces=extracted_faces,
                    camera_url=""
                )
                events = self.detection_engine.run_plugins(frame_data)
                if events:
                    logger.info(f"[{camera_id}] DeepStream detected actionable events: {events}")

            try:
                l_frame = l_frame.next
            except StopIteration:
                break

        return Gst.PadProbeReturn.OK

    def run(self):
        logger.info("Starting DeepStream Pipeline Loop...")
        self.broker.start()
        self.pipeline.set_state(Gst.State.PLAYING)
        try:
            loop = GLib.MainLoop()
            loop.run()
        except Exception as e:
            logger.error(f"Pipeline crashed: {e}")
        finally:
            self.broker.stop()
            self.pipeline.set_state(Gst.State.NULL)

if __name__ == "__main__":
    yolo_config = "deepstream/config_infer_yolo.txt"
    face_config = "deepstream/config_infer_face.txt"
    pipeline = DeepStreamPipeline(yolo_config, face_config)
    pipeline.run()
