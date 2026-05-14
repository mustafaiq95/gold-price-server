from flask import Flask, jsonify
from threading import Thread
import time
import requests
import os
from datetime import datetime, timezone

app = Flask(__name__)

gold_price = {
    "symbol": "OANDA:XAUUSD",
    "price": "0.0",
    "source": "tradingview.com",
    "status": "starting",
    "updated_at": None
}


def fetch_gold_price():
    global gold_price

    while True:
        try:
            url = "https://scanner.tradingview.com/symbol"

            params = {
                "symbol": "OANDA:XAUUSD",
                "fields": "close,change,change_abs,open,high,low,volume"
            }

            headers = {
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.tradingview.com/symbols/XAUUSD/",
                "Origin": "https://www.tradingview.com"
            }

            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=15
            )

            response.raise_for_status()
            data = response.json()

            price = data.get("close")

            if price is not None:
                gold_price = {
                    "symbol": "OANDA:XAUUSD",
                    "price": str(price),
                    "change": data.get("change"),
                    "change_abs": data.get("change_abs"),
                    "open": data.get("open"),
                    "high": data.get("high"),
                    "low": data.get("low"),
                    "volume": data.get("volume"),
                    "source": "tradingview.com",
                    "status": "ok",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                print(f"Updated gold price from TradingView: {price}", flush=True)
            else:
                gold_price["status"] = "price_not_found"
                gold_price["error"] = "TradingView response did not include close price"
                print("Price not found in TradingView response.", flush=True)
                print(data, flush=True)

        except Exception as e:
            gold_price["status"] = "error"
            gold_price["error"] = str(e)
            print(f"Error fetching TradingView price: {e}", flush=True)

        time.sleep(1)


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Gold price server is running",
        "price_endpoint": "/price",
        "symbol": "OANDA:XAUUSD"
    })


@app.route("/price", methods=["GET"])
def get_price():
    return jsonify(gold_price)


# Start background price updater when app starts.
Thread(target=fetch_gold_price, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
