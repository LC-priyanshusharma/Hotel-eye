import threading
from typing import Dict, Any

class TelemetryCache:
    def __init__(self):
        self.lock = threading.Lock()
        self.data: Dict[str, Any] = {}
        
    def update(self, edge_id: str, payload: Dict[str, Any]):
        with self.lock:
            self.data[edge_id] = payload
            
    def get_all(self) -> Dict[str, Any]:
        with self.lock:
            return self.data.copy()

telemetry_cache = TelemetryCache()
