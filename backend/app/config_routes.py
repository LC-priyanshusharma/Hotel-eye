from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict
from pydantic import BaseModel

from config.config import config
from app.auth.dependencies import require_permissions

config_router = APIRouter(tags=["configuration"])

class ConfigUpdate(BaseModel):
    # A generic dict to update top-level config keys
    updates: Dict[str, Any]

@config_router.get("/api/config")
async def get_config() -> Any:
    """Get the current running configuration (excluding secrets)."""
    # Create a safe copy of config without secrets
    safe_config = config.model_dump()
    if "SECRET_KEY" in safe_config:
        del safe_config["SECRET_KEY"]
    if "GROQ_API_KEY" in safe_config:
        safe_config["GROQ_API_KEY"] = "***"
        
    return safe_config

@config_router.post("/api/config")
async def update_config(
    update_data: ConfigUpdate
) -> Any:
    """Update running configuration in memory."""
    MUTABLE_KEYS = {"CAMERA_PLUGINS", "CONFIDENCE_THRESHOLD", "FRAME_SKIP", "GESTURE_ENABLED", "TRACKER_BACKEND"}
    try:
        for key, value in update_data.updates.items():
            if key not in MUTABLE_KEYS:
                raise HTTPException(status_code=403, detail=f"Config key '{key}' is not mutable at runtime")
                
            if hasattr(config, key):
                current_val = getattr(config, key)
                if isinstance(current_val, dict) and isinstance(value, dict):
                    # Safely merge dictionary updates (like CAMERA_PLUGINS) by creating a new copy
                    # This ensures Pydantic V2 detects the change and updates model_dump()
                    new_val = current_val.copy()
                    new_val.update(value)
                    setattr(config, key, new_val)
                    if key == "CAMERA_PLUGINS":
                        config.save_plugins_state()
                        
                        from core.state import sync_camera_plugins
                        import redis, json
                        
                        for cam_id, p_list in value.items():
                            sync_camera_plugins(cam_id, p_list)
                            
                        try:
                            r = redis.Redis.from_url(config.REDIS_URL)
                            r.publish("config:plugins_updated", json.dumps(value))
                        except Exception:
                            pass
                else:
                    setattr(config, key, value)
        return {"status": "success", "message": "Configuration updated in memory"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
