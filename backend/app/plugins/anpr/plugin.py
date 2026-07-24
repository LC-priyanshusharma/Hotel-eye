import asyncio
import copy
from typing import List, Dict, Any
from loguru import logger

from app.engine.base import BaseDetectionPlugin, FrameData, TrackerContext, DetectionEvent
from app.plugins.anpr.factory import ANPRFactory
from app.plugins.anpr.tracker import ANPRTracker
from app.plugins.anpr.validator import PlateValidator
from app.plugins.anpr.service import anpr_service
from app.plugins.anpr.config_parser import anpr_app_config
from app.plugins.anpr.utils import save_snapshot
from app.plugins.anpr.events import ANPREventType

class ANPRPlugin(BaseDetectionPlugin):
    """
    Enterprise ANPR Plugin.
    Handles Vehicle detection (via core), Plate Detection (via internal YOLO),
    OCR extraction (PP-OCRv5), Temporal Fusion, and Regex validation.
    """
    def __init__(self, app_config=None):
        super().__init__(app_config)
        self.plate_detector = ANPRFactory.get_plate_detector()
        self.ocr_engine = ANPRFactory.get_ocr_engine()
        self.tracker = ANPRTracker(track_timeout=anpr_app_config.fusion.track_timeout_seconds)
        logger.info("Initialized ANPRPlugin via ANPRFactory.")
        
        # Start the background service for DB logging if there's a loop
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(anpr_service.start())
        except RuntimeError:
            pass # No loop running yet

    @property
    def plugin_name(self) -> str:
        return "ANPRPlugin"

    def get_required_classes(self) -> List[int]:
        # Typically vehicles: 2 (car), 3 (motorcycle), 5 (bus), 7 (truck)
        return [2, 3, 5, 7]

    def process_frame(self, frame_data: FrameData, tracker_context: TrackerContext) -> List[DetectionEvent]:
        events = []
        camera_id = frame_data.camera_id
        timestamp = frame_data.timestamp
        frame = frame_data.frame
        
        # 1. Iterate over vehicle detections provided by the core pipeline
        if not hasattr(frame_data.detections, 'boxes') or getattr(frame_data.detections.boxes, 'id', None) is None:
            # Cleanup Stale Tracks and Emit Final Events even if no detections this frame
            return self._cleanup_and_emit(camera_id, timestamp)

        for box in frame_data.detections.boxes:
            track_id = int(box.id[0].item())
            class_id = int(box.cls[0].item())
            
            # 2 (car), 3 (motorcycle), 5 (bus), 7 (truck)
            if class_id not in [2, 3, 5, 7]:
                continue
                
            vehicle_box = box.xyxy[0].cpu().numpy()
            
            # Crop vehicle
            vx1, vy1, vx2, vy2 = map(int, vehicle_box)
            # Boundary checks
            h, w = frame.shape[:2]
            vx1, vy1 = max(0, vx1), max(0, vy1)
            vx2, vy2 = min(w, vx2), min(h, vy2)
            
            if vx2 - vx1 < 20 or vy2 - vy1 < 20:
                continue
                
            vehicle_crop = frame[vy1:vy2, vx1:vx2]
            
            # 2. Plate Detection within the vehicle crop
            plates = self.plate_detector.detect_plates(vehicle_crop)
            
            # Map COCO classes to vehicle types
            type_map = {
                2: "LMV",
                3: "2-Wheeler",
                5: "HMV-Bus",
                7: "HMV-Truck"
            }
            v_type_str = type_map.get(int(class_id), "Unknown")
            
            # Retrieve or create track
            vehicle_track = self.tracker.get_or_create_track(track_id, timestamp, vehicle_type=v_type_str)
            vehicle_track.update(timestamp)
            
            if not vehicle_track.best_vehicle_snapshot:
                # Store the raw numpy array, the background service will handle saving it
                vehicle_track.best_vehicle_snapshot = vehicle_crop.copy()
            
            for plate_crop, p_conf, p_bbox in plates:
                # 3. OCR Extraction
                ocr_results = self.ocr_engine.recognize(plate_crop)
                
                for res in ocr_results:
                    raw_text = res["text"]
                    ocr_conf = res["confidence"]
                    
                    if ocr_conf < anpr_app_config.ocr.confidence_threshold:
                        continue
                        
                    # 4. Validation & Repair
                    is_valid, repaired_text = PlateValidator.repair_and_validate(raw_text, confidence=ocr_conf)
                    
                    if is_valid and repaired_text:
                        # 5. Temporal Fusion
                        vehicle_track.fusion.add_observation(repaired_text, ocr_conf, timestamp)
                        
                        # Save the best plate snapshot dynamically based on highest OCR conf seen
                        if not hasattr(vehicle_track, 'max_ocr_seen') or ocr_conf > vehicle_track.max_ocr_seen:
                            vehicle_track.max_ocr_seen = ocr_conf
                            vehicle_track.best_plate_snapshot = plate_crop.copy()

            # Emit a live event so the plate and vehicle box are drawn in the frontend
            best_plate, best_conf = vehicle_track.fusion.get_best_plate()
            if best_plate:
                live_event = DetectionEvent(
                    plugin_name=self.plugin_name,
                    event_type="LIVE_TRACKING",
                    camera_id=camera_id,
                    timestamp=timestamp,
                    confidence=best_conf,
                    metadata={
                        "plate_number": best_plate,
                        "vehicle_type": getattr(vehicle_track, 'vehicle_type', 'Vehicle'),
                        "drawings": [
                            {
                                "type": "rect",
                                "coords": vehicle_box.tolist(),
                                "color": [0, 255, 0],
                                "thickness": 2
                            },
                            {
                                "type": "text",
                                "coords": [vehicle_box[0], max(0, vehicle_box[1] - 10)],
                                "text": f"{best_plate} ({best_conf:.2f})",
                                "color": [255, 255, 255],
                                "thickness": 2,
                                "scale": 0.8
                            }
                        ]
                    }
                )
                events.append(live_event)

        # 6. Cleanup Stale Tracks and Emit Final Events
        events.extend(self._cleanup_and_emit(camera_id, timestamp))
        return events

    def _cleanup_and_emit(self, camera_id: str, timestamp: float) -> List[DetectionEvent]:
        events = []
        finalized_tracks = self.tracker.cleanup_stale_tracks(timestamp)
        
        for track in finalized_tracks:
            best_plate, best_conf = track.fusion.get_best_plate()
            
            if best_plate:
                # Dispatch async DB log task
                track_info = {
                    "track_id": str(track.track_id),
                    "camera_id": camera_id,
                    "start_time": track.start_time,
                    "end_time": track.last_seen,
                    "best_plate": best_plate,
                    "plate_confidence": best_conf,
                    "vehicle_type": track.vehicle_type,
                    "vehicle_snapshot": track.best_vehicle_snapshot,
                    "plate_snapshot": track.best_plate_snapshot
                }
                
                import threading
                threading.Thread(target=anpr_service._handle_track, args=({"track_info": track_info},), daemon=True).start()
                
                # Emit WebSocket Event for real-time frontend
                event = DetectionEvent(
                    plugin_name=self.plugin_name,
                    event_type=ANPREventType.NEW_PLATE.value,
                    camera_id=camera_id,
                    timestamp=track.last_seen,
                    confidence=best_conf,
                    metadata={
                        "plate_number": best_plate,
                        "track_id": track.track_id,
                        "vehicle_type": track.vehicle_type,
                        "vehicle_snapshot": track.best_vehicle_snapshot,
                        "plate_snapshot": track.best_plate_snapshot,
                        "drawings": []
                    }
                )
                events.append(event)
                
        return events
