# File: database.py
import os, re, json, html, asyncio, logging, time
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import libsql_experimental as libsql

logger = logging.getLogger("FAST_IVAS")
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL", "").strip()
TURSO_AUTH_TOKEN   = os.getenv("TURSO_AUTH_TOKEN", "").strip()
SQLITE_PATH        = os.getenv("SQLITE_PATH", "fast_ivas.db")
ADMIN_ID           = int(os.getenv("ADMIN_ID", "0") or 0)
DB_TIMEOUT_SECONDS = 10.0
DB_WORKERS         = 4
db_executor        = ThreadPoolExecutor(max_workers=DB_WORKERS)
VN_TZ              = timezone(timedelta(hours=7))

def now(): return datetime.now(VN_TZ)
def now_text(): return now().isoformat(timespec="seconds")
def unix_now(): return int(time.time())
def safe(v, limit=500): return html.escape(str(v or "")[:limit])
def is_admin(uid): return int(uid) == ADMIN_ID

def detect_otp_platform(full_sms):
    if not full_sms: return "Other"
    sms = full_sms.lower()
    for name, kw in {"TikTok": ["tiktok"], "Facebook": ["facebook", "fb"], "Instagram": ["instagram"], "Threads": ["threads"], "Google": ["google", "gmail"], "Telegram": ["telegram"], "WhatsApp": ["whatsapp"], "Zalo": ["zalo"], "Twitter": ["twitter"], "Shopee": ["shopee"], "Apple": ["apple"], "Microsoft": ["microsoft"]}.items():
        if any(k in sms for k in kw): return name
    return "Other"

def get_network_icon(net):
    net = str(net).upper()
    return "📘" if "FACEBOOK" in net else "📸" if "INSTAGRAM" in net else "💬" if "WHATSAPP" in net else "✈️" if "TELEGRAM" in net else "📱" if "TIKTOK" in net else "🧵" if "THREADS" in net else "🇬" if "GOOGLE" in net else "🐦" if "TWITTER" in net or "X" in net else "🌐"

COUNTRY_CODES = {"84": ("Vietnam", "🇻🇳"), "62": ("Indonesia", "🇮🇩"), "60": ("Malaysia", "🇲🇾"), "1": ("United States", "🇺🇸"), "44": ("UK", "🇬🇧")}
SORTED_PREFIXES = sorted(COUNTRY_CODES.keys(), key=len, reverse=True)
ISO_MAP = {"VN": "Vietnam", "ID": "Indonesia"}
FALLBACK_COUNTRIES = {"Vietnam": "84XXX", "Indonesia": "62XXX"}
def get_country_flag(c):
    if not c: return "🌐"
    for k, v in COUNTRY_CODES.items():
        if v[0].lower() == str(c).lower(): return v[1]
    return "🌐"

def open_db():
    if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
        try: return libsql.connect(SQLITE_PATH, sync_url=TURSO_DATABASE_URL, auth_token=TURSO_AUTH_TOKEN)
        except Exception: pass
    import sqlite3
    conn = sqlite3.connect(SQLITE_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn

def row_to_dict(cursor, row):
    if row is None: return None
    if hasattr(row, 'keys'): return dict(row)
    columns = [column[0] for column in (cursor.description or [])]
    return dict(zip(columns, row))

def _sync_db_exec(query, params=(), fetch=None):
    db = None
    try:
        db = open_db()
        cursor = db.execute(query, params or ())
        if fetch == "one": return row_to_dict(cursor, cursor.fetchone())
        if fetch == "all": return [row_to_dict(cursor, r) for r in cursor.fetchall()]
        db.commit()
        return cursor.lastrowid if hasattr(cursor, 'lastrowid') else True
    finally:
        if db:
            try: db.close()
            except: pass

async def db_exec(query, params=(), fetch=None):
    loop = asyncio.get_running_loop()
    try: return await asyncio.wait_for(loop.run_in_executor(db_executor, _sync_db_exec, query, params, fetch), timeout=DB_TIMEOUT_SECONDS)
    except asyncio.TimeoutError: return None

async def init_db():
    await db_exec("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, usd_milli INTEGER NOT NULL DEFAULT 0, wallet_ton TEXT, referrer INTEGER, joined_at TEXT, language TEXT DEFAULT 'vi')")
    await db_exec("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, request_id TEXT UNIQUE, provider TEXT, platform TEXT, phone TEXT, country TEXT, operator TEXT, range_code TEXT, status TEXT NOT NULL DEFAULT 'PENDING', otp_code TEXT, full_sms TEXT, reward_milli INTEGER DEFAULT 0, created_at TEXT, expires_at TEXT, updated_at TEXT)")
    await db_exec("CREATE TABLE IF NOT EXISTS withdrawals (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, amount_milli INTEGER NOT NULL, wallet_ton TEXT, status TEXT NOT NULL DEFAULT 'PENDING', reject_reason TEXT, tx_hash TEXT, created_at TEXT, processed_at TEXT)")
    await db_exec("CREATE TABLE IF NOT EXISTS basha_numbers (id INTEGER PRIMARY KEY AUTOINCREMENT, phone TEXT UNIQUE NOT NULL, country TEXT NOT NULL, flag TEXT NOT NULL, added_at TEXT)")
    await db_exec("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    await db_exec("CREATE TABLE IF NOT EXISTS mail_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, address TEXT NOT NULL, created_at TEXT)")

async def get_setting(key, default=None):
    res = await db_exec("SELECT value FROM settings WHERE key=?", (key,), fetch="one")
    return res["value"] if res else default

async def set_setting(key, value):
    await db_exec("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))

async def register_user(tg_user, referrer=None):
    res = await db_exec("SELECT user_id FROM users WHERE user_id=?", (tg_user.id,), fetch="one")
    if res:
        await db_exec("UPDATE users SET username=?, first_name=? WHERE user_id=?", (tg_user.username, tg_user.first_name or "User", tg_user.id))
        return False
    if referrer == tg_user.id: referrer = None
    await db_exec("INSERT INTO users (user_id, username, first_name, referrer, joined_at, language) VALUES (?, ?, ?, ?, ?, 'vi')", (tg_user.id, tg_user.username, tg_user.first_name or "User", referrer, now_text()))
    return True

async def get_user(uid): return await db_exec("SELECT * FROM users WHERE user_id=?", (uid,), fetch="one")

async def change_usd(uid, amount_milli, tx_type, note):
    def _tx():
        db = open_db()
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT usd_milli FROM users WHERE user_id=?", (uid,)).fetchone()
            if not row: db.rollback(); return False, "User not found."
            new = int(row[0]) + int(amount_milli)
            if new < 0: db.rollback(); return False, "Insufficient balance."
            db.execute("UPDATE users SET usd_milli=? WHERE user_id=?", (new, uid))
            db.commit()
            return True, new
        except Exception as e:
            db.rollback(); return False, str(e)
        finally: db.close()
    loop = asyncio.get_running_loop()
    return await asyncio.wait_for(loop.run_in_executor(db_executor, _tx), timeout=DB_TIMEOUT_SECONDS)

async def clean_old_orders(uid):
    res = await db_exec("SELECT COUNT(*) as c FROM orders WHERE user_id=?", (uid,), fetch="one")
    if res and res["c"] > 1000:
        to_delete = res["c"] - 1000
        await db_exec("DELETE FROM orders WHERE id IN (SELECT id FROM orders WHERE user_id=? ORDER BY id ASC LIMIT ?)", (uid, to_delete))
