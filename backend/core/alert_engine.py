import os
import requests
from loguru import logger
from typing import Dict, Any, List

from config.config import config

class AlertEngine:
    """
    Handles external notification dispatching (SMS, Email, Webhooks) for critical events.
    """
    
    def __init__(self):
        self.twilio_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.twilio_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.twilio_from = os.getenv("TWILIO_FROM_NUMBER", "")
        self.twilio_to = os.getenv("TWILIO_TO_NUMBER", "")
        
        self.sendgrid_key = os.getenv("SENDGRID_API_KEY", "")
        self.sendgrid_from = os.getenv("SENDGRID_FROM_EMAIL", "alerts@logiceye.ai")
        self.sendgrid_to = os.getenv("SENDGRID_TO_EMAIL", "admin@logiceye.ai")

    def _is_critical(self, event_type: str, alerts: List[str]) -> bool:
        """Determines if the event warrants an external notification."""
        critical_alerts = {"FIRE_DETECTED", "SMOKE_DETECTED", "WEAPON_DETECTED", "INTRUSION_DETECTED"}
        
        for alert in alerts:
            if alert in critical_alerts:
                return True
        return False

    def process_events(self, camera_id: str, events: Dict[str, Any]):
        """Scans the event payload and dispatches notifications if critical."""
        for plugin_name, data in events.items():
            if isinstance(data, dict):
                active_alerts = data.get("active_alerts", [])
                if self._is_critical("", active_alerts):
                    self.dispatch_alert(camera_id, plugin_name, active_alerts)
            elif isinstance(data, list):
                for event in data:
                    event_type = event.get("event_type")
                    if event_type and self._is_critical("", [event_type]):
                        self.dispatch_alert(camera_id, plugin_name, [event_type])

    def dispatch_alert(self, camera_id: str, plugin_name: str, alerts: List[str]):
        """Dispatches the alert using configured providers."""
        message = f"[LOGICEYE CRITICAL ALERT] Camera: {camera_id} | Plugin: {plugin_name} | Alerts: {', '.join(alerts)}"
        logger.warning(f"🚨 ALERT ENGINE TRIGGERED: {message}")
        
        # Dispatch SMS via Twilio if configured
        if self.twilio_sid and self.twilio_token and self.twilio_to:
            try:
                url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_sid}/Messages.json"
                payload = {
                    "To": self.twilio_to,
                    "From": self.twilio_from,
                    "Body": message
                }
                requests.post(url, data=payload, auth=(self.twilio_sid, self.twilio_token), timeout=3.0)
                logger.info(f"Dispatched SMS Alert to {self.twilio_to}")
            except Exception as e:
                logger.error(f"Failed to dispatch SMS alert: {e}")
                
        # Dispatch Email via SendGrid if configured
        if self.sendgrid_key and self.sendgrid_to:
            try:
                headers = {
                    "Authorization": f"Bearer {self.sendgrid_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "personalizations": [{"to": [{"email": self.sendgrid_to}]}],
                    "from": {"email": self.sendgrid_from},
                    "subject": "LogicEye Critical Alert",
                    "content": [{"type": "text/plain", "value": message}]
                }
                requests.post("https://api.sendgrid.com/v3/mail/send", json=payload, headers=headers, timeout=3.0)
                logger.info(f"Dispatched Email Alert to {self.sendgrid_to}")
            except Exception as e:
                logger.error(f"Failed to dispatch Email alert: {e}")
