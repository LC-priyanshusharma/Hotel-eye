from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List

class GarbageConfig(BaseSettings):
    """
    Configuration settings specific to the Garbage Detection module.
    """
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    
    GARBAGE_CATEGORIES: List[str] = Field(
        default=["plastic bottle", "paper", "cup", "bag", "wrapper", "can", "garbage pile", "other waste"],
        description="List of garbage categories to detect"
    )
    GARBAGE_CONFIDENCE_THRESHOLD: float = Field(
        default=0.4, 
        description="Minimum confidence to consider a garbage detection valid"
    )
    GARBAGE_DWELL_TIME_SECONDS: float = Field(
        default=30.0,
        description="Seconds a piece of garbage must remain stationary before triggering an alert"
    )
    GARBAGE_ENABLED_CAMERAS: List[str] = Field(
        default=[],
        description="List of camera URLs where garbage detection is enabled. Empty means all cameras."
    )

garbage_config = GarbageConfig()
