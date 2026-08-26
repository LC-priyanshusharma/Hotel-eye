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
        
        from config.config import config
        allowed = config.get_allowed_plugins(cam_id)
        if allowed is not None:
            for p in list(cached_events.keys()):
                if p not in allowed:
                    del cached_events[p]

        new_events = packet.get("events", {})
        for plugin_name, events_list in new_events.items():
            if events_list and (allowed is None or plugin_name in allowed):
                cached_events[plugin_name] = {"data": events_list, "ts": now}
                
        PERSISTENT_PLUGINS = {"PeopleCountingPlugin", "CartonCountingPlugin", "ParkingAnalyticsPlugin"}
        pruned_events = {}
        for plugin_name, cache_obj in list(cached_events.items()):
            if allowed is None or plugin_name in allowed:
                # Persistent stats plugins stay alive while enabled; transient alerts use TTL
                if plugin_name in PERSISTENT_PLUGINS or (now - cache_obj["ts"] <= EVENT_TTL_SECONDS):
                    pruned_events[plugin_name] = cache_obj["data"]
                
        if old_packet and "GestureDetectionPlugin" in old_packet.get("events", {}):
            if allowed is None or "GestureDetectionPlugin" in allowed:
                pruned_events["GestureDetectionPlugin"] = old_packet["events"]["GestureDetectionPlugin"]

        packet["events"] = pruned_events
        packet["_cached_events"] = cached_events
        LATEST_DATA[cam_id] = packet

def sync_camera_plugins(cam_id: str, allowed: list):
    """Immediately synchronizes global state when plugins are toggled in dynamic plugin manager."""
    with DATA_LOCK:
        if cam_id in LATEST_DATA:
            old_events = LATEST_DATA[cam_id].get("events", {})
            cached_events = LATEST_DATA[cam_id].get("_cached_events", {})
            if allowed is not None:
                for p in list(old_events.keys()):
                    if p not in allowed:
                        del old_events[p]
                for p in list(cached_events.keys()):
                    if p not in allowed:
                        del cached_events[p]
