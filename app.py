from flask import Flask, jsonify, Response
import requests
import os
import time
import json
from datetime import datetime, timezone

app = Flask(__name__)


def get_tradingview_price():
    try:
        url = "https://scanner.tradingview.com/symbol"

        params = {
            "symbol": "OANDA:XAUUSD",
            "fields": "close,change,change_abs,open,high,low"
        }

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.tradingview.com/symbols/XAUUSD/",
            "Origin": "https://www.tradingview.com"
        }

        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        price = data.get("close")

        return {
            "symbol": "OANDA:XAUUSD",
            "price": price,
            "change": data.get("change"),
            "change_abs": data.get("change_abs"),
            "open": data.get("open"),
            "high": data.get("high"),
            "low": data.get("low"),
            "source": "tradingview.com",
            "status": "ok" if price is not None else "price_not_found",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        return {
            "symbol": "OANDA:XAUUSD",
            "price": None,
            "source": "tradingview.com",
            "status": "error",
            "error": str(e),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }


@app.route("/")
def home():
    return jsonify({
        "message": "Gold price server is running",
        "price_endpoint": "/price",
        "live_page": "/live",
        "stream_endpoint": "/stream"
    })


@app.route("/price")
def price():
    return jsonify(get_tradingview_price())


@app.route("/stream")
def stream():
    def event_stream():
        while True:
            data = get_tradingview_price()
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
    <title>XAUUSD Live Price</title>
    <style>
        body {
            background: #0b0f19;
            color: white;
            font-family: Arial, sans-serif;
            text-align: center;
            padding-top: 80px;
        }
        .box {
            background: #111827;
            display: inline-block;
            padding: 40px;
            border-radius: 20px;
            min-width: 320px;
        }
        .symbol {
            font-size: 26px;
            color: #aaa;
        }
        .price {
            font-size: 56px;
            font-weight: bold;
            margin: 20px 0;
        }
        .time {
            color: #999;
            font-size: 14px;
        }
        .status {
            margin-top: 15px;
            color: #00ff99;
        }
    </style>
</head>
<body>
    <div class="box">
        <div class="symbol">OANDA:XAUUSD</div>
        <div id="price" class="price">Loading...</div>
        <div id="time" class="time"></div>
        <div id="status" class="status">Connecting...</div>
    </div>

    <script>
        const priceEl = document.getElementById("price");
        const timeEl = document.getElementById("time");
        const statusEl = document.getElementById("status");

        const source = new EventSource("/stream");

        source.onmessage = function(event) {
            const data = JSON.parse(event.data);

            if (data.status === "ok" && data.price !== null) {
                priceEl.textContent = data.price;
                timeEl.textContent = data.updated_at;
                statusEl.textContent = "LIVE";
            } else {
                statusEl.textContent = data.status;
            }
        };

        source.onerror = function() {
            statusEl.textContent = "Reconnecting...";
        };
    </script>
</body>
</html>
"""


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
