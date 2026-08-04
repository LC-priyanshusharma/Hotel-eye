from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from loguru import logger

from core.state import LATEST_DATA, DATA_LOCK
from services.event_service import EventService
from database.session import SessionLocal
from database.models.models import CameraEvent
from database.repositories.event_repository import EventRepository

router = APIRouter(tags=["System"])

@router.get("/")
def health_check():
    return {"status": "running", "active_cameras": list(LATEST_DATA.keys())}

@router.get("/events")
def get_events(
    camera_id: str = None, 
    start_date: str = None, 
    end_date: str = None, 
    severity: str = None, 
    category: str = None
):
    """Returns the latest historical events from the database."""
    events = EventService.get_latest_events(
        camera_id=camera_id, 
        start_date=start_date, 
        end_date=end_date, 
        severity=severity, 
        category=category
    )
    return JSONResponse(content=events)

@router.get("/analytics/dashboard")
def get_analytics_dashboard():
    stats = EventService.get_dashboard_stats(len(LATEST_DATA))
    return stats

class ManualEvent(BaseModel):
    camera_id: str
    event_type: str
    description: str
    
@router.post("/events/manual")
def post_manual_event(event: ManualEvent):
    db = SessionLocal()
    try:
        repo = EventRepository(db)
        new_event = CameraEvent(
            camera_id=event.camera_id,
            events={
                "event_type": event.event_type,
                "description": event.description
            }
        )
        repo.add(new_event)
        return {"status": "success"}
    finally:
        db.close()

@router.get("/api/intrusions")
def get_intrusions():
    """Returns historical intrusion events with snapshots from the DB."""
    db = SessionLocal()
    try:
        repo = EventRepository(db)
        events = repo.get_recent_events(limit=1000)
        
        intrusions = []
        for e in events:
            spatial_events = e.events.get("IntrusionDetectionPlugin", [])
            for event in spatial_events:
                if event.get("event_type") == "INTRUSION_DETECTED":
                    intrusions.append({
                        "id": e.id,
                        "camera_id": e.camera_id,
                        "timestamp": e.timestamp.isoformat(),
                        "track_id": event["metadata"].get("track_id"),
                        "snapshot": "/" + event.get("snapshot_path", ""),
                        "zone": event["metadata"].get("zone")
                    })
                
        return {"intrusions": intrusions}
    finally:
        db.close()

@router.get("/report/pdf")
def get_report_pdf():
    # Dummy PDF endpoint
    return JSONResponse(content={"status": "not implemented"}, status_code=404)

@router.get("/api/system/ip")
def get_system_ip():
    import socket
    try:
        # Create a dummy socket to determine the local IP used for outbound connections
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # We don't actually connect to 8.8.8.8, it just helps the OS determine the route
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
        return {"ip": local_ip}
    except Exception as e:
        return {"ip": "127.0.0.1"}

# AI Agent Chat Endpoint
class ChatRequest(BaseModel):
    message: str
    camera_id: str = ""

@router.post("/api/chat")
def chat_with_agent(req: ChatRequest):
    try:
        from agents.chat_agent import agent
        response = agent.chat(req.message, req.camera_id)
        return {"response": response}
    except Exception as e:
        logger.error(f"Chat API error: {e}")
        return {"response": f"Sorry, I encountered an error: {str(e)}"}
