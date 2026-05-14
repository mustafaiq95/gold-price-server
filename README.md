# Gold Price Server - Twelve Data

Flask server for live XAU/USD price using Twelve Data WebSocket.

## Render settings

Build Command:

```bash
pip install -r requirements.txt
```

Start Command:

```bash
gunicorn app:app
```

## Environment Variables

Add this in Render:

```text
TWELVE_API_KEY=your_twelve_data_api_key
```

Optional:

```text
SYMBOL=XAU/USD
```

## Endpoints

- `/` status
- `/price` latest price as JSON
- `/live` live browser page
- `/stream` server-sent events stream
