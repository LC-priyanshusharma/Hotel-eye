import re

with open("/Users/ibm/Downloads/LogicEye-main-main-2/backend/app/plugins/attendance/router.py", "r") as f:
    content = f.read()

old_func = """@attendance_router.get("/stats")
def get_attendance_stats():
    # MOCK DATA FOR VIDEO DEMO
    import time
    now_ts = time.time()
    
    logs = [
        {"time": now_ts - 300, "action": "CHECK IN", "employee": "John Doe"},
        {"time": now_ts - 900, "action": "CHECK IN", "employee": "Sarah Smith"},
        {"time": now_ts - 120, "action": "CHECK IN", "employee": "Michael Chen"},
        {"time": now_ts - 1800, "action": "CHECK OUT", "employee": "Emily Davis"},
        {"time": now_ts - 60, "action": "UNKNOWN", "employee": "Unknown Person"},
    ]
    
    mock_data = {
        "Main Entrance (Cam 1)": {
            "timestamp": now.isoformat() + "Z",
            "authorized_employees_in_frame": [
                {"id": "EMP-001", "name": "John Doe", "confidence": 0.98},
                {"id": "EMP-099", "name": "Michael Chen", "confidence": 0.95}
            ],
            "unauthorized_count": 1,
            "attendance_logs": logs
        },
        "Back Door (Cam 2)": {
            "timestamp": now.isoformat() + "Z",
            "authorized_employees_in_frame": [],
            "unauthorized_count": 0,
            "attendance_logs": []
        }
    }
    return {"current": mock_data}"""

new_func = """@attendance_router.get("/stats")
def get_attendance_stats(db: Session = Depends(get_db)):
    events = db.query(CameraEvent).filter(
        CameraEvent.events.op("->")("AttendancePlugin") != None
    ).order_by(desc(CameraEvent.timestamp)).limit(50).all()
    
    logs_by_cam = {}
    for e in events:
        if e.camera_id not in logs_by_cam:
            logs_by_cam[e.camera_id] = []
        plugin_events = e.events.get("AttendancePlugin", [])
        for pe in plugin_events:
            if pe.get("event_type") in ["CHECK IN", "CHECK OUT", "UNAUTHORIZED"]:
                logs_by_cam[e.camera_id].append({
                    "time": e.timestamp.timestamp(),
                    "action": pe.get("event_type"),
                    "employee": pe.get("metadata", {}).get("person_name", "Unknown Person")
                })
    
    # We rely on WebSocket for live state, this just provides recent logs per camera
    # We will format it to match the expected schema but leave live arrays empty.
    result = {}
    for cam, logs in logs_by_cam.items():
        result[cam] = {
            "authorized_employees_in_frame": [], # Handled by WebSocket on frontend
            "unauthorized_count": 0,             # Handled by WebSocket on frontend
            "attendance_logs": logs[:10]
        }
    return {"current": result}"""

content = content.replace(old_func, new_func)

with open("/Users/ibm/Downloads/LogicEye-main-main-2/backend/app/plugins/attendance/router.py", "w") as f:
    f.write(content)
