# Gold Price Server

Simple Flask API that reads XAUUSD price from TradingView's scanner endpoint and exposes it at:

```txt
/price
```

## Run locally

```bash
pip install -r requirements.txt
python app.py
```

Open:

```txt
http://localhost:8080/price
```

## Deploy to Google Cloud Run

```bash
gcloud run deploy gold-price-server --source . --region us-central1 --allow-unauthenticated
```
