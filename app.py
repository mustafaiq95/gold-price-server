from flask import Flask, jsonify, Response
from threading import Thread, Lock
import websocket
import json
import os
import time
from datetime import datetime, timezone

app = Flask(__name__)

TWELVE_API_KEY = os.environ.get("TWELVE_API_KEY")
SYMBOL = os.environ.get("SYMBOL", "XAU/USD")

price_lock = Lock()

latest_price = {
    "symbol": SYMBOL,
    "price": None,
    "source": "twelvedata.com",
    "status": "starting",
    "updated_at": None,
    "raw": None
}


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def set_status(status, error=None, raw=None):
    global latest_price
    with price_lock:
        latest_price["status"] = status
        latest_price["updated_at"] = now_utc()
        if error is not None:
            latest_price["error"] = str(error)
        if raw is not None:
            latest_price["raw"] = raw


def update_latest_price(price, raw=None):
    global latest_price
    with price_lock:
        latest_price = {
            "symbol": SYMBOL,
            "price": price,
            "source": "twelvedata.com",
            "status": "ok",
            "updated_at": now_utc(),
            "raw": raw
        }


def on_open(ws):
    print("Connected to Twelve Data WebSocket", flush=True)

    subscribe_message = {
        "action": "subscribe",
        "params": {
            "symbols": SYMBOL
        }
    }

    ws.send(json.dumps(subscribe_message))
    print(f"Subscribed to {SYMBOL}", flush=True)
    set_status("connected")


def on_message(ws, message):
    try:
        data = json.loads(message)
        print(data, flush=True)

        # Twelve Data may send system/status messages without price.
        price = data.get("price")

        if price is not None:
            update_latest_price(price, data)
        elif data.get("event") in ["subscribe-status", "heartbeat"]:
            set_status("waiting_for_price", raw=data)
        elif data.get("status") == "error":
            set_status("error", error=data.get("message", data), raw=data)

    except Exception as e:
        print(f"Message error: {e}", flush=True)
        set_status("message_error", error=e)


def on_error(ws, error):
    print(f"WebSocket error: {error}", flush=True)
    set_status("error", error=error)


def on_close(ws, close_status_code, close_msg):
    print("WebSocket closed", close_status_code, close_msg, flush=True)
    set_status("closed", raw={"code": close_status_code, "message": close_msg})


def websocket_worker():
    if not TWELVE_API_KEY:
        set_status("missing_api_key", error="Add TWELVE_API_KEY in Render Environment Variables")
        return

    while True:
        try:
            ws_url = f"wss://ws.twelvedata.com/v1/quotes/price?apikey={TWELVE_API_KEY}"

            ws = websocket.WebSocketApp(
                ws_url,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )

            ws.run_forever(ping_interval=20, ping_timeout=10)

        except Exception as e:
            print(f"WebSocket worker error: {e}", flush=True)
            set_status("worker_error", error=e)

        time.sleep(1)


@app.route("/")
def home():
    return jsonify({
        "message": "Gold price server is running",
        "price_endpoint": "/price",
        "live_page": "/live",
        "stream_endpoint": "/stream",
        "source": "Twelve Data WebSocket",
        "symbol": SYMBOL
    })


@app.route("/price")
def price():
    with price_lock:
        return jsonify(latest_price)


@app.route("/stream")
def stream():
    def event_stream():
        while True:
            with price_lock:
                data = dict(latest_price)
            yield f"data: {json.dumps(data)}\n\n"
            time.sleep(1)

    return Response(event_stream(), mimetype="text/event-stream")


@app.route("/live")
def live():
    return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>XAU/USD Live Price</title>
    <style>
        body {
            margin: 0;
            background: #0b0f19;
            color: white;
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        .box {
            background: #111827;
            padding: 35px;
            border-radius: 20px;
            min-width: 320px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.35);
        }
        .symbol {
            font-size: 24px;
            color: #aaa;
        }
        .price {
            font-size: 54px;
            font-weight: bold;
            margin: 20px 0;
        }
        .time, .source {
            color: #999;
            font-size: 14px;
            margin-top: 8px;
        }
        .status {
            margin-top: 15px;
            color: #00ff99;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="box">
        <div class="symbol" id="symbol">XAU/USD</div>
        <div id="price" class="price">Loading...</div>
        <div id="time" class="time"></div>
        <div id="source" class="source">Twelve Data WebSocket</div>
        <div id="status" class="status">Connecting...</div>
    </div>

    <script>
        const symbolEl = document.getElementById("symbol");
        const priceEl = document.getElementById("price");
        const timeEl = document.getElementById("time");
        const statusEl = document.getElementById("status");

        const source = new EventSource("/stream");

        source.onmessage = function(event) {
            const data = JSON.parse(event.data);
            symbolEl.textContent = data.symbol || "XAU/USD";

            if (data.price !== null && data.price !== undefined) {
                priceEl.textContent = data.price;
            }

            timeEl.textContent = data.updated_at || "";
            statusEl.textContent = data.status || "unknown";
        };

        source.onerror = function() {
            statusEl.textContent = "reconnecting";
        };
    </script>
</body>
</html>
"""


Thread(target=websocket_worker, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
