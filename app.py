import os
import hmac
import hashlib
import json
import time
import requests
from flask import Flask, request, jsonify
from database import init_db, save_event

app = Flask(__name__)

SECRET = os.environ.get("BRIDGE_SECRET", "")
TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

with app.app_context():
    init_db()

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "online"})

@app.route("/webhook", methods=["POST"])
def webhook():
    body = request.get_data()

    timestamp = request.headers.get("X-Bridge-Timestamp", "")
    signature = request.headers.get("X-Bridge-Signature", "")

    try:
        ts = int(timestamp)
    except ValueError:
        return jsonify({"error": "Invalid timestamp"}), 401

    if abs(time.time() - ts) > 300:
        return jsonify({"error": "Expired request"}), 401

    signed = timestamp.encode() + b"." + body
    expected = hmac.new(
        SECRET.encode(),
        signed,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        return jsonify({"error": "Invalid signature"}), 401

    try:
        data = json.loads(body)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    if any(k in data for k in ("message", "phone", "otp", "code")):
        return jsonify({"error": "Sensitive fields not accepted"}), 400

    if not data.get("event_id"):
        return jsonify({"error": "Missing event_id"}), 400

    if not save_event(data):
        return jsonify({"status": "duplicate"})

    text = (
        "IVAS Monitor\n\n"
        f"Country: {data.get('country', 'Unknown')}\n"
        f"Sender: {data.get('sender', 'Unknown')}\n"
        f"Time: {data.get('received_at', 'Unknown')}\n"
        f"Revenue: {data.get('revenue', 'Unknown')}"
    )

    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text},
            timeout=15
        )
    except Exception:
        pass

    return jsonify({"status": "success"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
