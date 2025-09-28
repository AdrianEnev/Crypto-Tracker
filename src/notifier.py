from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from typing import Dict, Optional
import os
import json
import requests
from .slack_adapter import SlackAdapter

console = Console()


class Notifier:
    def __init__(self):
        self.last_alerts = {}
        self.webhook_url: Optional[str] = os.environ.get("NOTIFIER_WEBHOOK_URL")
        self.webhook_level: str = os.environ.get("NOTIFIER_WEBHOOK_LEVEL", "info").lower()
        self.slack_adapter = SlackAdapter() if os.environ.get("SLACK_WEBHOOK_URL") else None

    def check_thresholds(
        self,
        coin_id: str,
        coin_name: str,
        current_price: Optional[float],
        threshold: float,
        silent: bool = False,
    ):
        """Check if price is below threshold and show alert if needed.
        When silent=True, do not print panels, only update internal state.
        """
        if current_price is None:
            if not silent:
                console.print(
                    f"[yellow]⚠ Could not fetch price for {coin_name} (${threshold:,.2f} threshold)[/]"
                )
            return False

        if current_price < threshold:
            # Only alert if we haven't alerted recently for this coin
            if self.last_alerts.get(coin_id) != "below":
                if not silent:
                    self._send_alert(coin_name, current_price, threshold, "below")
                self.last_alerts[coin_id] = "below"
            return True
        else:
            # Reset alert state if price is back above threshold
            if self.last_alerts.get(coin_id) == "below":
                if not silent:
                    self._send_recovery(coin_name, current_price, threshold)
                self.last_alerts[coin_id] = "above"
            return False

    def _send_alert(self, coin_name: str, price: float, threshold: float, alert_type: str):
        """Display alert in the console."""
        if alert_type == "below":
            alert_text = Text.assemble(
                "⚠ ",
                (f"{coin_name} ", "bold"),
                (f"${price:,.2f}", "red"),
                " is below threshold ",
                (f"${threshold:,.2f}", "bold"),
            )
            panel = Panel(
                alert_text, title="[bold]Price Alert[/bold]", border_style="red", padding=(1, 2)
            )
            console.print(panel)

    def _send_recovery(self, coin_name: str, price: float, threshold: float):
        """Notify when price recovers above threshold."""
        recovery_text = Text.assemble(
            "✓ ",
            (f"{coin_name} ", "bold"),
            (f"${price:,.2f}", "green"),
            " has recovered above threshold ",
            (f"${threshold:,.2f}", "bold"),
        )
        console.print(
            Panel(
                recovery_text,
                title="[bold]Price Recovery[/bold]",
                border_style="green",
                padding=(1, 2),
            )
        )

    def clear_alerts(self, coin_id: str):
        """Clear alert state for a coin."""
        if coin_id in self.last_alerts:
            del self.last_alerts[coin_id]

    # Generic operational alert (console panel). Can be extended to Slack/webhooks later.
    def alert(
        self, title: str, message: str, style: str = "yellow", severity: str = "info"
    ) -> None:
        try:
            panel = Panel(
                Text(message), title=f"[bold]{title}[/bold]", border_style=style, padding=(1, 2)
            )
            console.print(panel)
            # Optional webhook post
            if self.slack_adapter and self._should_send_webhook(severity):
                self.slack_adapter.send(title, message, style)
            elif self.webhook_url and self._should_send_webhook(severity):
                try:
                    payload = {"title": title, "message": message, "style": style}
                    headers = {"Content-Type": "application/json"}
                    requests.post(
                        self.webhook_url, data=json.dumps(payload), headers=headers, timeout=5
                    )
                except Exception:
                    pass
        except Exception:
            # Fallback to plain print
            console.print(f"[{style}]{title}: {message}[/]")

    def _should_send_webhook(self, severity: str) -> bool:
        levels = {"debug": 0, "info": 1, "warning": 2, "error": 3}
        return levels.get(severity, 1) >= levels.get(self.webhook_level, 1)

    def set_webhook(self, url: Optional[str]) -> None:
        try:
            self.webhook_url = url
        except Exception:
            self.webhook_url = None
