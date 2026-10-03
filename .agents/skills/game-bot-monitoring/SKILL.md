---
name: game-bot-monitoring
description: >-
  Monitoring and alerting patterns for game automation bots. Covers Discord Webhooks,
  status embeds, real-time error screenshots, and daily CSV stats tracking.
---

# Game Bot Monitoring Skill

## 1. Discord Webhook Integration
Send status messages, warnings, and screenshot attachments to Discord:
```python
import requests

def send_discord_alert(webhook_url: str, title: str, description: str, image_path: str = None):
    payload = {
        "embeds": [{
            "title": title,
            "description": description,
            "color": 0x00ff88, # Green for success, 0xff0000 for error
        }]
    }
    if image_path and os.path.exists(image_path):
        with open(image_path, "rb") as f:
            requests.post(webhook_url, data={"payload_json": json.dumps(payload)}, files={"file": f})
    else:
        requests.post(webhook_url, json=payload)
```

## 2. CSV Session & Stats Tracker
Record every run for analysis:
- Timestamp
- Mode (Tower Hard, Champion, etc.)
- Waves Cleared
- Win / Loss status
- Duration (seconds)
