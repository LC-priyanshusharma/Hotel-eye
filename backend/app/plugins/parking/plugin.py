from typing import List, Dict, Any
from loguru import logger
from shapely.geometry import Point, Polygon

from app.engine.base import BaseDetectionPlugin, FrameData, TrackerContext, DetectionEvent
from config.config import config

class ParkingAnalyticsPlugin(BaseDetectionPlugin):
    """
    Handles Vehicle Detection and Parking Occupancy.
    """
    def __init__(self, app_config=None):
        super().__init__(app_config)
        # COCO Classes for vehicles: 2=car, 3=motorcycle, 5=bus, 7=truck
        self.vehicle_classes = {2, 3, 5, 7}
        logger.info("Initialized ParkingAnalyticsPlugin")

    @property
    def plugin_name(self) -> str:
        return "ParkingAnalyticsPlugin"

    def get_required_classes(self) -> List[int]:
        return list(self.vehicle_classes)

    def process_frame(self, frame_data: FrameData, tracker_context: TrackerContext) -> List[DetectionEvent]:
        camera_id = frame_data.camera_id
        timestamp = frame_data.timestamp
        events = []
        
        spots = config.get_parking_spots_for_camera(camera_id)
        if not spots:
            return events
            
        spot_polys = [Polygon(spot) for spot in spots]
        
        occupied_spots = [False] * len(spots)
        vehicle_count = 0
        
        if frame_data.detections is not None and getattr(frame_data.detections, 'boxes', None) is not None:
            boxes = frame_data.detections.boxes.xyxy.cpu().numpy()
            cls_ids = frame_data.detections.boxes.cls.cpu().numpy()
            
            for box, cls_id in zip(boxes, cls_ids):
                if int(cls_id) not in self.vehicle_classes:
                    continue
                    
                vehicle_count += 1
                
                x1, y1, x2, y2 = box
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                center_point = Point(center_x, center_y)
                
                for idx, poly in enumerate(spot_polys):
                    if poly.contains(center_point):
                        occupied_spots[idx] = True
                        
        total_spots = len(spots)
        occupied_count = sum(occupied_spots)
        available_count = total_spots - occupied_count
        
        drawings = []
        for idx, spot in enumerate(spots):
            color = [0, 0, 255] if occupied_spots[idx] else [0, 255, 0]
            drawings.append({
                "type": "poly",
                "coords": spot,
                "color": color,
                "thickness": 2
            })
            
        event = DetectionEvent(
            plugin_name=self.plugin_name,
            event_type="PARKING_STATS",
            camera_id=camera_id,
            timestamp=timestamp,
            confidence=1.0,
            metadata={
                "vehicle_count": vehicle_count,
                "total_spots": total_spots,
                "occupied_spots": occupied_count,
                "available_spots": available_count,
                "spot_status": occupied_spots,
                "drawings": drawings
            }
        )
        events.append(event)
            
        return events
