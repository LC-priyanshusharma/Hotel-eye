import re

with open("/Users/ibm/Downloads/LogicEye-main-main-2/backend/app/plugins/parking/router.py", "r") as f:
    content = f.read()

old_func = """@parking_router.get("/stats")
def get_parking_stats():
    # MOCK DATA FOR VIDEO DEMO
    from datetime import datetime
    now = datetime.utcnow().isoformat() + "Z"
    
    mock_data = {
        "Parking Lot Alpha (Cam 1)": {
            "timestamp": now,
            "total_spots": 50,
            "occupied_spots": 32,
            "available_spots": 18,
            "spot_status": [(i < 32) for i in range(50)],
            "vehicle_count": 35
        },
        "Underground Level B (Cam 2)": {
            "timestamp": now,
            "total_spots": 120,
            "occupied_spots": 115,
            "available_spots": 5,
            "spot_status": [(i < 115) for i in range(120)],
            "vehicle_count": 118
        }
    }
    return {"current": mock_data}"""

new_func = """@parking_router.get("/stats")
def get_parking_stats(db: Session = Depends(get_db)):
    events = db.query(CameraEvent).filter(
        CameraEvent.events.op("->")("ParkingPlugin") != None
    ).order_by(desc(CameraEvent.timestamp)).limit(50).all()
    
    # Just return empty/initial structure because WebSockets handles the real-time update
    result = {}
    for e in events:
        if e.camera_id not in result:
            plugin_events = e.events.get("ParkingPlugin", [])
            for pe in plugin_events:
                if pe.get("event_type") == "PARKING_STATS":
                    result[e.camera_id] = {
                        "timestamp": e.timestamp.isoformat() + "Z",
                        "total_spots": pe.get("metadata", {}).get("total_spots", 0),
                        "occupied_spots": pe.get("metadata", {}).get("occupied_spots", 0),
                        "available_spots": pe.get("metadata", {}).get("available_spots", 0),
                        "spot_status": pe.get("metadata", {}).get("spot_status", []),
                        "vehicle_count": pe.get("metadata", {}).get("vehicle_count", 0)
                    }
                    break
                    
    return {"current": result}"""

content = content.replace(old_func, new_func)

with open("/Users/ibm/Downloads/LogicEye-main-main-2/backend/app/plugins/parking/router.py", "w") as f:
    f.write(content)
