import re

with open("/Users/ibm/Downloads/LogicEye-main-main-2/backend/app/plugins/fire/router.py", "r") as f:
    content = f.read()

old_func = """@fire_router.get("/events")
def get_fire_events(db: Session = Depends(get_db), limit: int = 50):
    # MOCK DATA FOR VIDEO DEMO
    import time
    now_ts = time.time()
    mock_events = []
    for i in range(8):
        mock_events.append({
            "id": 5000 + i,
            "camera_id": f"Warehouse Zone {i % 3 + 1}",
            "timestamp": now_ts - (i * 12),
            "fire_boxes": [[100 + i*5, 150, 200, 250, 0.92 + (i*0.01)]],
            "snapshot_file": None
        })
    return {"events": mock_events}"""

new_func = """@fire_router.get("/events")
def get_fire_events(db: Session = Depends(get_db), limit: int = 50):
    events_query = db.query(CameraEvent).filter(
        CameraEvent.events.op("->")("FireDetectionPlugin") != None
    ).order_by(desc(CameraEvent.timestamp)).limit(limit).all()
    
    formatted_events = []
    for e in events_query:
        plugin_events = e.events.get("FireDetectionPlugin", [])
        for pe in plugin_events:
            if pe.get("event_type") == "FIRE_DETECTED":
                formatted_events.append({
                    "id": str(e.id),
                    "camera_id": e.camera_id,
                    "timestamp": e.timestamp.timestamp(),
                    "fire_boxes": pe.get("metadata", {}).get("fire_boxes", []),
                    "snapshot_file": pe.get("snapshot_path")
                })
    
    return {"events": formatted_events[:limit]}"""

content = content.replace(old_func, new_func)

with open("/Users/ibm/Downloads/LogicEye-main-main-2/backend/app/plugins/fire/router.py", "w") as f:
    f.write(content)
