import os
import time
import hmac
import hashlib
import logging
import json
import httpx

SOURCE_API_URL = os.getenv("AUTHORIZED_API_URL", "").strip()
SOURCE_API_TOKEN = os.getenv("AUTHORIZED_API_TOKEN", "").strip()

BRIDGE_URL = os.getenv("BRIDGE_URL", "").strip()
BRIDGE_SECRET = os.getenv("BRIDGE_SECRET", "").encode("utf-8")

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "20"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "15"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

session = httpx.Client()

def sign_payload(body: bytes, timestamp: str) -> str:
    message = timestamp.encode("utf-8") + b"." + body
    return hmac.new(
        BRIDGE_SECRET,
        message,
        hashlib.sha256
    ).hexdigest()

def fetch_messages():
    if not SOURCE_API_URL or not SOURCE_API_TOKEN:
        raise RuntimeError("Missing authorized source API configuration")

    response = session.get(
        SOURCE_API_URL,
        headers={
            "Authorization": f"Bearer {SOURCE_API_TOKEN}",
            "Accept": "application/json",
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()

    if data.get("status") != "success":
        logging.warning("Source API did not return success status")
        return []

    messages = data.get("messages", [])
    if not isinstance(messages, list):
        logging.warning("Invalid messages field")
        return []

    return messages

def extract_metadata(item: dict):
    if not isinstance(item, dict):
        return None
    event_id = item.get("id")
    if not event_id:
        return None

    return {
        "event_id": str(event_id),
        "country": str(item.get("country") or ""),
        "sender": str(item.get("sender") or ""),
        "received_at": str(item.get("received_at") or ""),
        "revenue": str(item.get("revenue") or ""),
    }

def send_to_bridge(event: dict):
    if not BRIDGE_URL or not BRIDGE_SECRET:
        raise RuntimeError("Missing Bridge configuration")

    body = json.dumps(
        event,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    timestamp = str(int(time.time()))
    signature = sign_payload(body, timestamp)

    response = session.post(
        BRIDGE_URL,
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Bridge-Timestamp": timestamp,
            "X-Bridge-Signature": signature,
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

def poll_once():
    messages = fetch_messages()
    logging.info("Fetched %d metadata records", len(messages))

    for item in messages:
        event = extract_metadata(item)
        if event is None:
            continue
        try:
            send_to_bridge(event)
            logging.info(
                "Forwarded metadata: id=%s country=%s sender=%s",
                event["event_id"],
                event["country"],
                event["sender"],
            )
        except Exception:
            logging.exception(
                "Bridge delivery failed for event %s",
                event["event_id"],
            )

def main():
    logging.info("Metadata poller started")
    while True:
        try:
            poll_once()
        except Exception:
            logging.exception("Polling cycle failed")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
  
