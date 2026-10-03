import os
import json
import requests
from typing import Optional
from datetime import datetime


class Notifier:
    """Discord Webhook Notification & Screenshot Dispatcher."""

    def __init__(self, config: dict):
        self.enabled = config.get("discord", {}).get("enabled", False)
        self.webhook_url = config.get("discord", {}).get("webhook_url", "")

    def send(self, title: str, message: str, color: int = 0x00ff88,
             screenshot_path: Optional[str] = None):
        """Send embed notification to Discord."""
        if not self.enabled or not self.webhook_url:
            return

        payload = {
            "embeds": [{
                "title": title,
                "description": message,
                "color": color,
                "timestamp": datetime.utcnow().isoformat()
            }]
        }

        try:
            if screenshot_path and os.path.exists(screenshot_path):
                with open(screenshot_path, "rb") as f:
                    requests.post(
                        self.webhook_url,
                        data={"payload_json": json.dumps(payload)},
                        files={"file": f},
                        timeout=10
                    )
            else:
                requests.post(self.webhook_url, json=payload, timeout=10)
        except Exception as e:
            print(f"[Notifier] ส่ง Discord ไม่สำเร็จ: {e}")
