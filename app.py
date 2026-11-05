import os
import re
import json
import html
import asyncio
import logging
import random
from datetime import datetime, timedelta, timezone
from aiohttp import web

import aiohttp
import libsql_experimental as libsql
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand, BotCommandScopeChat, BotCommandScopeDefault, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest

# =====================================================
# CONFIG
# =====================================================
BOT_TOKEN      = "8622066775:AAEB1CZhA0CKBFlmA6CEx4zHNzMXGZqjrFg" # Nhớ thay token mới của bro vào đây
ADMIN_ID       = 6726769296
OTP_GROUP_ID   = -1004341368656
OTP_GROUP_URL  = "https://t.me/LIVEOTPIVAS"
MAIN_CHANNEL_URL = "https://t.me/FastNode_1"

# Cấu hình MK Network (Nguồn 1)
MK_API_KEY     = "badacaa33d287233567a49db" 
MK_API_BASE    = "https://mknetworkbd.com/api/v3/public"

# Cấu hình Number Panel (Nguồn 2)
NP_API_KEY     = "np_live_lrRtdKcOeg-syi8UCpmaA_idYmBZY0zbpwl5P--gF-g"
NP_API_BASE    = "https://numberpanel.tech"

TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL", "")
TURSO_AUTH_TOKEN   = os.getenv("TURSO_AUTH_TOKEN", "")

ORDER_LIFETIME_MINUTES = 15
REWARD_MILLI_PER_OTP   = 2    # $0.002
MIN_WITHDRAW_MILLI     = 1000 # $1.000
MAX_HISTORY_RECORDS    = 100  # Tối đa 100 số
HISTORY_PER_PAGE       = 8    # 8 số 1 trang

MK_POLL_ENABLED = True
MK_POLL_MIN_SEC = 10 
MK_POLL_MAX_SEC = 30
MK_POLL_BATCH   = 100

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FAST_IVAS")

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp  = Dispatcher()

BOT_USERNAME = ""

# Định nghĩa múi giờ Việt Nam (UTC+7)
VN_TZ = timezone(timedelta(hours=7))

# Danh sách cờ quốc gia
COUNTRY_FLAGS = {
    "Vietnam": "🇻🇳", "Liberia": "🇱🇷", "Guinea": "🇬🇳", "Sierra Leone": "🇸🇱",
    "Indonesia": "🇮🇩", "Cambodia": "🇰🇭", "Myanmar": "🇲🇲", "Zambia": "🇿🇲",
    "Tanzania": "🇹🇿", "Lesotho": "🇱🇸", "Mozambique": "🇲🇿", "Yemen": "🇾🇪",
    "Algeria": "🇩🇿", "Tunisia": "🇹🇳", "Nigeria": "🇳🇬", "Nepal": "🇳🇵",
    "Afghanistan": "🇦🇫", "Lebanon": "🇱🇧", "Morocco": "🇲🇦", "Libya": "🇱🇾",
    "Madagascar": "🇲🇬", "Ethiopia": "🇪🇹", "Senegal": "🇸🇳", "Zimbabwe": "🇿🇼",
    "Norway": "🇳🇴", "Egypt": "🇪🇬", "Palestine": "🇵🇸", "Uzbekistan": "🇺🇿",
    "Sudan": "🇸🇩", "Cameroon": "🇨🇲", "Benin": "🇧🇯", "Mali": "🇲🇱",
    "Ghana": "🇬🇭", "Kenya": "🇰🇪", "Uganda": "🇺🇬", "Rwanda": "🇷🇼",
    "Chad": "🇹🇩", "Niger": "🇳🇪", "Somalia": "🇸🇴", "Angola": "🇦🇴",
    "Botswana": "🇧🇼", "Namibia": "🇳🇦", "Gabon": "🇬🇦", "Congo": "🇨🇬",
    "Togo": "🇹🇬", "Burkina Faso": "🇧🇫", "Mauritania": "🇲🇷", "Gambia": "🇬🇲",
    "Guinea-Bissau": "🇬🇼", "Maldives": "🇲🇻"
}

FALLBACK_COUNTRIES = {
    "Vietnam": "84XXX", "Liberia": "231XXX", "Guinea": "2246XXX",
    "Sierra Leone": "2327XXX", "Indonesia": "62XXX", "Cambodia": "855XXX",
    "Myanmar": "9596XXX", "Zambia": "260XXX", 
    "Tanzania": "255XXX", "Lesotho": "2666XXX", "Mozambique": "2588XXX", 
    "Yemen": "9677XXX", "Algeria": "2135XXX", "Tunisia": "2162XXX", 
    "Nigeria": "234XXX", "Nepal": "977XXX", "Afghanistan": "9370XXX", 
    "Lebanon": "961XXX", "Morocco": "2126XXX", "Libya": "2189XXX",
    "Madagascar": "2613XXX", "Ethiopia": "2519XXX", "Senegal": "2217XXX", 
    "Zimbabwe": "2637XXX", "Norway": "47XXX", "Egypt": "2012XXX", 
    "Palestine": "9725XXX", "Uzbekistan": "998XXX", "Sudan": "2491XXX", 
    "Cameroon": "237XXX", "Benin": "2290XXX", "Mali": "223XXX", 
    "Ghana": "233XXX", "Kenya": "254XXX", "Uganda": "256XXX", 
    "Rwanda": "250XXX", "Chad": "235XXX", "Niger": "227XXX", 
    "Somalia": "252XXX", "Angola": "244XXX", "Botswana": "267XXX", 
    "Namibia": "264XXX", "Gabon": "241XXX", "Congo": "242XXX", 
    "Togo": "228XXX", "Burkina Faso": "226XXX", "Mauritania": "222XXX", 
    "Gambia": "220XXX", "Guinea-Bissau": "245XXX", "Maldives": "960XXX"
}

def get_country_flag(country_name):
    if not country_name: return "🌐"
    if country_name in COUNTRY_FLAGS: return COUNTRY_FLAGS[country_name]
    for k, v in COUNTRY_FLAGS.items():
        if k.lower() in str(country_name).lower(): return v
    return "🌐"

def get_network_icon(net):
    net = str(net).upper()
    if "FACEBOOK" in net: return "📘"
    if "INSTAGRAM" in net: return "📸"
    if "WHATSAPP" in net: return "💬"
    if "TELEGRAM" in net: return "✈️"
    if "TIKTOK" in net: return "🎵"
    if "THREADS" in net: return "🧵"
    if "GOOGLE" in net or "GMAIL" in net: return "🇬"
    if "TWITTER" in net or "X" in net: return "🐦"
    return "🌐"

ADMIN_PENDING_APPROVE = {} 
MSG_TO_DELETE = {}
_mk_poller = None

# =====================================================
# HELPERS
# =====================================================
def now():      return datetime.now(VN_TZ)
def now_text(): return now().isoformat(timespec="seconds")

def usd(milli):
    milli = int(milli); s = "-" if milli < 0 else ""; milli = abs(milli)
    return f"{s}${milli // 1000}.{milli % 1000:03d}"

def safe(v, limit=500): return html.escape(str(v or "")[:limit])
def is_admin(uid):      return int(uid) == ADMIN_ID

def mask_phone(phone):
    if not phone or len(phone) < 7: return phone
    return phone[:3] + "*" * (len(phone) - 6) + phone[-3:]

def status_text(s):
    return {
        "PENDING":   "⏳ Pending",
        "EXPIRED":   "⌛ Expired",
        "COMPLETED": "✅ Received",
        "FAILED":    "❌ Failed",
        "APPROVED":  "✅ Approved",
        "REJECTED":  "❌ Rejected",
        "CANCELLED": "🚫 Cancelled by User"
    }.get(s, s)

def user_link(uid, name):
    n = html.escape(name or str(uid))[:32]
    return f'<a href="tg://user?id={uid}">{n}</a>'

async def safe_delete_msg(chat_id, message_id, delay=0):
    if delay > 0: await asyncio.sleep(delay)
    try: await bot.delete_message(chat_id, message_id)
    except Exception: pass

def track_msg(chat_id, message_id):
    if chat_id not in MSG_TO_DELETE: MSG_TO_DELETE[chat_id] = []
    MSG_TO_DELETE[chat_id].append(message_id)
    while len(MSG_TO_DELETE[chat_id]) > 2:
        old_msg = MSG_TO_DELETE[chat_id].pop(0)
        asyncio.create_task(safe_delete_msg(chat_id, old_msg))

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def detect_otp_platform(full_sms):
    if not full_sms: return "Other"
    sms_lower = full_sms.lower()
    platforms = {
        "Facebook": ["facebook", "fb-", "fb:"],
        "Instagram": ["instagram", "ig-"],
        "Threads": ["threads"],
        "Google": ["google", "gmail"],
        "Telegram": ["telegram"],
        "WhatsApp": ["whatsapp"],
        "TikTok": ["tiktok"],
        "Zalo": ["zalo"],
        "Twitter/X": ["twitter", "x.com"],
        "Shopee": ["shopee"],
        "Grab": ["grab"],
        "Apple": ["apple", "icloud"],
        "Microsoft": ["microsoft", "outlook"]
    }
    for name, keywords in platforms.items():
        if any(kw in sms_lower for kw in keywords):
            return name
    return "Other"

def fmt_date(iso_str):
    if not iso_str: return "N/A"
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc).astimezone(VN_TZ)
        else:
            dt = dt.astimezone(VN_TZ)
        return dt.strftime("%d/%m %H:%M")
    except:
        return iso_str[:16].replace("T", " ")

# =====================================================
# DATABASE
# =====================================================
def get_db():
    if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
        try:
            return libsql.connect("local_replica.db", sync_url=TURSO_DATABASE_URL, auth_token=TURSO_AUTH_TOKEN)
        except Exception as e:
            logger.error(f"DB connection error: {e}. Using local.")
            return libsql.connect("local.db")
    return libsql.connect("local.db")

async def init_db():
    db = get_db()
    db.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, usd_milli INTEGER NOT NULL DEFAULT 0, wallet_ton TEXT, referrer INTEGER, joined_at TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, request_id TEXT UNIQUE, provider TEXT DEFAULT 'MK', platform TEXT, phone TEXT, country TEXT, operator TEXT, range_code TEXT, status TEXT NOT NULL DEFAULT 'PENDING', otp_code TEXT, full_sms TEXT, reward_milli INTEGER NOT NULL DEFAULT 0, msg_id INTEGER, created_at TEXT, expires_at TEXT, updated_at TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, amount INTEGER NOT NULL, tx_type TEXT, note TEXT, created_at TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS withdrawals (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, amount_milli INTEGER NOT NULL, wallet_ton TEXT, status TEXT NOT NULL DEFAULT 'PENDING', reject_reason TEXT, tx_hash TEXT, proof_photo TEXT, created_at TEXT, processed_at TEXT)")
    try: db.execute("ALTER TABLE withdrawals ADD COLUMN reject_reason TEXT")
    except: pass
    try: db.execute("ALTER TABLE withdrawals ADD COLUMN tx_hash TEXT")
    except: pass
    try: db.execute("ALTER TABLE withdrawals ADD COLUMN proof_photo TEXT")
    except: pass
    try: db.execute("ALTER TABLE orders ADD COLUMN provider TEXT DEFAULT 'MK'")
    except: pass
    try: db.execute("ALTER TABLE orders ADD COLUMN platform TEXT")
    except: pass
    db.commit(); db.close()

# =====================================================
# HÀM DB
# =====================================================
async def register_user(tg_user, referrer=None):
    db = get_db()
    try:
        res = db.execute("SELECT user_id FROM users WHERE user_id=?", (tg_user.id,)).fetchone()
        name = tg_user.first_name or "User"
        if res:
            db.execute("UPDATE users SET username=?, first_name=? WHERE user_id=?", (tg_user.username, name, tg_user.id))
            db.commit(); return False
        if referrer == tg_user.id: referrer = None
        db.execute("INSERT INTO users (user_id, username, first_name, usd_milli, referrer, joined_at) VALUES (?, ?, ?, 0, ?, ?)", (tg_user.id, tg_user.username, name, referrer, now_text()))
        db.commit(); return True
    finally: db.close()

async def get_user(uid):
    db = get_db()
    try:
        cursor = db.execute("SELECT * FROM users WHERE user_id=?", (uid,))
        row = cursor.fetchone()
        if row: return dict_factory(cursor, row)
        return None
    finally: db.close()

async def set_wallet_ton(uid, wallet_ton):
    db = get_db()
    try:
        db.execute("UPDATE users SET wallet_ton=? WHERE user_id=?", (wallet_ton, uid))
        db.commit()
    finally: db.close()

async def change_usd(uid, amount_milli, tx_type, note):
    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT usd_milli FROM users WHERE user_id=?", (uid,)).fetchone()
        if not row: db.rollback(); return False, "User not found."
        new = int(row[0]) + int(amount_milli)
        if new < 0: db.rollback(); return False, "Insufficient balance."
        db.execute("UPDATE users SET usd_milli=? WHERE user_id=?", (new, uid))
        db.execute("INSERT INTO transactions (user_id, amount, tx_type, note, created_at) VALUES (?, ?, ?, ?, ?)", (uid, amount_milli, tx_type, note, now_text()))
        db.commit(); return True, new
    finally: db.close()

async def create_withdrawal(uid, amount_milli, wallet_ton):
    db = get_db()
    try:
        cur = db.execute("INSERT INTO withdrawals (user_id, amount_milli, wallet_ton, status, created_at) VALUES (?, ?, ?, 'PENDING', ?)", (uid, amount_milli, wallet_ton, now_text()))
        db.commit(); return cur.lastrowid
    finally: db.close()

async def expire_old_orders():
    t = now_text()
    db = get_db()
    try:
        rows = db.execute("SELECT id, user_id, msg_id, phone, country FROM orders WHERE status='PENDING' AND expires_at IS NOT NULL AND expires_at<=?", (t,)).fetchall()
        for r in rows:
            oid, uid, msg_id, phone, country = r
            db.execute("UPDATE orders SET status='EXPIRED', updated_at=? WHERE id=?", (t, oid))
            if msg_id:
                try: 
                    await bot.edit_message_text(
                        chat_id=uid, message_id=msg_id, 
                        text=f"⌛ <b>ORDER EXPIRED</b>\n\nNumber: <code>{safe(phone)}</code> ({safe(country)})\nStatus: Expired.\n\nPlease choose an action below:",
                        reply_markup=expired_kb()
                    )
                except Exception: pass
        db.commit()
    finally: db.close()

# =====================================================
# KEYBOARDS
# =====================================================
def get_main_reply_kb(uid):
    keyboard = [
        [KeyboardButton(text="👤 Account"), KeyboardButton(text="🎱 Number")],
        [KeyboardButton(text="📱 Numbers 2"), KeyboardButton(text="💰 Withdraw")],
        [KeyboardButton(text="💌 Invite"), KeyboardButton(text="📊 Ranges Stats")],
        [KeyboardButton(text="🏆 Leaderboard"), KeyboardButton(text="📜 History")],
        [KeyboardButton(text="💵 Wallet"), KeyboardButton(text="📢 OTP Group")]
    ]
    if is_admin(uid):
        keyboard.append([KeyboardButton(text="🛡 ADMIN PANEL")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def order_status_kb(order_id=None):
    rows = []
    if order_id:
        rows.append([
            InlineKeyboardButton(text="🔄 Refresh", callback_data=f"refresh_order_{order_id}"),
            InlineKeyboardButton(text="📜 Check OTP", callback_data="user_orders_history")
        ])
    else:
        rows.append([
            InlineKeyboardButton(text="📜 Check OTP", callback_data="user_orders_history")
        ])
    rows.append([InlineKeyboardButton(text="❌ Cancel", callback_data=f"cancel_num_{order_id}" if order_id else "cancel_num_0")])
    rows.append([InlineKeyboardButton(text="🌍 Change Country", callback_data="list_countries")])
    rows.append([InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistics",       callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 User List", callback_data="admin_users")],
        [InlineKeyboardButton(text="📦 Orders",       callback_data="admin_orders")],
        [InlineKeyboardButton(text="💸 Approve TON",  callback_data="admin_withdraws")],
        [InlineKeyboardButton(text="✅ Approve History",   callback_data="admin_withdraws_history")],
        [InlineKeyboardButton(text="🛠 Admin Commands",      callback_data="admin_cmds")],
        [InlineKeyboardButton(text="⬅️ Back to Menu",   callback_data="home")]
    ])

def admin_cmds_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Force Poll OTP (/pollnow)", callback_data="run_cmd_pollnow")],
        [InlineKeyboardButton(text="🟢 Health Check (/health)", callback_data="run_cmd_health")],
        [InlineKeyboardButton(text="📊 MK Account (/whoami)", callback_data="run_cmd_whoami")],
        [InlineKeyboardButton(text="🗺 MK Ranges (/access_list)", callback_data="run_cmd_access_list")],
        [InlineKeyboardButton(text="📡 MK Radar (/radar)", callback_data="run_cmd_radar")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="admin_menu")]
    ])

def expired_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Get New Number", callback_data="list_countries")],
        [InlineKeyboardButton(text="📜 Check History", callback_data="user_orders_history")],
        [InlineKeyboardButton(text="🏠 Home", callback_data="home")]
    ])

# =====================================================
# MK API CORE
# =====================================================
HTTP_ERRORS = {
    401: "Invalid API key.",
    403: "API locked or pending approval.",
    404: "Out of stock for this range.",
    405: "Wrong HTTP method.",
    422: "Invalid field data.",
    429: "Rate limit exceeded. Please try again later.",
    500: "API internal error.",
    503: "API temporarily disabled.",
}

async def api_request(method, endpoint, payload=None, params=None):
    headers = {"mknetwork-key": MK_API_KEY, "Accept": "application/json"}
    if payload is not None: headers["Content-Type"] = "application/json"
    url = f"{MK_API_BASE}/{endpoint.lstrip('/')}"
    timeout = aiohttp.ClientTimeout(total=25)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.request(method, url, headers=headers, json=payload, params=params) as r:
                raw = await r.text()
                try: data = json.loads(raw)
                except json.JSONDecodeError: data = {"response": raw[:1000]}

                if r.status >= 400:
                    err = HTTP_ERRORS.get(r.status, f"API Error ({r.status})")
                    logger.warning(f"MK IVAS {r.status}: {err} - Raw: {raw[:200]}")
                    return None, err
                if isinstance(data, dict) and data.get("success") is False:
                    return None, str(data.get("message") or "API Error")
                return data, None
    except asyncio.TimeoutError:
        return None, "Connection timeout."
    except Exception:
        logger.exception("API fail"); return None, "Cannot connect to API."

async def api_get(ep, params=None): 
    return await api_request("GET", ep, params=params)

# =====================================================
# NUMBER PANEL API CORE (Nguồn 2) - ĐÃ FIX LỖI HEADER
# =====================================================
async def np_api_request(method, endpoint, payload=None, params=None):
    # Thêm User-Agent giả lập trình duyệt để tránh bị server API chặn
    headers = {
        "Authorization": f"Bearer {NP_API_KEY}", 
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    if payload is not None: headers["Content-Type"] = "application/json"
    url = f"{NP_API_BASE}/{endpoint.lstrip('/')}"
    timeout = aiohttp.ClientTimeout(total=25)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.request(method, url, headers=headers, json=payload, params=params) as r:
                raw = await r.text()
                try: data = json.loads(raw)
                except json.JSONDecodeError: data = {"response": raw[:1000]}

                if r.status >= 400:
                    err = f"NP API Error ({r.status})"
                    logger.warning(f"NP IVAS {r.status}: {err} - Raw: {raw[:200]}")
                    return None, err
                if isinstance(data, dict) and data.get("success") is False:
                    return None, str(data.get("message") or "API Error")
                return data, None
    except asyncio.TimeoutError:
        return None, "Connection timeout."
    except Exception:
        logger.exception("NP API fail"); return None, "Cannot connect to NP API."

def unwrap(d):
    if not isinstance(d, dict): return {}
    for k in ("data", "result", "response"):
        v = d.get(k)
        if isinstance(v, dict): return v
    return d

def field(d, *names, default=""):
    if not isinstance(d, dict): return default
    sources = [d, unwrap(d)]
    if isinstance(d.get("data"), dict):
        sources.append(d.get("data"))
    for src in sources:
        for n in names:
            val = src.get(n)
            if val is not None and str(val).strip() != "":
                return val
    return default

def strip_secrets(obj):
    blocked = {"otp","otp_code","code","full_sms","sms","message", "api_key","token","authorization","password"}
    if isinstance(obj, dict):
        return {k: strip_secrets(v) for k, v in obj.items() if k.lower() not in blocked}
    if isinstance(obj, list):
        return [strip_secrets(x) for x in obj[:30]]
    return obj

def fmt_api(d):
    return html.escape(json.dumps(strip_secrets(d), ensure_ascii=False, indent=2, default=str)[:3500])

# =====================================================
# TẠO ĐƠN
# =====================================================
async def create_number_order(uid, range_code, msg_id=None):
    if not range_code or len(range_code) > 80 or any(c.isspace() for c in range_code):
        return False, "Invalid range code."

    data, err = await api_request("POST", "getnum/number", {"range": range_code})
    
    if err: return False, err

    def find_valid_id(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                k_lower = str(k).lower()
                if ("id" in k_lower or "request" in k_lower) and str(v).isdigit():
                    return str(v)
            for v in obj.values():
                res = find_valid_id(v)
                if res is not None: return res
        elif isinstance(obj, list):
            for item in obj:
                res = find_valid_id(item)
                if res is not None: return res
        return None

    rid_str = find_valid_id(data)

    if rid_str is None:
        logger.error(f"=== NO REQUEST_ID FOUND ===\nData: {json.dumps(data, ensure_ascii=False)}")
        return False, "No ID found in API response (Check logs)."

    phone    = field(data, "number", "phone", "phone_number")
    country  = field(data, "country", "country_name")
    operator = field(data, "operator", "network", "carrier")

    if not country or country == "Unknown":
        for c_name, c_range in FALLBACK_COUNTRIES.items():
            if range_code in c_range or c_range.replace("XXX", "") == range_code.replace("XXX", ""):
                country = c_name
                break

    exp = (now() + timedelta(minutes=ORDER_LIFETIME_MINUTES)).isoformat(timespec="seconds")
    db = get_db()
    try:
        db.execute("""
            INSERT INTO orders (user_id, request_id, provider, phone, country, operator,
                range_code, status, created_at, expires_at, updated_at, msg_id)
            VALUES (?, ?, 'MK', ?, ?, ?, ?, 'PENDING', ?, ?, ?, ?)
        """, (uid, rid_str, str(phone or "N/A"), str(country or "?"),
              str(operator or "?"), range_code, now_text(), exp, now_text(), msg_id))
        db.commit()
    except Exception as e:
        logger.error(f"Insert order error: {e}"); return False, "Database error."
    finally: db.close()

    return True, {
        "request_id": rid_str, "phone": phone or "N/A",
        "country": country or "?", "operator": operator or "?",
        "expires_at": exp,
    }

async def create_np_number_order(uid, service, country, msg_id=None):
    payload = {"service": service, "country": country}
    data, err = await np_api_request("POST", "request_number", payload=payload)
    if err: return False, err
    
    phone = data.get("number")
    rid = data.get("id") or phone # Dùng phone nếu không có ID
    
    if not phone or not rid:
        return False, "Không lấy được số từ Number Panel."

    exp = (now() + timedelta(minutes=ORDER_LIFETIME_MINUTES)).isoformat(timespec="seconds")
    db = get_db()
    try:
        db.execute("""
            INSERT INTO orders (user_id, request_id, provider, phone, country, operator,
                range_code, status, created_at, expires_at, updated_at, msg_id)
            VALUES (?, ?, 'NP', ?, ?, ?, ?, 'PENDING', ?, ?, ?, ?)
        """, (uid, str(rid), str(phone), str(country), service, service, now_text(), exp, now_text(), msg_id))
        db.commit()
    except Exception as e:
        logger.error(f"Insert NP order error: {e}"); return False, "Database error."
    finally: db.close()

    return True, {
        "request_id": rid, "phone": phone, "country": country, "operator": service, "expires_at": exp
    }

# =====================================================
# HELPER ĐƠN HÀNG
# =====================================================
async def get_user_orders(uid, limit=HISTORY_PER_PAGE, offset=0):
    await expire_old_orders()
    db = get_db()
    try:
        return db.execute("SELECT id, request_id, provider, phone, country, operator, status, created_at, expires_at FROM orders WHERE user_id=? ORDER BY id DESC LIMIT ? OFFSET ?", (uid, limit, offset)).fetchall()
    finally: db.close()

async def get_order(oid, uid=None):
    db = get_db()
    try:
        if uid is None: cursor = db.execute("SELECT * FROM orders WHERE id=?", (oid,))
        else: cursor = db.execute("SELECT * FROM orders WHERE id=? AND user_id=?", (oid, uid))
        row = cursor.fetchone()
        if row: return dict_factory(cursor, row)
        return None
    finally: db.close()

async def get_all_orders(limit=15):
    await expire_old_orders()
    db = get_db()
    try:
        return db.execute("SELECT id, user_id, request_id, phone, status FROM orders ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    finally: db.close()

async def get_pending_requests(limit=100):
    db = get_db()
    try:
        rows = db.execute("SELECT id, user_id, request_id, provider, phone, msg_id, range_code, country FROM orders WHERE status='PENDING' ORDER BY id ASC LIMIT ?", (limit,)).fetchall()
        return [{"id": r[0], "user_id": r[1], "request_id": r[2], "provider": r[3], "phone": r[4], "msg_id": r[5], "range_code": r[6], "country": r[7]} for r in rows]
    finally: db.close()

# =====================================================
# START / HELP
# =====================================================
@dp.message(CommandStart())
async def cmd_start(message: Message):
    try: await message.delete()
    except: pass
    args = message.text.split(maxsplit=1)
    ref = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    is_new = await register_user(message.from_user, ref)
    if is_new and ref:
        try: await bot.send_message(ref, "👥 Someone joined FAST IVAS using your link.")
        except Exception: pass
    
    msg = await message.answer("🚀 <b>FAST IVAS</b>\n\nWelcome!\nSelect an option below:", reply_markup=get_main_reply_kb(message.from_user.id))
    track_msg(message.from_user.id, msg.message_id)

# CÁC LỆNH TỪ MENU TEXT
@dp.message(F.text == "👤 Account")
async def menu_profile_txt(message: Message):
    try: await message.delete()
    except: pass
    await register_user(message.from_user)
    u = await get_user(message.from_user.id)
    msg = await message.answer("👤 <b>ACCOUNT</b>\n\n" f"ID: <code>{u['user_id']}</code>\nName: {safe(u['first_name'])}\nUsername: @{safe(u['username'] or '—')}\nJoined: {safe(u['joined_at'][:10])}\n\n" f"💵 Balance: <b>{usd(u['usd_milli'])}</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")]]))
    track_msg(message.from_user.id, msg.message_id)

@dp.message(F.text == "🎱 Number")
async def menu_order_help_txt(message: Message):
    try: await message.delete()
    except: pass
    await cb_list_countries_internal(message.from_user.id, message.chat.id)

@dp.message(F.text == "📱 Numbers 2")
async def menu_numbers2_txt(message: Message):
    try: await message.delete()
    except: pass
    
    data, err = await np_api_request("GET", "services")
    services = []
    if not err and data:
        services = data.get("services") or data.get("data", {}).get("services", [])
        
    if not services:
        # In ra log để dễ debug nếu vẫn lỗi
        logger.error(f"NP Services Error: {err} | Data: {data}")
        msg = await message.answer("⚠️ Không thể tải danh sách dịch vụ từ Number Panel lúc này. Vui lòng thử lại sau.")
        track_msg(message.from_user.id, msg.message_id)
        return
        
    buttons = []
    row = []
    for svc in services:
        if svc.get("count", 0) > 0:
            name = svc["name"]
            icon = get_network_icon(name)
            row.append(InlineKeyboardButton(text=f"{icon} {name} ({svc['count']})", callback_data=f"np_svc_{name}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
    if row: buttons.append(row)
    
    buttons.append([InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")])
    
    msg = await message.answer("📱 <b>NUMBER PANEL (NEW)</b>\n\nVui lòng chọn Dịch vụ bạn muốn lấy số:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    track_msg(message.from_user.id, msg.message_id)

@dp.message(F.text == "💰 Withdraw")
async def menu_wd_txt(message: Message):
    try: await message.delete()
    except: pass
    u = await get_user(message.from_user.id)
    wallet = u["wallet_ton"] or "Not set"
    text = f"💸 <b>WITHDRAW USD VIA TON</b>\n\nCurrent Balance: <b>{usd(u['usd_milli'])}</b>\nTON Wallet: <code>{wallet}</code>\n\nPlease select an action:"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Setup TON Wallet", callback_data="wd_setup_addr")], 
        [InlineKeyboardButton(text="💵 Withdraw", callback_data="wd_choose_amount")],
        [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")]
    ])
    msg = await message.answer(text, reply_markup=kb)
    track_msg(message.from_user.id, msg.message_id)

@dp.message(F.text == "💌 Invite")
async def menu_referral_txt(message: Message):
    try: await message.delete()
    except: pass
    link = f"https://t.me/{BOT_USERNAME}?start={message.from_user.id}"
    text = f"👥 <b>INVITE FRIENDS</b>\n\nInvite your friends to join FAST IVAS and earn commission:\n<code>{link}</code>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")]
    ])
    msg = await message.answer(text, reply_markup=kb)
    track_msg(message.from_user.id, msg.message_id)

@dp.message(F.text == "📊 Ranges Stats")
async def menu_stats_txt(message: Message):
    try: await message.delete()
    except: pass
    await cb_ranges_stats_internal(message.from_user.id, message.chat.id)

@dp.message(F.text == "🏆 Leaderboard")
async def menu_leaderboard_txt(message: Message):
    try: await message.delete()
    except: pass
    await cb_leaderboard_internal(message.from_user.id, message.chat.id)

@dp.message(F.text == "📜 History")
async def menu_history_txt(message: Message):
    try: await message.delete()
    except: pass
    await cb_user_orders_history_internal(message.from_user.id, message.chat.id, page=1)

@dp.message(F.text == "💵 Wallet")
async def menu_wallet_txt(message: Message):
    try: await message.delete()
    except: pass
    await register_user(message.from_user)
    u = await get_user(message.from_user.id)
    msg = await message.answer("💵 <b>WALLET</b>\n\n" f"Balance: <b>{usd(u['usd_milli'])}</b>\nReward/OTP: <b>{usd(REWARD_MILLI_PER_OTP)}</b>\nMin Withdraw: <b>{usd(MIN_WITHDRAW_MILLI)}</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")]]))
    track_msg(message.from_user.id, msg.message_id)

@dp.message(F.text == "📢 OTP Group")
async def menu_group_txt(message: Message):
    try: await message.delete()
    except: pass
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👉 Join OTP Group", url=OTP_GROUP_URL)],
        [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")]
    ])
    msg = await message.answer("Join the OTP group for latest updates:", reply_markup=kb)
    track_msg(message.from_user.id, msg.message_id)

@dp.message(F.text == "🛡 ADMIN PANEL")
async def menu_admin_txt(message: Message):
    try: await message.delete()
    except: pass
    if not is_admin(message.from_user.id): return
    msg = await message.answer("🛡 <b>ADMIN PANEL</b>", reply_markup=admin_kb())
    track_msg(message.from_user.id, msg.message_id)

# =====================================================
# MENU CALLBACKS
# =====================================================
@dp.callback_query(F.data == "home")
async def cb_home(call: CallbackQuery):
    try: await call.message.delete()
    except: pass
    msg = await call.message.answer("🚀 <b>FAST IVAS</b>\n\nSelect an option:", reply_markup=get_main_reply_kb(call.from_user.id))
    track_msg(call.from_user.id, msg.message_id)
    await call.answer()

# --- NUMBER PANEL FLOW ---
@dp.callback_query(F.data.startswith("np_svc_"))
async def cb_np_service(call: CallbackQuery):
    service = call.data.replace("np_svc_", "")
    await call.answer("Đang tải quốc gia...")
    
    data, err = await np_api_request("GET", "countries", params={"service": service})
    countries = []
    if not err and data:
        countries = data.get("countries") or data.get("data", {}).get("countries", [])
        
    if not countries:
        await call.message.edit_text(f"⚠️ <b>HẾT SỐ</b>\n\nDịch vụ {service} hiện tại đã hết số, vui lòng chọn dịch vụ khác.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Quay lại", callback_data="list_np_services")]]))
        return
        
    buttons = []
    row = []
    for c in countries:
        if c.get("count", 0) > 0:
            c_name = c["name"]
            flag = get_country_flag(c_name)
            row.append(InlineKeyboardButton(text=f"{flag} {c_name} ({c['count']})", callback_data=f"np_cty_{service}_{c_name}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
    if row: buttons.append(row)
    
    buttons.append([InlineKeyboardButton(text="⬅️ Quay lại", callback_data="list_np_services")])
    
    await call.message.edit_text(f"🌍 <b>CHỌN QUỐC GIA</b>\nDịch vụ: <b>{service}</b>\n\nVui lòng chọn quốc gia:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data == "list_np_services")
async def cb_list_np_services(call: CallbackQuery):
    await call.answer()
    data, err = await np_api_request("GET", "services")
    services = []
    if not err and data:
        services = data.get("services") or data.get("data", {}).get("services", [])
        
    if not services:
        await call.message.edit_text("⚠️ Không thể tải danh sách dịch vụ lúc này.")
        return
        
    buttons = []
    row = []
    for svc in services:
        if svc.get("count", 0) > 0:
            name = svc["name"]
            icon = get_network_icon(name)
            row.append(InlineKeyboardButton(text=f"{icon} {name} ({svc['count']})", callback_data=f"np_svc_{name}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
    if row: buttons.append(row)
    
    buttons.append([InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")])
    await call.message.edit_text("📱 <b>NUMBER PANEL (NEW)</b>\n\nVui lòng chọn Dịch vụ bạn muốn lấy số:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("np_cty_"))
async def cb_np_country(call: CallbackQuery):
    parts = call.data.replace("np_cty_", "").split("_", 1)
    service = parts[0]
    country = parts[1]
    
    await call.answer("Đang lấy số...")
    
    ok, res = await create_np_number_order(call.from_user.id, service, country, msg_id=call.message.message_id)
    if not ok:
        await call.message.edit_text(f"⚠️ <b>LỖI LẤY SỐ</b>\n\n{res}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Quay lại", callback_data=f"np_svc_{service}")]]))
        return
        
    db = get_db()
    row = db.execute("SELECT id FROM orders WHERE request_id=?", (res['request_id'],)).fetchone()
    db.close()
    order_id = row[0] if row else 0

    await call.message.edit_text(f"✅ <b>NUMBER RECEIVED (NP)</b>\n\nNumber: <code>{res['phone']}</code>\nCountry: {safe(res['country'])}\nService: {service}\nExpires: {safe(res['expires_at'])}\n\n⏳ Waiting for OTP...", reply_markup=order_status_kb(order_id))


# --- MK NETWORK FLOW ---
async def cb_list_countries_internal(uid, chat_id, message_id=None):
    try:
        country_dict = FALLBACK_COUNTRIES.copy()
        sorted_countries = sorted(list(country_dict.keys()))[:50]
        
        buttons = []
        for i in range(0, len(sorted_countries), 2):
            row = []
            c1 = sorted_countries[i]
            flag1 = get_country_flag(c1)
            row.append(InlineKeyboardButton(text=f"{flag1} {c1}", callback_data=f"rng_{country_dict[c1]}"))
            if i + 1 < len(sorted_countries):
                c2 = sorted_countries[i+1]
                flag2 = get_country_flag(c2)
                row.append(InlineKeyboardButton(text=f"{flag2} {c2}", callback_data=f"rng_{country_dict[c2]}"))
            buttons.append(row)
            
        buttons.append([InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")])

        text = "🌍 <b>SELECT COUNTRY (MK)</b>\n\nClick a country to get a number:"
        
        if message_id:
            try: await bot.delete_message(chat_id, message_id)
            except: pass
        
        msg = await bot.send_message(chat_id, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        track_msg(chat_id, msg.message_id)
    except Exception as e:
        logger.error(f"Lỗi tạo bảng quốc gia: {e}")
        msg = await bot.send_message(chat_id, f"⚠️ Error: {e}")
        track_msg(chat_id, msg.message_id)

@dp.callback_query(F.data == "list_countries")
async def cb_list_countries(call: CallbackQuery):
    await call.answer("Loading...")
    await cb_list_countries_internal(call.from_user.id, call.message.chat.id, call.message.message_id)

@dp.callback_query(F.data == "menu_order_help")
async def cb_menu_order_help(call: CallbackQuery):
    await call.answer("Loading...")
    await cb_list_countries_internal(call.from_user.id, call.message.chat.id, call.message.message_id)

# NÂNG CẤP: THỐNG KÊ CÓ KÈM DỊCH VỤ HỖ TRỢ VÀ NÚT PLATFORM
async def cb_ranges_stats_internal(uid, chat_id, message_id=None):
    today_str = now().strftime("%Y-%m-%d")
    
    db = get_db()
    db_stats = {}
    try:
        rows = db.execute("SELECT country, COUNT(id) FROM orders WHERE status='COMPLETED' AND created_at >= ? GROUP BY country", (today_str,)).fetchall()
        for r in rows:
            db_stats[r[0]] = r[1]
    finally:
        db.close()

    api_networks = {}
    data, err = await api_get("access_list", params={"limit": 50})
    if not err and isinstance(data, dict):
        items = data.get("data", {}).get("items", [])
        for item in items:
            c_name = item.get("country")
            nets = item.get("networks") or item.get("supported_networks") or item.get("platforms") or []
            if c_name:
                api_networks[c_name] = nets

    text = "📊 <b>RANGES STATS TODAY</b>\n\n"
    total_otps = sum(db_stats.values())
    text += f"Tổng OTP hôm nay: <b>{total_otps}</b>\n"
    text += "──────────────────\n"
    
    all_countries = set(list(db_stats.keys()) + list(api_networks.keys()))
    sorted_countries = sorted(all_countries)
    
    if not sorted_countries:
        text += "No data available."
    else:
        for c_name in sorted_countries:
            count = db_stats.get(c_name, 0)
            flag = get_country_flag(c_name)
            
            nets = api_networks.get(c_name, [])
            net_str = ""
            if nets:
                icons = [f"{get_network_icon(n)} {n.capitalize()}" for n in nets]
                net_str = f"\n   ↳ <i>Support: {', '.join(icons)}</i>"
            
            text += f"{flag} <b>{c_name}</b>: {count} OTPs{net_str}\n"

    if len(text) > 4000:
        text = text[:4000] + "\n\n<i>(... Danh sách bị cắt bớt)</i>"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Platform Activity", callback_data="platform_stats")],
        [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")]
    ])
    
    if message_id:
        try: await bot.delete_message(chat_id, message_id)
        except: pass
    msg = await bot.send_message(chat_id, text, reply_markup=kb)
    track_msg(chat_id, msg.message_id)

@dp.callback_query(F.data == "ranges_stats")
async def cb_ranges_stats(call: CallbackQuery):
    await cb_ranges_stats_internal(call.from_user.id, call.message.chat.id, call.message.message_id)
    await call.answer()

# NÚT PLATFORM ACTIVITY REAL-TIME
@dp.callback_query(F.data == "platform_stats")
async def cb_platform_stats(call: CallbackQuery):
    await call.answer("Đang tải...")
    today_str = now().strftime("%Y-%m-%d")
    db = get_db()
    try:
        rows = db.execute("""
            SELECT platform, COUNT(id) 
            FROM orders 
            WHERE status='COMPLETED' AND created_at >= ? 
            GROUP BY platform 
            ORDER BY COUNT(id) DESC
        """, (today_str,)).fetchall()
        
        text = "📱 <b>PLATFORM ACTIVITY (REAL-TIME)</b>\n\n"
        if not rows:
            text += "Chưa có OTP nào được nhận hôm nay."
        else:
            total = sum(r[1] for r in rows)
            text += f"Tổng OTP hôm nay: <b>{total}</b>\n"
            text += "──────────────────\n"
            for r in rows:
                platform = r[0] or "Unknown"
                count = r[1]
                icon = get_network_icon(platform)
                text += f"{icon} <b>{platform}</b>: {count} OTPs\n"
    finally:
        db.close()
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Làm mới", callback_data="platform_stats")],
        [InlineKeyboardButton(text="⬅️ Quay lại Stats", callback_data="ranges_stats")]
    ])
    
    await call.message.edit_text(text, reply_markup=kb)

async def cb_leaderboard_internal(uid, chat_id, message_id=None):
    today_str = now().strftime("%Y-%m-%d")
    db = get_db()
    try:
        rows = db.execute("""
            SELECT 
                o.user_id, 
                COUNT(o.id) as otp_count, 
                u.first_name, 
                u.usd_milli,
                (SELECT COUNT(*) FROM users ref WHERE ref.referrer = o.user_id) as ref_count
            FROM orders o
            JOIN users u ON o.user_id = u.user_id
            WHERE o.status='COMPLETED' AND o.created_at >= ?
            GROUP BY o.user_id
            ORDER BY otp_count DESC LIMIT 10
        """, (today_str,)).fetchall()
        
        text = "🏆 <b>LEADERBOARD TODAY</b>\n\n"
        if not rows:
            text += "No OTPs received today yet."
        else:
            for i, r in enumerate(rows, 1):
                uid_r = r[0]
                otp_count = r[1]
                name = safe(r[2] or f"User {uid_r}")
                balance = usd(r[3])
                ref_count = r[4]
                
                text += f"{i}. <b>{name}</b> (<code>{uid_r}</code>)\n"
                text += f"   ├ 🔑 OTPs: <b>{otp_count}</b>\n"
                text += f"   ├ 💵 Balance: <b>{balance}</b>\n"
                text += f"   └ 👥 Invites: <b>{ref_count}</b>\n\n"
    finally:
        db.close()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")]])
    if message_id:
        try: await bot.delete_message(chat_id, message_id)
        except: pass
    msg = await bot.send_message(chat_id, text, reply_markup=kb)
    track_msg(chat_id, msg.message_id)

@dp.callback_query(F.data == "leaderboard")
async def cb_leaderboard(call: CallbackQuery):
    await cb_leaderboard_internal(call.from_user.id, call.message.chat.id, call.message.message_id)
    await call.answer()

# LỊCH SỬ ĐƠN HÀNG
async def cb_user_orders_history_internal(uid, chat_id, message_id=None, page=1):
    if page < 1: page = 1
    max_page = MAX_HISTORY_RECORDS // HISTORY_PER_PAGE
    if page > max_page: page = max_page
    
    offset = (page - 1) * HISTORY_PER_PAGE
    rows = await get_user_orders(uid, limit=HISTORY_PER_PAGE, offset=offset)
    
    if not rows and page > 1:
        return await cb_user_orders_history_internal(uid, chat_id, message_id, page - 1)
        
    if not rows:
        msg = await bot.send_message(chat_id, "You haven't ordered any numbers yet!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")]]))
        track_msg(chat_id, msg.message_id)
        return
    
    buttons = []
    for r in rows:
        oid, req, provider, phone, country, op, status, c_at, e_at = r
        flag = get_country_flag(country)
        
        date_str = fmt_date(c_at)
        
        if status == "COMPLETED": icon = "✅"
        elif status == "EXPIRED": icon = "⌛"
        elif status == "CANCELLED": icon = "🚫"
        elif status == "FAILED": icon = "❌"
        else: icon = "⏳"
        
        p_tag = "[MK]" if provider == "MK" else "[NP]"
        btn_text = f"{icon} {flag} {mask_phone(phone)} {p_tag}| {date_str}"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"view_history_{oid}")])
    
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️ Prev", callback_data=f"hist_page_{page-1}"))
    if len(rows) == HISTORY_PER_PAGE and page < max_page:
        nav_row.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"hist_page_{page+1}"))
        
    if nav_row:
        buttons.append(nav_row)
        
    buttons.append([InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")])
    text = f"📜 <b>RECENT HISTORY (Page {page}/{max_page})</b>\n\nClick a number to view details:"
    
    if message_id:
        try: await bot.delete_message(chat_id, message_id)
        except: pass
    msg = await bot.send_message(chat_id, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    track_msg(chat_id, msg.message_id)

@dp.callback_query(F.data == "user_orders_history")
async def cb_user_orders_history(call: CallbackQuery):
    await cb_user_orders_history_internal(call.from_user.id, call.message.chat.id, call.message.message_id, page=1)
    await call.answer()

@dp.callback_query(F.data.startswith("hist_page_"))
async def cb_hist_page(call: CallbackQuery):
    page = int(call.data.replace("hist_page_", ""))
    await cb_user_orders_history_internal(call.from_user.id, call.message.chat.id, call.message.message_id, page=page)
    await call.answer(f"Page {page}")

# =====================================================
# CÁC HANDLER KHÁC
# =====================================================
@dp.callback_query(F.data == "menu_profile")
async def cb_menu_profile(call: CallbackQuery):
    await register_user(call.from_user)
    u = await get_user(call.from_user.id)
    await call.message.edit_text("👤 <b>ACCOUNT</b>\n\n" f"ID: <code>{u['user_id']}</code>\nName: {safe(u['first_name'])}\nUsername: @{safe(u['username'] or '—')}\nJoined: {safe(u['joined_at'][:10])}\n\n" f"💵 Balance: <b>{usd(u['usd_milli'])}</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")]]))
    await call.answer()

@dp.callback_query(F.data == "menu_wallet")
async def cb_menu_wallet(call: CallbackQuery):
    await register_user(call.from_user)
    u = await get_user(call.from_user.id)
    await call.message.edit_text("💵 <b>WALLET</b>\n\n" f"Balance: <b>{usd(u['usd_milli'])}</b>\nReward/OTP: <b>{usd(REWARD_MILLI_PER_OTP)}</b>\nMin Withdraw: <b>{usd(MIN_WITHDRAW_MILLI)}</b>\n\n" "Command: <code>/withdraw</code>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")]]))
    await call.answer()

@dp.callback_query(F.data == "menu_referral")
async def cb_menu_referral(call: CallbackQuery):
    link = f"https://t.me/{BOT_USERNAME}?start={call.from_user.id}"
    text = f"👥 <b>INVITE FRIENDS</b>\n\nInvite your friends to join FAST IVAS and earn commission:\n<code>{link}</code>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")]
    ])
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()

# =====================================================
# RÚT TIỀN
# =====================================================
@dp.message(Command("withdraw"))
async def cmd_rut_menu(message: Message):
    try: await message.delete()
    except: pass
    u = await get_user(message.from_user.id)
    wallet = u["wallet_ton"] or "Not set"
    text = f"💸 <b>WITHDRAW USD VIA TON</b>\n\nCurrent Balance: <b>{usd(u['usd_milli'])}</b>\nTON Wallet: <code>{wallet}</code>\n\nPlease select an action:"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Setup TON Wallet", callback_data="wd_setup_addr")], 
        [InlineKeyboardButton(text="💵 Withdraw", callback_data="wd_choose_amount")],
        [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")]
    ])
    msg = await message.answer(text, reply_markup=kb)
    track_msg(message.from_user.id, msg.message_id)

@dp.callback_query(F.data == "wd_menu")
async def cb_wd_menu(call: CallbackQuery):
    u = await get_user(call.from_user.id)
    wallet = u["wallet_ton"] or "Not set"
    text = f"💸 <b>WITHDRAW USD VIA TON</b>\n\nCurrent Balance: <b>{usd(u['usd_milli'])}</b>\nTON Wallet: <code>{wallet}</code>\n\nPlease select an action:"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Setup TON Wallet", callback_data="wd_setup_addr")], 
        [InlineKeyboardButton(text="💵 Withdraw", callback_data="wd_choose_amount")],
        [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")]
    ])
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()

@dp.callback_query(F.data == "wd_setup_addr")
async def cb_wd_setup_addr(call: CallbackQuery):
    text = "⚙️ <b>SETUP TON WALLET</b>\n\nPlease send your TON wallet address below.\nExample: <code>UQBfFHeVzZyixLYup3rvCkRaSVJTOc8UtCeqksenDoMxSvOS</code>\n\n<i>(Address usually starts with UQ or EQ and is 48 characters long).</i>"
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="wd_menu")]]))
    await call.answer()

@dp.message(F.text.regexp(r"^(EQ|UQ)[a-zA-Z0-9_-]{46}$"))
async def handle_wallet_input(message: Message):
    try: await message.delete()
    except: pass
    wallet = message.text.strip()
    await set_wallet_ton(message.from_user.id, wallet)
    text = f"✅ <b>TON WALLET SAVED</b>\n\nYour wallet:\n<code>{wallet}</code>\n\nYou can now click <b>Back</b> to return to Withdraw menu."
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back to Withdraw", callback_data="wd_menu")]])
    msg = await message.answer(text, reply_markup=kb)
    track_msg(message.from_user.id, msg.message_id)

@dp.callback_query(F.data == "wd_choose_amount")
async def cb_wd_choose_amount(call: CallbackQuery):
    u = await get_user(call.from_user.id)
    if not u["wallet_ton"]:
        await call.answer("Please setup TON wallet first!", show_alert=True); return
        
    balance = int(u['usd_milli'])
    buttons = []
    row = []
    for i in [1, 2, 4, 6, 8, 10]:
        row.append(InlineKeyboardButton(text=f"${i}", callback_data=f"wd_amt_{i}"))
        if len(row) == 3: buttons.append(row); row = []
    if row: buttons.append(row)
    
    TON_FEE_MILLI = 100
    all_in_amt = balance - TON_FEE_MILLI
    if all_in_amt >= MIN_WITHDRAW_MILLI:
        buttons.append([InlineKeyboardButton(text=f"💰 Withdraw All (~{usd(all_in_amt)})", callback_data=f"wd_amt_all")])
        
    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="wd_menu")])
    
    text = f"💵 <b>SELECT AMOUNT TO WITHDRAW</b>\n\nBalance: <b>{usd(balance)}</b>\n\n<i>(* Note: Withdraw All applies a ~$0.1 TON network fee)</i>"
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await call.answer()

@dp.callback_query(F.data.startswith("wd_amt_"))
async def cb_wd_amt(call: CallbackQuery):
    u = await get_user(call.from_user.id)
    balance = int(u["usd_milli"])
    
    if call.data == "wd_amt_all":
        TON_FEE_MILLI = 100
        amt_milli = balance - TON_FEE_MILLI
        if amt_milli < MIN_WITHDRAW_MILLI:
            await call.answer("Insufficient balance after network fee!", show_alert=True); return
        text_amt = f"All {usd(amt_milli)} (after fee)"
        amt_usd = 0
    else:
        amt_usd = int(call.data.replace("wd_amt_", ""))
        amt_milli = amt_usd * 1000
        if balance < amt_milli:
            await call.answer(f"Insufficient balance for ${amt_usd}!", show_alert=True); return
        text_amt = f"${amt_usd}.000"
        
    text = f"⚠️ <b>CONFIRM WITHDRAWAL</b>\n\nAre you sure you want to withdraw <b>{text_amt}</b> to:\n<code>{u['wallet_ton']}</code>?\n\n<i>(Funds will be deducted immediately and await Admin approval)</i>"
    
    if call.data == "wd_amt_all":
        callback_conf = "wd_conf_all"
    else:
        callback_conf = f"wd_conf_{amt_usd}"
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Confirm", callback_data=callback_conf)], 
        [InlineKeyboardButton(text="❌ Cancel", callback_data="wd_choose_amount")]
    ])
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()

@dp.callback_query(F.data.startswith("wd_conf_"))
async def cb_wd_conf(call: CallbackQuery):
    u = await get_user(call.from_user.id)
    balance = int(u["usd_milli"])
    
    if call.data == "wd_conf_all":
        TON_FEE_MILLI = 100
        amt_milli = balance - TON_FEE_MILLI
        if amt_milli < MIN_WITHDRAW_MILLI:
            await call.answer("Insufficient balance!", show_alert=True); return
        amt_str = usd(amt_milli)
    else:
        amt_usd = int(call.data.replace("wd_conf_", ""))
        amt_milli = amt_usd * 1000
        if balance < amt_milli:
            await call.answer(f"Insufficient balance!", show_alert=True); return
        amt_str = usd(amt_milli)

    ok, new_usd = await change_usd(call.from_user.id, -amt_milli, "WITHDRAW_HOLD", "TON Withdrawal Request")
    if not ok:
        await call.answer(safe(new_usd), show_alert=True); return
        
    wid = await create_withdrawal(call.from_user.id, amt_milli, u["wallet_ton"])
    await call.message.edit_text(f"✅ <b>WITHDRAWAL CREATED</b>\n\nID: <code>#{wid}</code>\nAmount: <b>{amt_str}</b>\nTON Wallet: <code>{u['wallet_ton']}</code>\nRemaining: <b>{usd(new_usd)}</b>\n\nPlease wait for Admin approval.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")]]))
    
    try:
        db = get_db()
        pending_count = db.execute("SELECT COUNT(*) FROM withdrawals WHERE status='PENDING'").fetchone()[0]
        db.close()
        admin_text = f"🔔 <b>WITHDRAWAL NOTIFICATION</b>\n\nThere are <b>{pending_count}</b> pending withdrawal requests.\nPlease click below to process."
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👉 Process Now", callback_data="admin_withdraws")]])
        admin_msg = await bot.send_message(ADMIN_ID, admin_text, reply_markup=kb)
        track_msg(ADMIN_ID, admin_msg.message_id)
    except Exception as e: logger.error(f"Error notifying admin: {e}")
    await call.answer("Withdrawal created!")

# =====================================================
# NHẬN SỐ & CHECK OTP
# =====================================================
@dp.callback_query(F.data.startswith("rng_"))
async def cb_choose_range(call: CallbackQuery):
    range_code = call.data.replace("rng_", "")
    await call.answer("Getting number...")
    ok, res = await create_number_order(call.from_user.id, range_code, msg_id=call.message.message_id)
    
    if not ok:
        error_msg = "Out of stock for this range. Please choose another country." if "404" in res or "Out of stock" in res else res
        await call.message.edit_text(
            f"⚠️ <b>UNABLE TO GET NUMBER</b>\n\n{error_msg}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Back to Country List", callback_data="list_countries")]
            ])
        )
        return
    
    db = get_db()
    row = db.execute("SELECT id FROM orders WHERE request_id=?", (res['request_id'],)).fetchone()
    db.close()
    order_id = row[0] if row else 0

    await call.message.edit_text(f"✅ <b>NUMBER RECEIVED (MK)</b>\n\nNumber: <code>{res['phone']}</code>\nCountry: {safe(res['country'])}\nExpires: {safe(res['expires_at'])}\n\n⏳ Waiting for OTP...", reply_markup=order_status_kb(order_id))

@dp.callback_query(F.data.startswith("new_num_"))
async def cb_new_num(call: CallbackQuery):
    range_code = call.data.replace("new_num_", "")
    await call.answer("Getting new number...")
    
    ok, res = await create_number_order(call.from_user.id, range_code, msg_id=call.message.message_id)
    if not ok:
        error_msg = "Out of stock for this range. Please choose another country." if "404" in res or "Out of stock" in res else res
        await call.message.edit_text(
            f"⚠️ <b>UNABLE TO GET NUMBER</b>\n\n{error_msg}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Back to Country List", callback_data="list_countries")]
            ])
        )
        return
    
    db = get_db()
    row = db.execute("SELECT id FROM orders WHERE request_id=?", (res['request_id'],)).fetchone()
    db.close()
    order_id = row[0] if row else 0

    await call.message.edit_text(f"✅ <b>NUMBER RECEIVED (MK)</b>\n\nNumber: <code>{res['phone']}</code>\nCountry: {safe(res['country'])}\nExpires: {safe(res['expires_at'])}\n\n⏳ Waiting for OTP...", reply_markup=order_status_kb(order_id))

@dp.callback_query(F.data.startswith("refresh_order_"))
async def cb_refresh_order(call: CallbackQuery):
    oid = int(call.data.replace("refresh_order_", ""))
    row = await get_order(oid, call.from_user.id)
    if not row:
        await call.answer("Order not found or no permission!", show_alert=True); return
    
    await call.answer("Checking...")
    
    if row.get("provider") == "NP":
        data, err = await np_api_request("GET", "latest_otp", params={"number": row['phone']})
        if not err and data and data.get("has_otp"):
            otp = str(data.get("otp_code") or "").strip()
            if otp:
                if _mk_poller:
                    success = await _mk_poller._process_otp(row, otp, f"OTP from NumberPanel: {otp}")
                    if success:
                        await call.answer("New OTP received!", show_alert=True)
                        return
    else:
        try:
            req_id = int(row['request_id'])
            data, err = await api_request("POST", "check/status", {"request_ids": [req_id]})
            if not err and isinstance(data, dict):
                inner = data.get("data") if isinstance(data, dict) else None
                results = inner.get("results") if isinstance(inner, dict) else None
                if isinstance(results, list) and results:
                    item = results[0]
                    if (item.get("status") or "").lower() == "success":
                        otp = str(item.get("otp_code") or "").strip()
                        sms = str(item.get("full_sms") or "").strip()
                        if otp:
                            if _mk_poller:
                                success = await _mk_poller._process_otp(row, otp, sms)
                                if success:
                                    await call.answer("New OTP received!", show_alert=True)
                                    return
        except Exception as e:
            logger.error(f"Refresh error #{oid}: {e}")

    row = await get_order(oid, call.from_user.id)
    if row["status"] == "COMPLETED":
        text = f"✅ <b>OTP RECEIVED</b>\n\nNumber: <code>{row['phone']}</code>\nCountry: {safe(row['country'])}\nOTP: <code>{safe(row['otp_code'])}</code>"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📜 History", callback_data="user_orders_history")], [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")]])
    elif row["status"] == "EXPIRED":
        text = f"⌛ <b>EXPIRED</b>\n\nNumber: <code>{row['phone']}</code>\nCountry: {safe(row['country'])}\nExpired at: {safe(row['expires_at'])}"
        kb = order_status_kb()
    else:
        text = f"⏳ <b>WAITING FOR OTP</b>\n\nNumber: <code>{row['phone']}</code>\nCountry: {safe(row['country'])}\nExpires: {safe(row['expires_at'])}\n\n<i>(Click Refresh to check again)</i>"
        kb = order_status_kb(oid)
        
    await call.message.edit_text(text, reply_markup=kb)

@dp.callback_query(F.data.startswith("view_history_"))
async def cb_view_history(call: CallbackQuery):
    oid = int(call.data.replace("view_history_", ""))
    row = await get_order(oid, call.from_user.id)
    if not row:
        await call.answer("Not found!", show_alert=True); return
    
    date_created = fmt_date(row.get('created_at'))
    date_expires = fmt_date(row.get('expires_at'))
    stt_text = status_text(row['status'])
    
    provider_tag = "MK Network" if row.get("provider") == "MK" else "Number Panel"
    
    text = f"📦 <b>ORDER DETAILS #{oid}</b> ({provider_tag})\n\n"
    text += f"Number: <code>{safe(row['phone'])}</code>\n"
    text += f"Country: {safe(row['country'])}\n"
    text += f"Status: <b>{stt_text}</b>\n"
    text += f"Created: {date_created}\n"
    text += f"Expires: {date_expires}\n"
    
    if row["status"] == "COMPLETED" and row.get("otp_code"):
        text += f"\n🔑 <b>OTP:</b> <code>{safe(row['otp_code'])}</code>"
        if row.get("full_sms"): text += f"\n💬 {safe(row['full_sms'])}"

    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="user_orders_history")]]))
    await call.answer()

@dp.callback_query(F.data.startswith("cancel_num_"))
async def cb_cancel_num(call: CallbackQuery):
    oid = int(call.data.replace("cancel_num_", ""))
    
    if oid > 0:
        db = get_db()
        try:
            row = db.execute("SELECT provider, phone, request_id FROM orders WHERE id=?", (oid,)).fetchone()
            if row and row[0] == "NP":
                await np_api_request("POST", "release_number", payload={"number": row[1]})
                
            db.execute("UPDATE orders SET status='CANCELLED', updated_at=? WHERE id=? AND status='PENDING'", (now_text(), oid))
            db.commit()
        finally: db.close()

    await call.answer("Cancelled...", show_alert=False)
    try: await call.message.delete()
    except: pass
    msg = await call.message.answer("🚫 Number cancelled successfully by user.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 Get New Number", callback_data="list_countries")], [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")]]))
    track_msg(call.from_user.id, msg.message_id)

@dp.message(Command("getnum"))
async def cmd_nhanso(message: Message):
    try: await message.delete()
    except: pass
    await register_user(message.from_user)
    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        await message.answer("Usage: <code>/getnum RANGE</code>"); return
    waiting_msg = await message.answer("⏳ Sending request...")
    ok, res = await create_number_order(message.from_user.id, parts[1].strip(), msg_id=waiting_msg.message_id)
    if not ok:
        await waiting_msg.edit_text(f"❌ {safe(res)}"); return

    db = get_db()
    row = db.execute("SELECT id FROM orders WHERE request_id=?", (res['request_id'],)).fetchone()
    db.close()
    order_id = row[0] if row else 0

    await waiting_msg.edit_text(f"✅ <b>NUMBER RECEIVED</b>\n\nNumber: <code>{res['phone']}</code>\nCountry: {safe(res['country'])}\nExpires: {safe(res['expires_at'])}\n\n⏳ Waiting for OTP...", reply_markup=order_status_kb(order_id))

# =====================================================
# ADMIN PANEL
# =====================================================
@dp.callback_query(F.data == "admin_menu")
async def cb_admin_menu(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Access denied.", show_alert=True); return
    try: await call.message.edit_text("🛡 <b>ADMIN PANEL</b>", reply_markup=admin_kb())
    except: pass
    await call.answer()

@dp.callback_query(F.data == "admin_cmds")
async def cb_admin_cmds(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    await call.message.edit_text("🛠 <b>ADMIN COMMANDS</b>\n\nClick below to execute:", reply_markup=admin_cmds_kb())
    await call.answer()

@dp.callback_query(F.data.startswith("run_cmd_"))
async def cb_run_cmd(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    cmd = call.data.replace("run_cmd_", "")
    try: await call.message.delete()
    except: pass

    if cmd == "pollnow":
        if not _mk_poller: await call.message.answer("Poller not running."); return
        msg = await call.message.answer("🔄 Polling...")
        try:
            c, n, err = await _mk_poller._poll_once()
            if err: await msg.edit_text(f"⚠️ API Error: {err}")
            else: await msg.edit_text(f"✅ Checked: {c} · New OTPs: {n}")
        except Exception as e: await msg.edit_text(f"❌ {safe(str(e))}")
        
    elif cmd == "health":
        db = get_db()
        try: pending = db.execute("SELECT COUNT(*) FROM orders WHERE status='PENDING'").fetchone()[0]
        finally: db.close()
        poller = "OFF" if not _mk_poller else f"ON ({_mk_poller.interval}s, err={_mk_poller._consecutive_errors})"
        text = "🟢 <b>FAST IVAS ONLINE</b>\n\n" f"DB: <code>Turso Cloud</code>\nMK Key: {'✓' if MK_API_KEY else '✗'}\nNP Key: {'✓' if NP_API_KEY else '✗'}\n" f"OTP group: <code>{OTP_GROUP_ID}</code>\nPending Orders: <b>{pending}</b>\nPoller: {safe(poller)}\n" f"Reward/OTP: <b>{usd(REWARD_MILLI_PER_OTP)}</b>\nMin Withdraw: <b>{usd(MIN_WITHDRAW_MILLI)}</b>"
        await call.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="admin_menu")]]))

    elif cmd == "whoami":
        data, err = await api_get("whoami")
        if err: await call.message.answer(f"❌ {safe(err)}"); return
        await call.message.answer(f"📊 <b>MK ACCOUNT</b>\n\n<pre>{fmt_api(data)}</pre>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="admin_menu")]]))
        
    elif cmd == "access_list":
        data, err = await api_get("access_list")
        if err: await call.message.answer(f"❌ {safe(err)}"); return
        await call.message.answer(f"🗺 <b>RANGES LIST</b>\n\n<pre>{fmt_api(data)}</pre>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="admin_menu")]]))
        
    elif cmd == "radar":
        data, err = await api_get("radar", params={"limit": 25, "charts": "true"})
        if err: await call.message.answer(f"❌ {safe(err)}"); return
        await call.message.answer(f"📡 <b>RADAR</b>\n\n<pre>{fmt_api(data)}</pre>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="admin_menu")]]))
        
    await call.answer()

@dp.callback_query(F.data == "admin_stats")
async def cb_admin_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    await expire_old_orders()
    db = get_db()
    try:
        users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        tot_usd = db.execute("SELECT COALESCE(SUM(usd_milli),0) FROM users").fetchone()[0]
        orders = db.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        pending = db.execute("SELECT COUNT(*) FROM orders WHERE status='PENDING'").fetchone()[0]
        completed = db.execute("SELECT COUNT(*) FROM orders WHERE status='COMPLETED'").fetchone()[0]
        wd = db.execute("SELECT COUNT(*) FROM withdrawals WHERE status='PENDING'").fetchone()[0]
        text = f"📊 <b>STATISTICS</b>\n\n👥 Users: <b>{users}</b>\n📦 Orders: <b>{orders}</b> (pending <b>{pending}</b>, completed <b>{completed}</b>)\n💵 Total USD: <b>{usd(tot_usd)}</b>\n💸 Pending Withdrawals: <b>{wd}</b>"
        await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="admin_menu")]]))
    finally: db.close()
    await call.answer()

@dp.callback_query(F.data == "admin_users")
async def cb_admin_users(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    db = get_db()
    try:
        users = db.execute("SELECT joined_at, user_id, first_name FROM users ORDER BY joined_at DESC LIMIT 50").fetchall()
        if not users:
            await call.message.edit_text("No users yet.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="admin_menu")]]))
        else:
            buttons = []
            for joined, uid, name in users:
                buttons.append([InlineKeyboardButton(text=f"👤 {name} ({uid})", callback_data=f"adm_u_{uid}")])
            buttons.append([InlineKeyboardButton(text="🗑 Clear Chat History", callback_data="admin_clear_chat")])
            buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="admin_menu")])
            await call.message.edit_text("👥 <b>USER LIST</b>\n\nClick a user for details:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    finally: db.close()
    await call.answer()

@dp.callback_query(F.data == "admin_clear_chat")
async def cb_admin_clear_chat(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    try:
        await call.message.delete()
        await call.message.answer("🗑 Chat history cleared.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back to Admin", callback_data="admin_menu")]]))
    except Exception: pass
    await call.answer("Cleared!")

@dp.callback_query(F.data == "admin_orders")
async def cb_admin_orders(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    rows = await get_all_orders()
    if not rows:
        text = "No orders."
    else:
        lines = ["📦 <b>RECENT ORDERS</b>\n"]
        for r in rows: lines.append(f"#{r[0]} | User <code>{r[1]}</code>\nRequest: <code>{safe(r[2])}</code>\nNumber: <code>{safe(r[3])}</code>\nStatus: {safe(r[4])}")
        text = "\n\n".join(lines)
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="admin_menu")]]))
    await call.answer()

@dp.callback_query(F.data == "admin_withdraws")
async def cb_admin_withdraws(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    db = get_db()
    try:
        rows = db.execute("SELECT w.id, w.user_id, w.amount_milli, w.wallet_ton, u.first_name FROM withdrawals w JOIN users u ON w.user_id = u.user_id WHERE w.status='PENDING' ORDER BY w.id DESC LIMIT 15").fetchall()
        if not rows:
            await call.message.edit_text("No pending TON withdrawals.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="admin_menu")]]))
        else:
            buttons = []
            for i, (rid, uid, amt, wallet, name) in enumerate(rows, 1):
                buttons.append([InlineKeyboardButton(text=f"{i}. {name} - {usd(amt)}", callback_data=f"wd_admin_view_{rid}")])
            buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="admin_menu")])
            await call.message.edit_text("💸 <b>PENDING WITHDRAWALS</b>\n\nClick a User to process:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    finally: db.close()
    await call.answer()

@dp.callback_query(F.data == "admin_withdraws_history")
async def cb_admin_withdraws_history(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    db = get_db()
    try:
        rows = db.execute("SELECT w.id, w.user_id, w.amount_milli, w.status, w.processed_at, w.reject_reason, u.first_name FROM withdrawals w JOIN users u ON w.user_id = u.user_id WHERE w.status IN ('APPROVED', 'REJECTED') ORDER BY w.processed_at DESC LIMIT 20").fetchall()
        if not rows:
            text = "No approval history."
        else:
            lines = ["📜 <b>APPROVAL HISTORY</b>\n"]
            for rid, uid, amt, status, p_at, reason, name in rows:
                icon = "✅" if status == "APPROVED" else "❌"
                note = f" - Reason: {reason}" if reason else ""
                lines.append(f"{icon} <b>Order #{rid}</b> | {p_at[:16] if p_at else ''}\n👤 {name} (<code>{uid}</code>)\n💵 {usd(amt)}{note}\n")
            text = "\n".join(lines)
        await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Clear History", callback_data="admin_clear_history")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="admin_menu")]
        ]))
    finally: db.close()
    await call.answer()

@dp.callback_query(F.data == "admin_clear_history")
async def cb_admin_clear_history(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    try:
        await call.message.delete()
        await call.message.answer("🗑 Approval history cleared.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="admin_menu")]]))
    except Exception: pass
    await call.answer("Cleared!")

@dp.callback_query(F.data.startswith("adm_u_"))
async def cb_adm_user_detail(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    uid = int(call.data.replace("adm_u_", ""))
    u = await get_user(uid)
    if not u:
        await call.answer("User not found.", show_alert=True); return
    text = f"👤 <b>USER DETAILS</b>\n\nID: <code>{uid}</code>\nName: {safe(u['first_name'])}\nUsername: @{safe(u['username'] or '—')}\nBalance: <b>{usd(u['usd_milli'])}</b>\n\n👇 Choose action:"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add Balance", callback_data=f"adm_cong_help_{uid}")],
        [InlineKeyboardButton(text="➖ Deduct Balance", callback_data=f"adm_tru_help_{uid}")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="admin_users")]
    ])
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()

@dp.callback_query(F.data.startswith("adm_cong_help_"))
async def cb_adm_cong_help(call: CallbackQuery):
    uid = call.data.replace("adm_cong_help_", "")
    text = f"➕ <b>ADD BALANCE INSTRUCTIONS</b>\n\nType this command in chat:\n\n<code>/addbal {uid} 10$</code>"
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data=f"adm_u_{uid}")]]))
    await call.answer()

@dp.callback_query(F.data.startswith("adm_tru_help_"))
async def cb_adm_tru_help(call: CallbackQuery):
    uid = call.data.replace("adm_tru_help_", "")
    text = f"➖ <b>DEDUCT BALANCE INSTRUCTIONS</b>\n\nType this command in chat:\n\n<code>/deductbal {uid} 10$</code>"
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data=f"adm_u_{uid}")]]))
    await call.answer()

@dp.callback_query(F.data.startswith("wd_admin_view_"))
async def cb_wd_admin_view(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    wid = int(call.data.replace("wd_admin_view_", ""))
    db = get_db()
    try:
        row = db.execute("SELECT w.id, w.user_id, w.amount_milli, w.wallet_ton, w.status, u.first_name FROM withdrawals w JOIN users u ON w.user_id = u.user_id WHERE w.id=?", (wid,)).fetchone()
        if not row or row[4] != "PENDING":
            await call.answer("Order already processed!", show_alert=True); return
        rid, uid, amt, wallet, status, name = row
        text = f"💸 <b>WITHDRAWAL REQUEST</b>\n\n👤 User: <b>{name}</b> (<code>{uid}</code>)\n💵 Amount: <b>{usd(amt)}</b>\n🔗 TON Wallet: <code>{wallet}</code>\n\n👇 Choose action:"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Approve (Send Bill)", callback_data=f"wd_approve_step1_{rid}")],
            [InlineKeyboardButton(text="⏳ Later", callback_data="admin_withdraws")],
            [InlineKeyboardButton(text="❌ Reject", callback_data=f"wd_reject_list_{rid}")]
        ])
        await call.message.edit_text(text, reply_markup=kb)
    finally: db.close()
    await call.answer()

@dp.callback_query(F.data.startswith("wd_approve_step1_"))
async def cb_wd_approve_step1(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    wid = int(call.data.replace("wd_approve_step1_", ""))
    ADMIN_PENDING_APPROVE[ADMIN_ID] = {"wid": wid, "step": "waiting_link"}
    text = f"🔗 <b>ADD TX HASH</b>\n\nPlease send the <b>TON Transaction Link (TX Hash)</b> to this chat."
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data=f"wd_admin_view_{wid}")]])
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()

@dp.message(F.text.regexp(r"^https?://"))
async def handle_admin_tx_hash(message: Message):
    if not is_admin(message.from_user.id): return
    state = ADMIN_PENDING_APPROVE.get(ADMIN_ID)
    if not state or state["step"] != "waiting_link": return

    wid = state["wid"]
    tx_hash = message.text.strip()
    state["tx_hash"] = tx_hash
    state["step"] = "confirm_link"
    ADMIN_PENDING_APPROVE[ADMIN_ID] = state

    text = f"🔗 <b>CONFIRM TX HASH</b>\n\nLink received:\n<code>{safe(tx_hash)}</code>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Confirm", callback_data="wd_confirm_link")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data=f"wd_admin_view_{wid}")]
    ])
    msg = await message.answer(text, reply_markup=kb)
    track_msg(message.from_user.id, msg.message_id)

@dp.callback_query(F.data == "wd_confirm_link")
async def cb_wd_confirm_link(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    state = ADMIN_PENDING_APPROVE.get(ADMIN_ID)
    if not state or state["step"] != "confirm_link": return

    wid = state["wid"]
    state["step"] = "waiting_photo"
    ADMIN_PENDING_APPROVE[ADMIN_ID] = state

    text = f"🖼 <b>ADD PROOF PHOTO</b>\n\nPlease send a <b>Photo of the transaction receipt</b> to this chat."
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data=f"wd_admin_view_{wid}")]])
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()

@dp.message(F.photo)
async def handle_admin_photo(message: Message):
    if not is_admin(message.from_user.id): return
    state = ADMIN_PENDING_APPROVE.get(ADMIN_ID)
    if not state or state["step"] != "waiting_photo": return

    wid = state["wid"]
    photo_id = message.photo[-1].file_id
    state["photo_id"] = photo_id
    state["step"] = "confirm_photo"
    ADMIN_PENDING_APPROVE[ADMIN_ID] = state

    text = f"🖼 <b>CONFIRM PROOF</b>\n\nYou sent 1 photo. Confirm approval for order <code>#{wid}</code> and send the bill to User?"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Confirm Approval", callback_data="wd_confirm_photo")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data=f"wd_admin_view_{wid}")]
    ])
    msg = await message.answer_photo(photo_id, caption=text, reply_markup=kb)
    track_msg(message.from_user.id, msg.message_id)

@dp.callback_query(F.data == "wd_confirm_photo")
async def cb_wd_confirm_photo(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    state = ADMIN_PENDING_APPROVE.get(ADMIN_ID)
    if not state or state["step"] != "confirm_photo": return

    wid = state["wid"]
    tx_hash = state["tx_hash"]
    photo_id = state["photo_id"]
    ADMIN_PENDING_APPROVE.pop(ADMIN_ID, None)

    db = get_db()
    try:
        db.execute("UPDATE withdrawals SET status='APPROVED', processed_at=?, tx_hash=?, proof_photo=? WHERE id=?", (now_text(), tx_hash, photo_id, wid))
        db.commit()
        row = db.execute("SELECT user_id, amount_milli, wallet_ton FROM withdrawals WHERE id=?", (wid,)).fetchone()
        uid, amt, wallet = row
    finally: db.close()

    text = f"🎉 <b>WITHDRAWAL SUCCESSFUL</b> 🎉\n\nCongratulations! Your withdrawal of <b>{usd(amt)}</b> has been approved.\n\nWallet: <code>{wallet}</code>\n"
    if tx_hash: 
        tonscan_url = tx_hash if tx_hash.startswith("http") else f"https://tonscan.org/tx/{tx_hash}"
        text += f"TX Hash: <code>{tx_hash}</code>\n<a href='{tonscan_url}'>👉 View on Tonscan</a>\n\n"
    text += "Thank you for choosing FAST IVAS. ❤️"
    
    try:
        await bot.send_photo(uid, photo_id, caption=text)
    except Exception as e: logger.error(f"Error sending bill to user: {e}")
    
    await call.message.edit_text(f"✅ Successfully approved order #{wid} and sent bill to User.")
    await call.answer("Approved successfully!")

@dp.callback_query(F.data.startswith("wd_reject_list_"))
async def cb_wd_reject_list(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    wid = int(call.data.replace("wd_reject_list_", ""))
    reasons = [("Wrong TON Address", "wrong_wallet"), ("Unsupported TON Network", "wrong_network"), ("Suspected Fraud", "fraud"), ("Wrong Amount", "wrong_amount"), ("Other", "other")]
    buttons = [[InlineKeyboardButton(text=r[0], callback_data=f"wd_reject_conf_{wid}_{r[1]}")] for r in reasons]
    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data=f"wd_admin_view_{wid}")])
    await call.message.edit_text(f"❌ <b>SELECT REJECTION REASON FOR ORDER #{wid}</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await call.answer()

@dp.callback_query(F.data.startswith("wd_reject_conf_"))
async def cb_wd_reject_conf(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    parts = call.data.replace("wd_reject_conf_", "").split("_")
    wid = int(parts[0]); reason_code = parts[1]
    reason_map = {"wrong_wallet": "Wrong TON Address", "wrong_network": "Unsupported TON Network", "fraud": "Suspected Fraud", "wrong_amount": "Wrong Amount", "other": "Other"}
    reason_text = reason_map.get(reason_code, "Unknown")
    db = get_db()
    try:
        row = db.execute("SELECT user_id, amount_milli FROM withdrawals WHERE id=? AND status='PENDING'", (wid,)).fetchone()
        if not row: await call.answer("Error!", show_alert=True); return
        uid, amt = row
    finally: db.close()
    text = f"⚠️ <b>CONFIRM CANCEL</b>\n\nReject withdrawal <code>#{wid}</code>.\nRefund: <b>{usd(amt)}</b>.\nReason: <b>{reason_text}</b>"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔥 CONFIRM CANCEL & REFUND", callback_data=f"wd_reject_final_{wid}_{reason_code}")], [InlineKeyboardButton(text="⬅️ Back", callback_data=f"wd_admin_view_{wid}")]])
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()

@dp.callback_query(F.data.startswith("wd_reject_final_"))
async def cb_wd_reject_final(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    parts = call.data.replace("wd_reject_final_", "").split("_")
    wid = int(parts[0]); reason_code = parts[1]
    reason_text = {"wrong_wallet": "Wrong TON Address", "wrong_network": "Unsupported TON Network", "fraud": "Suspected Fraud", "wrong_amount": "Wrong Amount", "other": "Other"}.get(reason_code, "Unknown")
    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT user_id, amount_milli, status FROM withdrawals WHERE id=?", (wid,)).fetchone()
        if not row or row[2] != "PENDING": db.rollback(); await call.answer("Already processed.", show_alert=True); return
        uid, amt = row[0], row[1]
        db.execute("UPDATE withdrawals SET status='REJECTED', processed_at=?, reject_reason=? WHERE id=?", (now_text(), reason_text, wid))
        db.execute("UPDATE users SET usd_milli=usd_milli+? WHERE user_id=?", (amt, uid))
        db.execute("INSERT INTO transactions (user_id, amount, tx_type, note, created_at) VALUES (?, ?, 'WITHDRAW_REFUND', ?, ?)", (uid, amt, f"Refund #{wid}: {reason_text}", now_text()))
        db.commit()
    finally: db.close()
    await call.message.edit_text(call.message.text + "\n\n❌ <b>CANCELLED AND REFUNDED</b>")
    await call.answer("Cancelled")
    try: await bot.send_message(uid, f"❌ <b>WITHDRAWAL REJECTED</b>\n\nOrder <code>#{wid}</code> was cancelled.\nReason: <b>{reason_text}</b>\nRefunded <b>{usd(amt)}</b> to your wallet.")
    except Exception: pass

@dp.message(Command("addbal"))
async def cmd_congtien(message: Message):
    try: await message.delete()
    except: pass
    if not is_admin(message.from_user.id): return
    parts = message.text.split()
    if len(parts) != 3 or not parts[1].isdigit():
        await message.answer("Usage: <code>/addbal ID AMOUNT</code>"); return
    uid = int(parts[1]); amt = int(float(parts[2].replace("$","")) * 1000)
    if amt <= 0: await message.answer("Amount must be > 0."); return
    u = await get_user(uid)
    if not u: await message.answer("User not found."); return
    db = get_db()
    try:
        cur = db.execute("INSERT INTO transactions (user_id, amount, tx_type, note, created_at) VALUES (?, ?, 'PENDING_ADD', 'Waiting for user confirmation', ?)", (uid, amt, now_text()))
        tid = cur.lastrowid; db.commit()
    finally: db.close()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Receive Now", callback_data=f"acc_recv_{tid}"), InlineKeyboardButton(text="❌ Cancel", callback_data=f"acc_cancel_{tid}")]])
    try:
        await bot.send_message(uid, f"🎁 <b>YOU RECEIVED MONEY!</b>\n\nAdmin added <b>{usd(amt)}</b>.\nClick <b>Receive Now</b> to add to wallet.", reply_markup=kb)
        await message.answer(f"✅ Sent request to add {usd(amt)} to {uid}.")
    except Exception as e: await message.answer(f"❌ Error: {e}")

@dp.callback_query(F.data.startswith("acc_recv_"))
async def cb_acc_recv(call: CallbackQuery):
    tid = int(call.data.replace("acc_recv_", ""))
    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT user_id, amount, tx_type FROM transactions WHERE id=?", (tid,)).fetchone()
        if not row or row[2] != "PENDING_ADD": db.rollback(); await call.answer("Error!", show_alert=True); return
        uid, amt, _ = row
        db.execute("UPDATE transactions SET tx_type='ADMIN_ADD' WHERE id=?", (tid,))
        db.execute("UPDATE users SET usd_milli=usd_milli+? WHERE user_id=?", (amt, uid))
        db.commit()
    finally: db.close()
    await call.message.edit_text(f"✅ Successfully received <b>{usd(amt)}</b>.")
    await call.answer("Received")

@dp.callback_query(F.data.startswith("acc_cancel_"))
async def cb_acc_cancel(call: CallbackQuery):
    tid = int(call.data.replace("acc_cancel_", ""))
    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT user_id, amount, tx_type FROM transactions WHERE id=?", (tid,)).fetchone()
        if not row or row[2] != "PENDING_ADD": db.rollback(); await call.answer("Error!", show_alert=True); return
        db.execute("UPDATE transactions SET tx_type='ADMIN_ADD_CANCEL' WHERE id=?", (tid,))
        db.commit()
    finally: db.close()
    await call.message.edit_text("❌ You cancelled receiving money.")
    await call.answer("Cancelled")

@dp.message(Command("deductbal"))
async def cmd_trutien(message: Message):
    try: await message.delete()
    except: pass
    if not is_admin(message.from_user.id): return
    parts = message.text.split()
    if len(parts) != 3 or not parts[1].isdigit():
        await message.answer("Usage: <code>/deductbal ID AMOUNT</code>"); return
    uid = int(parts[1]); amt = int(float(parts[2].replace("$","")) * 1000)
    if amt <= 0: await message.answer("Amount must be > 0."); return
    ok, new_usd = await change_usd(uid, -amt, "ADMIN_REMOVE", "Admin deduct")
    if not ok: await message.answer(f"❌ {safe(new_usd)}"); return
    await message.answer(f"✅ Deducted {usd(amt)} from {uid}.")

@dp.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    try: await message.delete()
    except: pass
    if not is_admin(message.from_user.id): return
    content = message.text.partition(" ")[2].strip()
    if not content: await message.answer("Usage: <code>/broadcast Message</code>"); return
    db = get_db()
    try: users = db.execute("SELECT user_id FROM users").fetchall()
    finally: db.close()
    sent = failed = 0
    for (uid,) in users:
        try:
            await bot.send_message(uid, "📢 <b>ANNOUNCEMENT</b>\n\n" + safe(content, 3500))
            sent += 1; await asyncio.sleep(0.05)
        except Exception: failed += 1
    await message.answer(f"📢 Done. OK: {sent} · Fail: {failed}")

# =====================================================
# OTP POLLER (XỬ LÝ TRUNG TÂM - HỖ TRỢ CẢ 2 NGUỒN VÀ LƯU PLATFORM)
# =====================================================
class MkOtpPoller:
    MAX_CONSECUTIVE_ERRORS = 5
    def __init__(self):
        self.interval = max(MK_POLL_MIN_SEC, 10) 
        self._consecutive_errors = 0

    async def _broadcast_otp(self, row, otp_code, full_sms, reward_milli, platform):
        user_name = f"User {row['user_id']}"
        u = await get_user(row["user_id"])
        if u and u["first_name"]: user_name = u["first_name"]
        
        flag = get_country_flag(row['country'])
        
        kb_group = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👁 View OTP", callback_data=f"show_otp_{row['id']}")],
            [
                InlineKeyboardButton(text="📢 Main Channel", url=MAIN_CHANNEL_URL),
                InlineKeyboardButton(text="🤖 Get Numbers", url=f"https://t.me/{BOT_USERNAME}?start=home")
            ]
        ])
        
        kb_user = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Get New Number", callback_data=f"new_num_{row['range_code']}")],
            [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")]
        ])

        group_text = (
            f"🔔 <b>NEW OTP RECEIVED</b>\n"
            f"<blockquote>"
            f"🟢 <b>Service :</b> {platform}\n"
            f"🌍 <b>Country :</b> {row['country']} {flag}\n"
            f"📞 <b>Number :</b> {mask_phone(row['phone'])}\n"
            f"🔑 <b>OTP :</b> <code>{otp_code}</code>"
            f"</blockquote>"
        )
        if full_sms: group_text += f"\n<blockquote>💬 {safe(full_sms, 300)}</blockquote>"

        user_text = (
            f"🔔 <b>NEW OTP RECEIVED</b>\n"
            f"<blockquote>"
            f"📦 <b>Order :</b> #{row['id']}\n"
            f"🟢 <b>Service :</b> {platform}\n"
            f"🌍 <b>Country :</b> {row['country']} {flag}\n"
            f"📞 <b>Number :</b> {row['phone']}\n"
            f"🔑 <b>OTP :</b> <code>{otp_code}</code>\n"
            f"💵 <b>Reward :</b> {usd(reward_milli)}"
            f"</blockquote>"
        )
        if full_sms: user_text += f"\n<blockquote>💬 {safe(full_sms, 300)}</blockquote>"

        if OTP_GROUP_ID:
            try:
                await bot.send_message(OTP_GROUP_ID, group_text, reply_markup=kb_group)
            except Exception as e: 
                logger.error(f"Error sending OTP to Group: {e}")
                try: await bot.send_message(ADMIN_ID, f"⚠️ Error sending OTP to Group: {e}")
                except: pass
            
        try:
            if row["user_id"] not in (ADMIN_ID, OTP_GROUP_ID):
                if row.get("msg_id"):
                    try:
                        await bot.edit_message_text(
                            chat_id=row["user_id"], message_id=row["msg_id"],
                            text=user_text, reply_markup=kb_user
                        )
                        return
                    except Exception:
                        pass 
                
                u_msg = await bot.send_message(row["user_id"], user_text, reply_markup=kb_user)
                track_msg(row["user_id"], u_msg.message_id)
        except Exception as e:
            logger.error(f"Error sending OTP to User: {e}")

    async def _process_otp(self, row, otp, sms):
        reward = REWARD_MILLI_PER_OTP
        platform = detect_otp_platform(sms) 
        
        db = get_db()
        try:
            db.execute("BEGIN IMMEDIATE")
            chk = db.execute("SELECT status FROM orders WHERE id=?", (row["id"],)).fetchone()
            if not chk or chk[0] != "PENDING":
                db.rollback()
                return False
            db.execute("UPDATE orders SET status='COMPLETED', otp_code=?, full_sms=?, platform=?, reward_milli=?, updated_at=? WHERE id=?", (otp, sms, platform, reward, now_text(), row["id"]))
            db.commit()
        except Exception:
            db.rollback()
            return False
        finally: db.close()
        
        ok, _ = await change_usd(row["user_id"], reward, "OTP_REWARD", f"Reward OTP #{row['id']}")
        if not ok: reward = 0
        await self._broadcast_otp(row, otp, sms, reward, platform)
        return True

    async def _poll_once(self):
        rows = await get_pending_requests(limit=MK_POLL_BATCH)
        if not rows: return 0, 0, False
        
        mk_rows = [r for r in rows if r.get("provider") == "MK"]
        np_rows = [r for r in rows if r.get("provider") == "NP"]
        
        checked = new_otp = 0
        api_error = False
        
        if mk_rows:
            ids = []
            by_req = {}
            for r in mk_rows:
                try:
                    rid_int = int(r["request_id"])
                    ids.append(rid_int)
                    by_req[rid_int] = r
                except (ValueError, TypeError):
                    await self._update_failed(r["id"])
            
            if ids:
                data, err = await api_request("POST", "check/status", {"request_ids": ids})
                if err: 
                    api_error = True
                else:
                    inner = data.get("data") if isinstance(data, dict) else None
                    results = inner.get("results") if isinstance(inner, dict) else None
                    
                    if isinstance(results, list):
                        for item in results:
                            try: rid = int(item.get("request_id"))
                            except (ValueError, TypeError): continue
                            
                            row = by_req.get(rid)
                            if not row: continue
                            checked += 1
                            status = (item.get("status") or "").lower()
                            
                            if status == "success":
                                otp = str(item.get("otp_code") or "").strip()
                                sms = str(item.get("full_sms") or "").strip()
                                if not otp:
                                    await self._update_failed(row["id"]); continue
                                
                                success = await self._process_otp(row, otp, sms)
                                if success:
                                    new_otp += 1
                            elif status in ["cancel", "failed", "expired", "refunded", "not_found"]:
                                await self._update_failed(row["id"])

        for r in np_rows:
            checked += 1
            data, err = await np_api_request("GET", "latest_otp", params={"number": r['phone']})
            if err:
                api_error = True
                continue
                
            if data and data.get("has_otp"):
                otp = str(data.get("otp_code") or "").strip()
                if otp:
                    sms = f"OTP from NumberPanel: {otp}"
                    success = await self._process_otp(r, otp, sms)
                    if success:
                        new_otp += 1
                        
        return checked, new_otp, api_error

    async def _update_failed(self, oid):
        db = get_db()
        try:
            db.execute("UPDATE orders SET status='FAILED', updated_at=? WHERE id=? AND status='PENDING'", (now_text(), oid))
            db.commit()
        finally: db.close()

    async def run_forever(self):
        while True:
            try:
                await expire_old_orders()
                checked, new_otp, api_error = await self._poll_once()
                if api_error:
                    self._consecutive_errors += 1
                    self.interval = min(MK_POLL_MAX_SEC, max(self.interval * 2, self.interval + 5))
                else:
                    self._consecutive_errors = 0
                    if checked == 0: self.interval = min(MK_POLL_MAX_SEC, self.interval + 5)
                    elif new_otp > 0: self.interval = max(MK_POLL_MIN_SEC, self.interval - 2)
                    else: self.interval = max(MK_POLL_MIN_SEC, self.interval - 1)
            except Exception as e:
                logger.error(f"Poller error: {e}")
                self.interval = min(MK_POLL_MAX_SEC, max(self.interval * 2, 15))
            await asyncio.sleep(self.interval)

@dp.callback_query(F.data.startswith("show_otp_"))
async def cb_show_otp(call: CallbackQuery):
    oid = int(call.data.replace("show_otp_", ""))
    row = await get_order(oid)
    if not row or not row.get("otp_code"):
        await call.answer("OTP not found for this order!", show_alert=True); return
    platform = detect_otp_platform(row.get("full_sms", ""))
    await call.answer(f"Your {platform} OTP is: {row['otp_code']}", show_alert=True)

# =====================================================
# WEB SERVER & MAIN
# =====================================================
async def web_server():
    async def handle(request): return web.Response(text="Bot is running!")
    app = web.Application(); app.router.add_get('/', handle)
    runner = web.AppRunner(app); await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port); await site.start()
    logger.info(f"Web server started on port {port}")

@dp.message(F.text)
async def unknown(message: Message):
    if message.text.startswith('/'): return
    try: await message.delete()
    except: pass
    msg = await message.answer("Type /start to open FAST IVAS menu.", reply_markup=get_main_reply_kb(message.from_user.id))
    track_msg(message.from_user.id, msg.message_id)

async def set_bot_commands():
    user_commands = [
        BotCommand(command="start", description="Open main menu"),
        BotCommand(command="profile", description="View profile"),
        BotCommand(command="wallet", description="View USD wallet"),
        BotCommand(command="getnum", description="Get OTP Number (e.g. /getnum 84XXX)"),
        BotCommand(command="withdraw", description="Withdraw USD menu"),
        BotCommand(command="history", description="Transaction history"),
        BotCommand(command="id", description="Get Telegram ID"),
    ]
    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

    admin_commands = user_commands + [
        BotCommand(command="admin", description="[Admin] Open admin panel"),
        BotCommand(command="health", description="[Admin] Check bot health"),
        BotCommand(command="pollnow", description="[Admin] Force poll OTP now"),
        BotCommand(command="broadcast", description="[Admin] Broadcast message"),
        BotCommand(command="addbal", description="[Admin] Add balance to user"),
        BotCommand(command="deductbal", description="[Admin] Deduct user balance"),
        BotCommand(command="whoami", description="[Admin] View MK account info"),
        BotCommand(command="access_list", description="[Admin] View MK ranges"),
        BotCommand(command="radar", description="[Admin] View MK radar"),
    ]
    try: await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=ADMIN_ID))
    except Exception as e: logger.error(f"Error setting admin commands: {e}")

async def main():
    global _mk_poller, BOT_USERNAME
    try: 
        me = await bot.get_me()
        BOT_USERNAME = me.username
        await set_bot_commands()
    except Exception as e: logger.error(f"Error setting menu: {e}")

    await init_db(); await expire_old_orders()
    asyncio.create_task(web_server())

    if MK_POLL_ENABLED:
        _mk_poller = MkOtpPoller()
        asyncio.create_task(_mk_poller.run_forever())
        logger.info("Poller task created.")

    logger.info("FAST IVAS starting...")
    await dp.start_polling(bot, drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())