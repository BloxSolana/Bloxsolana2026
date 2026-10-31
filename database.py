import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "bridge.db")

def init_db():
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                country TEXT,
                sender TEXT,
                received_at TEXT,
                revenue REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

def save_event(event):
    with sqlite3.connect(DB_PATH) as db:
        cursor = db.execute("""
            INSERT OR IGNORE INTO events
            (event_id, country, sender, received_at, revenue)
            VALUES (?, ?, ?, ?, ?)
        """, (
            event["event_id"],
            event.get("country"),
            event.get("sender"),
            event.get("received_at"),
            event.get("revenue")
        ))
        return cursor.rowcount == 1
      
