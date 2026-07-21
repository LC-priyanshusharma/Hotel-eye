from database.session import SessionLocal
from models.models import CameraEvent

class EventService:
    @staticmethod
    def get_latest_events():
        """Returns the latest historical events from the database."""
        db = SessionLocal()
        try:
            known_cameras = db.query(CameraEvent.camera_id).distinct().all()
            result = []
            
            for (cam_id,) in known_cameras:
                # Fetch up to 20 to ensure we bypass duplicates
                cam_events = db.query(CameraEvent).filter(CameraEvent.camera_id == cam_id).order_by(CameraEvent.timestamp.desc()).limit(20).all()
                
                valid_cam_events = []
                last_desc = None
                for e in cam_events:
                    event_type = e.events.get("event_type", "info")
                    description = e.events.get("description", "Analytics Update")
                    snapshot_file = e.events.get("snapshot_file", None)
                    
                    if "EnterpriseSafetyPlugin" in e.events:
                        active_alerts = e.events["EnterpriseSafetyPlugin"].get("active_alerts", [])
                        if "FIRE_DETECTED" in active_alerts:
                            event_type = "danger"
                            description = "Fire Detected"
                        elif "SMOKE_DETECTED" in active_alerts:
                            event_type = "danger"
                            description = "Smoke Detected"
                            
                    if "WeaponDetectionPlugin" in e.events:
                        active_alerts = e.events["WeaponDetectionPlugin"].get("active_alerts", [])
                        new_snapshots = e.events["WeaponDetectionPlugin"].get("new_snapshots", [])
                        if "WEAPON_DETECTED" in active_alerts:
                            event_type = "danger"
                            description = "Weapon Detected"
                            if new_snapshots:
                                snapshot_file = new_snapshots[0]
                            
                    if "IntrusionDetectionPlugin" in e.events:
                        for event in e.events["IntrusionDetectionPlugin"]:
                            if event.get("event_type") == "INTRUSION_DETECTED":
                                event_type = "warning"
                                description = "Zone Intrusion Detected"
                                snapshot_file = event.get("snapshot_path")
                                break
                            
                    if "AttendanceDetectionPlugin" in e.events:
                        for event in e.events["AttendanceDetectionPlugin"]:
                            if event.get("event_type") in ["CHECK_IN", "CHECK_OUT"]:
                                action = event["metadata"].get("action")
                                emp = event["metadata"].get("employee_id")
                                description = f"Emp {emp} {action}"
                                event_type = "success" if action == "CHECK IN" else "info"
                                break
                            
                    if "PeopleCountingPlugin" in e.events and description == "Analytics Update":
                        for event in e.events["PeopleCountingPlugin"]:
                            if event.get("event_type") == "PERSON_COUNT":
                                count = event["metadata"].get("current_people_in_frame", 0)
                                if count > 0:
                                    description = f"Person Count: {count}"
                                    event_type = "info"
                                break
                            
                    if "GestureDetectionPlugin" in e.events:
                        gesture_data = e.events["GestureDetectionPlugin"]
                        active_alerts = gesture_data.get("active_alerts", [])
                        if "HAND_RAISE_DETECTED" in active_alerts:
                            event_type = "info"
                            description = "Hand Raise Detected"
                            if gesture_data.get("snapshot_file"):
                                snapshot_file = "/" + gesture_data.get("snapshot_file")
                        elif "GESTURE_DETECTED" in active_alerts:
                            gesture_events = gesture_data.get("gesture_events", [])
                            if gesture_events:
                                top_gesture = gesture_events[0].get("gesture", "Unknown")
                                event_type = "info"
                                description = f"Gesture: {top_gesture}"
                                if gesture_data.get("snapshot_file"):
                                    snapshot_file = "/" + gesture_data.get("snapshot_file")

                    # Skip spammy analytics updates at the API level
                    if description == "Analytics Update":
                        continue
                        
                    # Deduplicate consecutive identical events to prevent starvation
                    if description == last_desc:
                        continue
                    last_desc = description

                    valid_cam_events.append({
                        "id": e.id,
                        "timestamp": e.timestamp.isoformat(),
                        "camera_id": e.camera_id,
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
        db = SessionLocal()
        critical_alerts = 0
        try:
            # Just grab the last 1000 events to estimate recent critical alerts
            events = db.query(CameraEvent).order_by(CameraEvent.timestamp.desc()).limit(1000).all()
            for e in events:
                if "EnterpriseSafetyPlugin" in e.events:
                    active = e.events["EnterpriseSafetyPlugin"].get("active_alerts", [])
                    if "FIRE_DETECTED" in active or "SMOKE_DETECTED" in active:
                        critical_alerts += 1
                if "WeaponDetectionPlugin" in e.events:
                    active = e.events["WeaponDetectionPlugin"].get("active_alerts", [])
                    if "WEAPON_DETECTED" in active:
                        critical_alerts += 1
        finally:
            db.close()

        return {
            "total_cameras": active_cameras_count or 1,
            "ai_enabled": active_cameras_count or 1,
            "critical_alerts": critical_alerts,
            "uptime": "99.9%",
            "system_health": {
                "cpu_usage": 45,
                "gpu_usage": 15,
                "ram_usage": 60,
                "storage_usage": 30,
                "network_bandwidth": 150
            }
        }
