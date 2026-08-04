import threading

# Global state for the latest telemetry payload per camera
LATEST_DATA = {}

# Reentrant lock to prevent race conditions when reading/writing state
DATA_LOCK = threading.RLock()
EVENT_TTL_SECONDS = 1.0

def update_global_state(packet: dict):
    import time
    cam_id = packet["camera_id"]
    now = time.time()
    
    with DATA_LOCK:
        if packet.get("is_gesture_synthetic", False):
            # Merge gesture events into existing packet to avoid overwriting YOLO events
            if cam_id in LATEST_DATA:
                LATEST_DATA[cam_id]["events"].update(packet.get("events", {}))
            return
            
        old_packet = LATEST_DATA.get(cam_id, {})
        cached_events = old_packet.get("_cached_events", {}).copy()
        
        new_events = packet.get("events", {})
        for plugin_name, events_list in new_events.items():
            if events_list:
                cached_events[plugin_name] = {"data": events_list, "ts": now}
                
        pruned_events = {}
        for plugin_name, cache_obj in list(cached_events.items()):
            if now - cache_obj["ts"] <= EVENT_TTL_SECONDS:
                pruned_events[plugin_name] = cache_obj["data"]
                
        if old_packet and "GestureDetectionPlugin" in old_packet.get("events", {}):
            pruned_events["GestureDetectionPlugin"] = old_packet["events"]["GestureDetectionPlugin"]

        packet["events"] = pruned_events
        packet["_cached_events"] = cached_events
        LATEST_DATA[cam_id] = packet
