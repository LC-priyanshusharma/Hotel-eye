from database.session import SessionLocal
from database.models.models import CameraEvent
from typing import Dict, Any, Tuple, Optional

# --- Dispatcher Handlers ---

def _handle_enterprise_safety(e_data: Dict, cam_name: str) -> Optional[Tuple[str, str, Optional[str]]]:
    active_alerts = e_data.get("active_alerts", [])
    if "FIRE_DETECTED" in active_alerts:
        return "danger", "Fire Detected", None
    return None

def _handle_intrusion(e_data: list, cam_name: str) -> Optional[Tuple[str, str, Optional[str]]]:
    for event in e_data:
        if event.get("event_type") == "INTRUSION_DETECTED":
            return "warning", "Zone Intrusion Detected", event.get("snapshot_path")
    return None

def _handle_attendance(e_data: list, cam_name: str) -> Optional[Tuple[str, str, Optional[str]]]:
    for event in e_data:
        if event.get("event_type") in ["CHECK_IN", "CHECK_OUT"]:
            action = event["metadata"].get("action")
            emp = event["metadata"].get("employee_id")
            return "success" if action == "CHECK IN" else "info", f"Emp {emp} {action}", None
    return None

def _handle_people_counting(e_data: list, cam_name: str) -> Optional[Tuple[str, str, Optional[str]]]:
    for event in e_data:
        if event.get("event_type") == "LINE_CROSSED":
            return "info", "Visitor detected in this camera", None
        elif event.get("event_type") == "PERSON_COUNT":
            count = event["metadata"].get("current_people_in_frame", 0)
            if count > 0:
                return "info", f"Person Count: {count}", None
    return None

def _handle_gesture(e_data: Dict, cam_name: str) -> Optional[Tuple[str, str, Optional[str]]]:
    active_alerts = e_data.get("active_alerts", [])
    snapshot = "/" + e_data.get("snapshot_file") if e_data.get("snapshot_file") else None
    
    if "HAND_RAISE_DETECTED" in active_alerts:
        return "info", "Hand Raise Detected", snapshot
    elif "GESTURE_DETECTED" in active_alerts:
        gesture_events = e_data.get("gesture_events", [])
        if gesture_events:
            top_gesture = gesture_events[0].get("gesture", "Unknown")
            return "info", f"Gesture: {top_gesture}", snapshot
    return None

def _handle_visitor(e_data: Any, cam_name: str) -> Optional[Tuple[str, str, Optional[str]]]:
    # Handle both list and dict formats for backward compatibility
    events_list = e_data if isinstance(e_data, list) else (e_data["VisitorPlugin"] if isinstance(e_data, dict) and "VisitorPlugin" in e_data else [])
    
    for event in events_list:
        if isinstance(event, dict) and event.get("plugin_name") == "VisitorPlugin":
            evt_type = event.get("event_type")
            if evt_type in ["EMPLOYEE_RECOGNIZED", "VISITOR_RECOGNIZED", "UNKNOWN_PERSON"]:
                meta = event.get("metadata", {})
                vid = meta.get("visitor_id", "N/A")
                name = meta.get("name", "Unknown")
                snapshot = meta.get("snapshot_file")
                if snapshot:
                    snapshot = "/" + snapshot
                
                if evt_type == "EMPLOYEE_RECOGNIZED":
                    dept = "Broker 1" if hash(vid) % 2 == 0 else "Broker 2"
                    role = f"Employee [{dept}]"
                    event_type_str = "success"
                elif evt_type == "VISITOR_RECOGNIZED":
                    role = "Visitor"
                    event_type_str = "info"
                else:
                    role = "Unknown"
                    event_type_str = "warning"
                    
                action_word = "Checkout" if "CHECK OUT" in cam_name.upper() else "Detect"
                return event_type_str, f"{role} {action_word} with Camera {cam_name} ID: {vid} Name: {name}", snapshot
    return None

def _handle_anpr(e_data: list, cam_name: str) -> Optional[Tuple[str, str, Optional[str]]]:
    for event in e_data:
        if event.get("event_type") == "NEW_PLATE":
            metadata = event.get("metadata", {})
            plate_num = metadata.get("plate_number")
            snap = metadata.get("vehicle_snapshot")
            if snap:
                snap = "/" + snap
            if plate_num:
                return "info", f"Plate Detected: {plate_num}", snap
        elif event.get("event_type") == "LIVE_TRACKING":
            metadata = event.get("metadata", {})
            plate_num = metadata.get("plate_number")
            if plate_num:
                return "info", f"Plate Detected: {plate_num}", None
    return None

def _handle_parking(e_data: list, cam_name: str) -> Optional[Tuple[str, str, Optional[str]]]:
    if isinstance(e_data, list):
        for event in e_data:
            if event.get("event_type") == "PARKING_ALERT":
                meta = event.get("metadata", {})
                bay = meta.get("bay_id", "Unknown")
                status = meta.get("status", "")
                return "danger" if status == "OCCUPIED" else "success", f"Parking Bay {bay} {status}", None
    return None

def _handle_ppe(e_data: Any, cam_name: str) -> Optional[Tuple[str, str, Optional[str]]]:
    # e_data could be a dict if wrapped by the pipeline, or a list of events
    events_list = e_data if isinstance(e_data, list) else (e_data["PPEDetectionPlugin"] if isinstance(e_data, dict) and "PPEDetectionPlugin" in e_data else [])
    
    for event in events_list:
        if isinstance(event, dict) and event.get("event_type") == "PPE_MISSING":
            metadata = event.get("metadata", {})
            snap = metadata.get("snapshot_file")
            if snap:
                snap = "/" + snap
            
            missing_count = len(metadata.get("persons_without_ppe", []))
            return "danger", f"Missing PPE Detected: {missing_count} Person(s)", snap
    return None

EVENT_DISPATCHER = {
    "EnterpriseSafetyPlugin": _handle_enterprise_safety,
    "IntrusionDetectionPlugin": _handle_intrusion,
    "AttendanceDetectionPlugin": _handle_attendance,
    "PeopleCountingPlugin": _handle_people_counting,
    "GestureDetectionPlugin": _handle_gesture,
    "ANPRPlugin": _handle_anpr,
    "ParkingAnalyticsPlugin": _handle_parking,
    "PPEDetectionPlugin": _handle_ppe
}

class EventService:
    @staticmethod
    def get_latest_events(
        camera_id: str = None, 
        start_date: str = None, 
        end_date: str = None, 
        severity: str = None, 
        category: str = None
    ):
        """Returns the latest historical events from the database."""
        from database.repositories.event_repository import EventRepository
        from database.repositories.camera_repository import CameraRepository
        db = SessionLocal()
        try:
            repo = EventRepository(db)
            repo_cam = CameraRepository(db)
            
            cameras = repo_cam.get_active_cameras()
            cam_map = {str(c.id): c.name for c in cameras}
            
            if camera_id:
                known_cameras = [(camera_id,)]
            else:
                known_cameras = repo.get_distinct_camera_ids()
                
            result = []
            
            for (cam_id,) in known_cameras:
                cam_events = repo.get_filtered_events(
                    camera_id=cam_id, 
                    start_date=start_date, 
                    end_date=end_date, 
                    limit=20
                )
                
                valid_cam_events = []
                last_desc = None
                for e in cam_events:
                    event_type = e.events.get("event_type", "info") if isinstance(e.events, dict) else "info"
                    description = e.events.get("description", "Analytics Update") if isinstance(e.events, dict) else "Analytics Update"
                    snapshot_file = e.events.get("snapshot_file", None) if isinstance(e.events, dict) else None
                    
                    cam_name = cam_map.get(e.camera_id, e.camera_id.split("/")[-1])
                    
                    # Try Dispatcher Handlers
                    handled = False
                    if isinstance(e.events, dict):
                        for plugin_name, handler in EVENT_DISPATCHER.items():
                            if plugin_name in e.events:
                                res = handler(e.events[plugin_name], cam_name)
                                if res:
                                    event_type, description, snap = res
                                    if snap:
                                        snapshot_file = snap
                                    handled = True
                                    break
                    
                    # Fallback to Visitor if not handled
                    if not handled:
                        res = _handle_visitor(e.events, cam_name)
                        if res:
                            event_type, description, snap = res
                            if snap:
                                snapshot_file = snap

                    # Skip spammy analytics updates at the API level
                    if description == "Analytics Update":
                        continue
                        
                    # Deduplicate consecutive identical events to prevent starvation
                    if description == last_desc:
                        continue
                    last_desc = description

                    # Apply Category filter
                    event_category = "EVENT"
                    upper_desc = description.upper()
                    if "CHECK IN" in upper_desc or "CHECK OUT" in upper_desc or "ATTENDANCE" in upper_desc:
                        event_category = "ATTENDANCE"
                    elif "INTRUSION" in upper_desc:
                        event_category = "INTRUSION"
                    elif "FIRE" in upper_desc:
                        event_category = "SAFETY ALERT"
                    elif "PERSON COUNT" in upper_desc or "PEOPLE" in upper_desc:
                        event_category = "PEOPLE COUNT"
                        
                    if category and category.upper() != event_category:
                        continue
                        
                    # Apply Severity filter
                    if severity and severity.lower() != event_type:
                        continue

                    valid_cam_events.append({
                        "id": e.id,
                        "timestamp": e.timestamp.isoformat(),
                        "camera_id": e.camera_id,
                        "camera_name": cam_name,
                        "event_type": event_type,
                        "description": description,
                        "snapshot_file": snapshot_file
                    })
                    
                    if len(valid_cam_events) >= 15:
                        break
                        
                result.extend(valid_cam_events)

            result.sort(key=lambda x: x["timestamp"], reverse=True)
            return result
        finally:
            db.close()

    @staticmethod
    def get_dashboard_stats(active_cameras_count: int):
        import psutil
        from database.repositories.event_repository import EventRepository
        db = SessionLocal()
        critical_alerts = 0
        try:
            repo = EventRepository(db)
            # Fetch only the last 50 events to keep JSON parsing overhead <100ms
            events = db.query(CameraEvent).order_by(CameraEvent.timestamp.desc()).limit(50).all()
            for e in events:
                if isinstance(e.events, dict) and "EnterpriseSafetyPlugin" in e.events:
                    active = e.events["EnterpriseSafetyPlugin"].get("active_alerts", [])
                    if "FIRE_DETECTED" in active:
                        critical_alerts += 1
        finally:
            db.close()

        cpu_usage = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net = psutil.net_io_counters()
        net_mbps = round((net.bytes_sent + net.bytes_recv) / (1024 * 1024), 1)

        return {
            "total_cameras": active_cameras_count or 0,
            "ai_enabled": active_cameras_count or 0,
            "critical_alerts": critical_alerts,
            "uptime": "99.9%",
            "system_health": {
                "cpu_usage": round(cpu_usage, 1),
                "gpu_usage": 0,
                "ram_usage": round(ram.percent, 1),
                "storage_usage": round(disk.percent, 1),
                "network_bandwidth": net_mbps
            }
        }
