import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List

class AppConfig(BaseSettings):
    """
    Application configuration.
    Loads from environment variables or a .env file.
    No hardcoded values should exist in business logic.
    """
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    
    # Auth Settings
    SECRET_KEY: str = Field(
        default="supersecretkey_change_in_production",
        description="JWT Secret Key"
    )
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    
    # AI Agent Settings
    GROQ_API_KEY: str = Field(default="")
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile") # Groq's fast and smart model instead of invalid qwen
    
    
    # Database Settings
    DATABASE_URL: str = Field(
        default="postgresql://admin:admin@localhost:5432/cctv",
        description="PostgreSQL Connection String"
    )
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis Connection String"
    )
    
    # Camera Settings (comma separated if multiple)
    CAMERA_URLS: str = Field(
        default="0",
        description="Comma-separated list of RTSP URLs, video file paths, or camera indices."
    )
    
    @property
    def camera_list(self) -> List[str]:
        return [url.strip() for url in self.CAMERA_URLS.split(",") if url.strip()]
        
    CAMERA_RECONNECT_MAX_RETRIES: int = Field(default=-1)
    CAMERA_RECONNECT_DELAY_SECONDS: float = Field(default=5.0)
    FRAME_BUFFER_SIZE: int = Field(default=3)
    
    # AI Pipeline Settings
    FRAME_SKIP: int = Field(default=3)
    MODEL_PATH: str = Field(default="detection/yolo11n.pt")
    CONFIDENCE_THRESHOLD: float = Field(default=0.4)
    
    UNTRACKED_CAMERAS: List[str] = Field(
        default=["Screen Recording"],
        description="List of camera substrings that should bypass ByteTrack to avoid confidence thresholds filtering out low-conf objects (e.g. weapons)."
    )
    
    CAMERA_CONFIDENCE_THRESHOLDS: dict = Field(
        default={"Screen Recording": 0.1},
        description="Camera-specific confidence thresholds. Overrides CONFIDENCE_THRESHOLD if matched."
    )
    
    def get_confidence_for_camera(self, camera_id: str) -> float:
        for cam, conf in self.CAMERA_CONFIDENCE_THRESHOLDS.items():
            if cam in camera_id:
                return conf
        return self.CONFIDENCE_THRESHOLD
        
    def should_bypass_tracker(self, camera_id: str) -> bool:
        for cam in self.UNTRACKED_CAMERAS:
            if cam in camera_id:
                return True
        return False
    
    # Spatial Analytics Settings
    LOITERING_THRESHOLD_SECONDS: float = Field(default=10.0)
    
    # Gesture Detection Settings
    GESTURE_ENABLED: bool = Field(default=True)
    GESTURE_FPS: int = Field(default=8)
    GESTURE_CONFIDENCE: float = Field(default=0.2)
    GESTURE_MAX_HANDS: int = Field(default=4)
    GESTURE_ASSOCIATE_WITH_PERSON: bool = Field(default=True)
    
    HAND_RAISE_ENABLED_CAMERAS: List[str] = Field(
        default=["rtsp://admin:Snap@1222@192.168.1.121/stream1", "rtsp://admin:Snap@1222@192.168.1.122/stream1"],
        description="List of camera URLs that are allowed to trigger HAND_RAISE_DETECTED alerts."
    )
    
    def is_hand_raise_enabled(self, camera_id: str) -> bool:
        return camera_id in self.HAND_RAISE_ENABLED_CAMERAS or "default" in self.HAND_RAISE_ENABLED_CAMERAS
    
    # Dictionary of camera_id to list of polygon points [(x,y), (x,y), ...]
    RESTRICTED_ZONES: dict = Field(
        default={
            # Default test zone (a large square in the center of a 1080p frame)
            "default": [(400, 300), (1500, 300), (1500, 800), (400, 800)],
            # Lobby camera (121): Top Left
            "rtsp://admin:Snap@1222@192.168.1.121/stream1": [(100, 100), (600, 100), (600, 600), (100, 600)],
            # Room camera (122): No intrusion zone for the room!
            "rtsp://admin:Snap@1222@192.168.1.122/stream1": []
        }
    )
    
    def get_zone_for_camera(self, camera_id: str) -> list:
        return self.RESTRICTED_ZONES.get(camera_id, self.RESTRICTED_ZONES.get("default"))
        
    # Dictionary of camera_id to list of polygon points for Queues
    QUEUE_ZONES: dict = Field(
        default={
            # Default queue zone (left side of the frame)
            "default": [(0, 100), (300, 100), (300, 1000), (0, 1000)]
        }
    )
    
    def get_queue_zone_for_camera(self, camera_id: str) -> list:
        return self.QUEUE_ZONES.get(camera_id, self.QUEUE_ZONES.get("default"))
        
    # Dictionary of camera_id to line segment ((x1, y1), (x2, y2))
    CHECKIN_LINES: dict = Field(
        default={
            # Default vertical line down the middle of a 1080p frame
            "default": ((960, 0), (960, 1080)),
            # Lobby camera (121): Vertical line
            "rtsp://admin:Snap@1222@192.168.1.121/stream1": ((960, 0), (960, 1080)),
            # Room camera (122): Vertical line
            "rtsp://admin:Snap@1222@192.168.1.122/stream1": ((960, 0), (960, 1080))
        }
    )
    
    def get_checkin_line_for_camera(self, camera_id: str) -> tuple:
        return self.CHECKIN_LINES.get(camera_id, self.CHECKIN_LINES.get("default"))
        
    # Dictionary of camera_id to list of parking spots (each spot is a list of polygon points)
    PARKING_SPOTS: dict = Field(
        default={
            # 3 dummy spots
            "default": [
                [(1500, 800), (1600, 800), (1600, 1000), (1500, 1000)], # Spot 1
                [(1610, 800), (1710, 800), (1710, 1000), (1610, 1000)], # Spot 2
                [(1720, 800), (1820, 800), (1820, 1000), (1720, 1000)], # Spot 3
            ]
        }
    )
    
    def get_parking_spots_for_camera(self, camera_id: str) -> list:
        return self.PARKING_SPOTS.get(camera_id, self.PARKING_SPOTS.get("default"))
    
config = AppConfig()

import redis
# Global redis client for inter-process communication
redis_client = redis.Redis.from_url(config.REDIS_URL, decode_responses=True)
