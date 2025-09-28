import websocket
import json
import threading
from typing import Dict, List


class WebSocketPriceFetcher:
    def __init__(self, symbols: List[str]):
        self.ws_url = "wss://ws-feed.exchange.coinbase.com"
        self.prices: Dict[str, float] = {}
        self.symbols = symbols
        self.ws = None
        self.thread = None

    def on_message(self, ws, message):
        data = json.loads(message)
        if data.get("type") == "ticker":
            symbol = data.get("product_id")
            price = data.get("price")
            if symbol and price:
                self.prices[symbol] = float(price)

    def on_error(self, ws, error):
        print(f"WebSocket error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print("WebSocket connection closed")

    def on_open(self, ws):
        subscribe_message = {
            "type": "subscribe",
            "product_ids": self.symbols,
            "channels": ["ticker"],
        }
        ws.send(json.dumps(subscribe_message))

    def start(self):
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )
        self.thread = threading.Thread(target=self.ws.run_forever)
        self.thread.daemon = True
        self.thread.start()

    def get_prices(self) -> Dict[str, float]:
        return self.prices
