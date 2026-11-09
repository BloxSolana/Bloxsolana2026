import os
import re
import json
import html
import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import libsql_experimental as libsql

logger = logging.getLogger("FAST_IVAS")

# CẤU HÌNH DATABASE (Turso / SQLite)
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL", "").strip()
TURSO_AUTH_TOKEN   = os.getenv("TURSO_AUTH_TOKEN", "").strip()
SQLITE_PATH        = os.getenv("SQLITE_PATH", "fast_ivas.db")
ADMIN_ID           = int(os.getenv("ADMIN_ID", "0") or 0)

DB_TIMEOUT_SECONDS = 10.0
DB_WORKERS         = 4
db_executor        = ThreadPoolExecutor(max_workers=DB_WORKERS)
VN_TZ              = timezone(timedelta(hours=7))

# ==================== CÁC HÀM TIỆN ÍCH DÙNG CHUNG ====================
def now(): return datetime.now(VN_TZ)
def now_text(): return now().isoformat(timespec="seconds")
def unix_now(): return int(time.time())

def usd(milli):
    milli = int(milli); s = "-" if milli < 0 else ""; milli = abs(milli)
    return f"{s}${milli // 1000}.{milli % 1000:03d}"

def safe(v, limit=500): return html.escape(str(v or "")[:limit])
def is_admin(uid): return int(uid) == ADMIN_ID

def mask_phone(phone):
    if not phone or len(phone) < 7: return phone
    return phone[:3] + "*" * (len(phone) - 6) + phone[-3:]

# ==================== CÁC HẰNG SỐ QUỐC GIA ====================
COUNTRY_CODES = {
    "84": ("Vietnam", "🇻🇳"), "62": ("Indonesia", "🇮🇩"), "60": ("Malaysia", "🇲🇾"),
    "65": ("Singapore", "🇸🇬"), "66": ("Thailand", "🇹🇭"), "63": ("Philippines", "🇵🇭"),
    "95": ("Myanmar", "🇲🇲"), "855": ("Cambodia", "🇰🇭"), "856": ("Laos", "🇱🇦"),
    "1": ("United States", "🇺🇸"), "44": ("United Kingdom", "🇬🇧"), "7": ("Russia", "🇷🇺"),
    "81": ("Japan", "🇯🇵"), "82": ("South Korea", "🇰🇷"), "86": ("China", "🇨🇳"),
    "91": ("India", "🇮🇳"), "92": ("Pakistan", "🇵🇰"), "880": ("Bangladesh", "🇧🇩"),
    "234": ("Nigeria", "🇳🇬"), "254": ("Kenya", "🇰🇪"), "27": ("South Africa", "🇿🇦"),
    "20": ("Egypt", "🇪🇬"), "212": ("Morocco", "🇲🇦"), "213": ("Algeria", "🇩🇿"),
    "216": ("Tunisia", "🇹🇳"), "218": ("Libya", "🇱🇾"), "249": ("Sudan", "🇸🇩"),
    "251": ("Ethiopia", "🇪🇹"), "255": ("Tanzania", "🇹🇿"), "256": ("Uganda", "🇺🇬"),
    "263": ("Zimbabwe", "🇿🇼"), "260": ("Zambia", "🇿🇲"), "233": ("Ghana", "🇬🇭"),
    "221": ("Senegal", "🇸🇳"), "224": ("Guinea", "🇬🇳"), "231": ("Liberia", "🇱🇷"),
    "232": ("Sierra Leone", "🇸🇱"), "225": ("Ivory Coast", "🇨🇮"), "237": ("Cameroon", "🇨🇲"),
    "243": ("DR Congo", "🇨🇩"), "242": ("Congo", "🇨🇬"), "241": ("Gabon", "🇬🇦"),
    "235": ("Chad", "🇹🇩"), "227": ("Niger", "🇳🇪"), "223": ("Mali", "🇲🇱"),
    "226": ("Burkina Faso", "🇧🇫"), "228": ("Togo", "🇹🇬"), "229": ("Benin", "🇧🇯"),
    "220": ("Gambia", "🇬🇲"), "222": ("Mauritania", "🇲🇷"), "245": ("Guinea-Bissau", "🇬🇼"),
    "30": ("Greece", "🇬🇷"), "31": ("Netherlands", "🇳🇱"), "32": ("Belgium", "🇧🇪"),
    "33": ("France", "🇫🇷"), "34": ("Spain", "🇪🇸"), "36": ("Hungary", "🇭🇺"),
    "39": ("Italy", "🇮🇹"), "40": ("Romania", "🇷🇴"), "41": ("Switzerland", "🇨🇭"),
    "43": ("Austria", "🇦🇹"), "45": ("Denmark", "🇩🇰"), "46": ("Sweden", "🇸🇪"),
    "47": ("Norway", "🇳🇴"), "48": ("Poland", "🇵🇱"), "49": ("Germany", "🇩🇪"),
    "351": ("Portugal", "🇵🇹"), "352": ("Luxembourg", "🇱🇺"), "353": ("Ireland", "🇮🇪"),
    "358": ("Finland", "🇫🇮"), "370": ("Lithuania", "🇱🇹"), "371": ("Latvia", "🇱🇻"),
    "372": ("Estonia", "🇪🇪"), "380": ("Ukraine", "🇺🇦"), "420": ("Czechia", "🇨🇿"),
    "421": ("Slovakia", "🇸🇰"), "90": ("Turkey", "🇹🇷"), "972": ("Israel", "🇮🇱"),
    "971": ("UAE", "🇦🇪"), "966": ("Saudi Arabia", "🇸🇦"), "974": ("Qatar", "🇶🇦"),
    "965": ("Kuwait", "🇰🇼"), "968": ("Oman", "🇴🇲"), "973": ("Bahrain", "🇧🇭"),
    "962": ("Jordan", "🇯🇴"), "961": ("Lebanon", "🇱🇧"), "964": ("Iraq", "🇮🇶"),
    "98": ("Iran", "🇮🇷"), "93": ("Afghanistan", "🇦🇫"), "94": ("Sri Lanka", "🇱🇰"),
    "977": ("Nepal", "🇳🇵"), "975": ("Bhutan", "🇧🇹"), "960": ("Maldives", "🇲🇻"),
    "673": ("Brunei", "🇧🇳"), "670": ("Timor-Leste", "🇹🇱"), "61": ("Australia", "🇦🇺"),
    "64": ("New Zealand", "🇳🇿"), "52": ("Mexico", "🇲🇽"), "55": ("Brazil", "🇧🇷"),
    "54": ("Argentina", "🇦🇷"), "56": ("Chile", "🇨🇱"), "57": ("Colombia", "🇨🇴"),
    "58": ("Venezuela", "🇻🇪"), "51": ("Peru", "🇵🇪"), "593": ("Ecuador", "🇪🇨"),
    "591": ("Bolivia", "🇧🇴"), "595": ("Paraguay", "🇵🇾"), "598": ("Uruguay", "🇺🇾"),
    "509": ("Haiti", "🇭🇹"), "244": ("Angola", "🇦🇴"), "267": ("Botswana", "🇧🇼"),
    "266": ("Lesotho", "🇱🇸"), "261": ("Madagascar", "🇲🇬"), "258": ("Mozambique", "🇲🇿"),
    "264": ("Namibia", "🇳🇦"), "970": ("Palestine", "🇵🇸"), "250": ("Rwanda", "🇷🇼"),
    "252": ("Somalia", "🇸🇴"), "998": ("Uzbekistan", "🇺🇿"), "967": ("Yemen", "🇾🇪")
}
SORTED_PREFIXES = sorted(COUNTRY_CODES.keys(), key=len, reverse=True)

ISO_MAP = {
    "VN": "Vietnam", "TL": "Timor-Leste", "HT": "Haiti", "SN": "Senegal", "SD": "Sudan", "AF": "Afghanistan",
    "ID": "Indonesia", "PH": "Philippines", "MM": "Myanmar", "KH": "Cambodia", "LA": "Laos", "MY": "Malaysia",
    "TH": "Thailand", "BD": "Bangladesh", "PK": "Pakistan", "NG": "Nigeria", "GH": "Ghana", "KE": "Kenya",
    "ZM": "Zambia", "CM": "Cameroon", "CI": "Ivory Coast", "UG": "Uganda", "TZ": "Tanzania", "ZW": "Zimbabwe",
    "EG": "Egypt", "MA": "Morocco", "DZ": "Algeria", "TN": "Tunisia", "LY": "Libya", "ML": "Mali",
    "BF": "Burkina Faso", "NE": "Niger", "TD": "Chad", "SO": "Somalia", "ET": "Ethiopia", "MG": "Madagascar",
    "MZ": "Mozambique", "AO": "Angola", "NA": "Namibia", "BW": "Botswana", "ZA": "South Africa", "LR": "Liberia",
    "SL": "Sierra Leone", "GN": "Guinea", "GW": "Guinea-Bissau", "GM": "Gambia", "MR": "Mauritania", "TG": "Togo",
    "BJ": "Benin", "GA": "Gabon", "CG": "Congo", "RW": "Rwanda", "NO": "Norway"
}

FALLBACK_COUNTRIES = {
    "Vietnam": "84XXX", "Liberia": "231XXX", "Guinea": "2246XXX", "Sierra Leone": "2327XXX", "Indonesia": "62XXX",
    "Cambodia": "855XXX", "Myanmar": "9596XXX", "Zambia": "260XXX", "Tanzania": "255XXX", "Lesotho": "2666XXX",
    "Mozambique": "2588XXX", "Yemen": "9677XXX", "Algeria": "2135XXX", "Tunisia": "2162XXX", "Nigeria": "234XXX",
    "Nepal": "977XXX", "Afghanistan": "9370XXX", "Lebanon": "961XXX", "Morocco": "2126XXX", "Libya": "2189XXX",
    "Madagascar": "2613XXX", "Ethiopia": "2519XXX", "Senegal": "2217XXX", "Zimbabwe": "2637XXX", "Norway": "47XXX",
    "Egypt": "2012XXX", "Palestine": "9725XXX", "Uzbekistan": "998XXX", "Sudan": "2491XXX", "Cameroon": "237XXX",
    "Benin": "2290XXX", "Mali": "223XXX", "Ghana": "233XXX", "Kenya": "254XXX", "Uganda": "256XXX", "Rwanda": "250XXX",
    "Chad": "235XXX", "Niger": "227XXX", "Somalia": "252XXX", "Angola": "244XXX", "Botswana": "267XXX", "Namibia": "264XXX",
    "Gabon": "241XXX", "Congo": "242XXX", "Togo": "228XXX", "Burkina Faso": "226XXX", "Mauritania": "222XXX", "Gambia": "220XXX",
    "Guinea-Bissau": "245XXX", "Maldives": "960XXX"
}

def get_country_flag(c):
    if not c: return "🌐"
    for k, v in COUNTRY_CODES.items():
        if v[0].lower() == str(c).lower(): return v[1]
    return "🌐"

def detect_otp_platform(full_sms):
    if not full_sms: return "Other"
    sms = full_sms.lower()
    for name, kw in {"TikTok": ["tiktok"], "Facebook": ["facebook", "fb"], "Instagram": ["instagram"], "Threads": ["threads"], "Google": ["google", "gmail"], "Telegram": ["telegram"], "WhatsApp": ["whatsapp"], "Zalo": ["zalo"], "Twitter": ["twitter"], "Shopee": ["shopee"], "Apple": ["apple"], "Microsoft": ["microsoft"]}.items():
        if any(k in sms for k in kw): return name
    return "Other"

def get_network_icon(net):
    net = str(net).upper()
    return "📘" if "FACEBOOK" in net else "📸" if "INSTAGRAM" in net else "💬" if "WHATSAPP" in net else "✈️" if "TELEGRAM" in net else "📱" if "TIKTOK" in net else "🧵" if "THREADS" in net else "🇬" if "GOOGLE" in net else "🐦" if "TWITTER" in net or "X" in net else "🌐"

# ==================== CÁC HÀM TƯƠNG TÁC DATABASE ====================
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
    try:
        return await asyncio.wait_for(loop.run_in_executor(db_executor, _sync_db_exec, query, params, fetch), timeout=DB_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        logger.error("DB Timeout!")
        return None

async def init_db():
    await db_exec("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, usd_milli INTEGER NOT NULL DEFAULT 0, wallet_ton TEXT, referrer INTEGER, joined_at TEXT, language TEXT DEFAULT 'vi')")
    await db_exec("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, request_id TEXT UNIQUE, provider TEXT, platform TEXT, phone TEXT, country TEXT, operator TEXT, range_code TEXT, status TEXT NOT NULL DEFAULT 'PENDING', otp_code TEXT, full_sms TEXT, reward_milli INTEGER DEFAULT 0, created_at TEXT, expires_at TEXT, updated_at TEXT)")
    await db_exec("CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, amount INTEGER NOT NULL, tx_type TEXT, note TEXT, created_at TEXT)")
    await db_exec("CREATE TABLE IF NOT EXISTS withdrawals (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, amount_milli INTEGER NOT NULL, wallet_ton TEXT, status TEXT NOT NULL DEFAULT 'PENDING', reject_reason TEXT, tx_hash TEXT, created_at TEXT, processed_at TEXT)")
    await db_exec("CREATE TABLE IF NOT EXISTS basha_numbers (id INTEGER PRIMARY KEY AUTOINCREMENT, phone TEXT UNIQUE NOT NULL, country TEXT NOT NULL, flag TEXT NOT NULL, added_at TEXT)")
    await db_exec("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    
    await db_exec("CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id)")
    await db_exec("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")

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

async def get_user(uid): 
    return await db_exec("SELECT * FROM users WHERE user_id=?", (uid,), fetch="one")

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
            db.execute("INSERT INTO transactions (user_id, amount, tx_type, note, created_at) VALUES (?, ?, ?, ?, ?)", (uid, amount_milli, tx_type, note, now_text()))
            db.commit()
            return True, new
        except Exception as e:
            db.rollback(); return False, str(e)
        finally: db.close()
    loop = asyncio.get_running_loop()
    return await asyncio.wait_for(loop.run_in_executor(db_executor, _tx), timeout=DB_TIMEOUT_SECONDS)

async def clean_old_orders(uid):
    res = await db_exec("SELECT COUNT(*) as c FROM orders WHERE user_id=?", (uid,), fetch="one")
    if res and res["c"] > 1000: # MAX_HISTORY_RECORDS
        to_delete = res["c"] - 1000
        await db_exec("DELETE FROM orders WHERE id IN (SELECT id FROM orders WHERE user_id=? ORDER BY id ASC LIMIT ?)", (uid, to_delete))
