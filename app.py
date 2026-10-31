import os
import hmac
import hashlib
import json
import time
import httpx

from fastapi import FastAPI, Request, HTTPException
from database import init_db, save_event

app = FastAPI()

SECRET = os.environ["BRIDGE_SECRET"]
TG_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

@app.on_event("startup")
async def startup():
    init_db()

@app.get("/")
async def health():
    return {"status": "online"}

@app.post("/webhook")
async def webhook(request: Request):
    body = await request.body()

    timestamp = request.headers.get("X-Bridge-Timestamp", "")
    signature = request.headers.get("X-Bridge-Signature", "")

    try:
        ts = int(timestamp)
    except ValueError:
        raise HTTPException(401, "Invalid timestamp")

    if abs(time.time() - ts) > 300:
        raise HTTPException(401, "Expired request")

    signed = timestamp.encode() + b"." + body

    expected = hmac.new(
        SECRET.encode(),
        signed,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        raise HTTPException(401, "Invalid signature")

    try:
        data = json.loads(body)
    except Exception:
        raise HTTPException(400, "Invalid JSON")

    # Chỉ chấp nhận metadata thống kê, loại bỏ các trường nhạy cảm
    if any(k in data for k in ("message", "phone", "otp", "code")):
        raise HTTPException(400, "Sensitive fields not accepted")

    if not data.get("event_id"):
        raise HTTPException(400, "Missing event_id")

    if not save_event(data):
        return {"status": "duplicate"}

    text = (
        "IVAS Monitor\n\n"
        f"Country: {data.get('country', 'Unknown')}\n"
        f"Sender: {data.get('sender', 'Unknown')}\n"
        f"Time: {data.get('received_at', 'Unknown')}\n"
        f"Revenue: {data.get('revenue', 'Unknown')}"
    )

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text}
        )
        response.raise_for_status()

    return {"status": "success"}
  
