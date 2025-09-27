import os
import json
import requests
from typing import Optional

class SlackAdapter:
    def __init__(self):
        self.webhook_url: Optional[str] = os.environ.get("SLACK_WEBHOOK_URL")

    def send(self, title: str, message: str, style: str = "info") -> None:
        if not self.webhook_url:
            return

        color_map = {
            "red": "#ff0000",
            "green": "#00ff00",
            "yellow": "#ffff00",
            "blue": "#0000ff",
            "magenta": "#ff00ff",
            "cyan": "#00ffff",
            "white": "#ffffff",
        }

        payload = {
            "attachments": [
                {
                    "color": color_map.get(style, "#ffffff"),
                    "title": title,
                    "text": message,
                }
            ]
        }

        try:
            headers = {"Content-Type": "application/json"}
            requests.post(self.webhook_url, data=json.dumps(payload), headers=headers, timeout=5)
        except Exception:
            pass
