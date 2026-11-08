import os
import re
import json
import html
import asyncio
import logging
import random
import hashlib
import hmac
import time
from urllib.parse import parse_qsl
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from aiohttp import web
from types import SimpleNamespace

import aiohttp
import libsql_experimental as libsql
from aiogram import Bot, Dispatcher, F, BaseMiddleware
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    BotCommand, BotCommandScopeChat, BotCommandScopeDefault,
    ReplyKeyboardRemove, MenuButtonWebApp, WebAppInfo
)
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

# =====================================================
# CẤU HÌNH HỆ THỐNG (BRO NHỚ ĐIỀN TOKEN MỚI VÀO ĐÂY)
# =====================================================
BOT_TOKEN      = os.getenv("BOT_TOKEN", "").strip()
WEBAPP_URL     = os.getenv("WEBAPP_URL", "").strip()
ADMIN_ID       = int(os.getenv("ADMIN_ID", "0") or 0)

OTP_GROUP_ID   = int(os.getenv("OTP_GROUP_ID", "-1004341368656"))
OTP_GROUP_URL  = "https://t.me/LIVEOTPIVAS"
MAIN_CHANNEL_URL = "https://t.me/FastNode_1"

# Cấu hình API Nguồn 1: MK Network
MK_API_KEY     = os.getenv("MK_API_KEY", "").strip()
MK_API_BASE    = "https://mknetworkbd.com/api/v3/public"

# Cấu hình API Nguồn 2: Number Panel (NP)
NP_API_KEY     = os.getenv("NP_API_KEY", "").strip()
NP_API_BASE    = "https://numberpanel.tech/api"

# Cấu hình API Nguồn 3: Basha
BASHA_API_KEY  = os.getenv("BASHA_API_KEY", "").strip()
BASHA_API_BASE = "https://basha.cc/api"

# Cấu hình API Nguồn 4: SL Virtual Number
SLVN_API_KEY   = os.getenv("SLVN_API_KEY", "").strip()
SLVN_API_BASE  = "https://slvirtualnumber.com/api/v1/developer"

# Cấu hình Database (Turso / SQLite)
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL", "").strip()
TURSO_AUTH_TOKEN   = os.getenv("TURSO_AUTH_TOKEN", "").strip()
SQLITE_PATH        = os.getenv("SQLITE_PATH", "fast_ivas.db")
PORT               = int(os.getenv("PORT", "10000"))

# Các hằng số cài đặt
ORDER_LIFETIME_MINUTES = 15
REWARD_MILLI_PER_OTP   = 2
MIN_WITHDRAW_MILLI     = 1000       # Tối thiểu 1$
MAX_WITHDRAW_MILLI     = 1000000
WITHDRAW_FEE_MILLI     = 100        # Phí rút toàn bộ 0.1$
HISTORY_PAGE_SIZE      = 10         # Mỗi trang 10 đơn
MAX_HISTORY_PAGES      = 100        # Tối đa 100 trang (1000 đơn)
MAX_HISTORY_RECORDS    = HISTORY_PAGE_SIZE * MAX_HISTORY_PAGES

DB_TIMEOUT_SECONDS     = 10.0
DB_WORKERS             = 4

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FAST_IVAS")

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp  = Dispatcher()
db_executor = ThreadPoolExecutor(max_workers=DB_WORKERS)
BOT_USERNAME = ""
VN_TZ = timezone(timedelta(hours=7))
started_at = time.time()

class ErrorMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        try:
            return await handler(event, data)
        except Exception as e:
            logger.error(f"Handler error: {e}")
            try:
                if isinstance(event, Message):
                    await event.answer(f"⚠️ <b>Lỗi hệ thống:</b> <code>{safe(str(e))}</code>")
            except: pass

dp.message.middleware(ErrorMiddleware())
dp.callback_query.middleware(ErrorMiddleware())

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

async def register_user(tg_user, referrer=None):
    res = await db_exec("SELECT user_id FROM users WHERE user_id=?", (tg_user.id,), fetch="one")
    if res:
        await db_exec("UPDATE users SET username=?, first_name=? WHERE user_id=?", (tg_user.username, tg_user.first_name or "User", tg_user.id))
        return False
    if referrer == tg_user.id: referrer = None
    await db_exec("INSERT INTO users (user_id, username, first_name, referrer, joined_at) VALUES (?, ?, ?, ?, ?)", (tg_user.id, tg_user.username, tg_user.first_name or "User", referrer, now_text()))
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
    if res and res["c"] > MAX_HISTORY_RECORDS:
        to_delete = res["c"] - MAX_HISTORY_RECORDS
        await db_exec("DELETE FROM orders WHERE id IN (SELECT id FROM orders WHERE user_id=? ORDER BY id ASC LIMIT ?)", (uid, to_delete))

async def api_request(method, endpoint, payload=None, params=None, api_type="MK"):
    headers = {"Accept": "application/json"}
    if api_type == "MK": headers["mknetwork-key"] = MK_API_KEY; base = MK_API_BASE
    elif api_type == "NP": headers["Authorization"] = f"Bearer {NP_API_KEY}"; base = NP_API_BASE
    elif api_type == "BASHA": headers["Authorization"] = f"Bearer {BASHA_API_KEY}"; base = BASHA_API_BASE
    elif api_type == "SLVN": headers["x-api-key"] = SLVN_API_KEY; base = SLVN_API_BASE
    
    if payload is not None: headers["Content-Type"] = "application/json"
    url = f"{base}/{endpoint.lstrip('/')}"
    timeout = aiohttp.ClientTimeout(total=25)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.request(method, url, headers=headers, json=payload, params=params) as r:
                raw = await r.text()
                try: data = json.loads(raw)
                except json.JSONDecodeError: data = {"response": raw[:1000]}
                if r.status >= 400: return None, f"API Error {r.status}: {raw[:100]}"
                return data, None
    except asyncio.TimeoutError: return None, "Connection timeout."
    except Exception as e: return None, str(e)

@dp.message(CommandStart())
async def cmd_start(message: Message):
    try: await message.delete()
    except: pass
    args = message.text.split(maxsplit=1)
    ref = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    await register_user(message.from_user, ref)
    
    if WEBAPP_URL.startswith("https://"):
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚡ MỞ ỨNG DỤNG FAST IVAS", web_app=WebAppInfo(url=WEBAPP_URL))]])
        # XÓA SẠCH BÀN PHÍM REPLY KEYBOARD
        await message.answer("🚀 Chào mừng đến với <b>FAST IVAS</b>!\n\nVui lòng bấm nút bên dưới để mở ứng dụng.", reply_markup=ReplyKeyboardRemove())
        await message.answer("👇", reply_markup=kb)
    else:
        await message.answer("⚠️ Lỗi: Chưa cấu hình WEBAPP_URL.", reply_markup=ReplyKeyboardRemove())

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id): return
    await message.answer("🛡 <b>ADMIN PANEL</b>\n\nMở Mini App và vào mục ADMIN PANEL để quản lý.")

@dp.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    if not is_admin(message.from_user.id): return
    content = message.text.partition(" ")[2].strip()
    if not content: return await message.answer("Usage: /broadcast Message")
    users = await db_exec("SELECT user_id FROM users", fetch="all")
    sent = 0
    for row in users or []:
        try: await bot.send_message(row["user_id"], f"📢 <b>ANNOUNCEMENT</b>\n\n{content}"); sent += 1; await asyncio.sleep(0.05)
        except: pass
    await message.answer(f"Đã gửi {sent} tin nhắn.")

@dp.message(F.text)
async def handle_text(message: Message):
    if message.text.startswith('/'): return
    # Không gửi menu nữa, chỉ nhắc nhở
    await message.answer("Vui lòng mở Mini App để sử dụng các tính năng.")

def validate_telegram_init_data(init_data: str) -> dict | None:
    if not init_data or len(init_data) > 16384: return None
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = pairs.pop("hash", None)
        if not received_hash: return None
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calculated, received_hash): return None
        auth_date = int(pairs.get("auth_date", "0"))
        if auth_date <= 0 or abs(unix_now() - auth_date) > 86400: return None
        user = json.loads(pairs.get("user", "{}"))
        if not isinstance(user, dict) or not user.get("id"): return None
        return user
    except: return None

@web.middleware
async def mini_auth_middleware(request, handler):
    if request.path.startswith("/api/mini/"):
        tg_user = validate_telegram_init_data(request.headers.get("X-Telegram-Init-Data", ""))
        if not tg_user: return web.json_response({"error": "Invalid session"}, status=401)
        request["tg_user"] = tg_user
        await register_user(SimpleNamespace(id=int(tg_user["id"]), username=tg_user.get("username"), first_name=tg_user.get("first_name") or "User"))
    return await handler(request)

def mini_uid(request): return int(request["tg_user"]["id"])
def mini_admin_guard(request): return is_admin(mini_uid(request))

async def mini_me(request):
    uid = mini_uid(request)
    u = await get_user(uid)
    total = await db_exec("SELECT COUNT(*) as c FROM orders WHERE user_id=?", (uid,), fetch="one")
    today = await db_exec("SELECT COUNT(*) as c FROM orders WHERE user_id=? AND status='COMPLETED' AND created_at >= ?", (uid, now().strftime("%Y-%m-%d")), fetch="one")
    return web.json_response({
        "user": {
            "id": u['user_id'], "first_name": u['first_name'], "usd_milli": u['usd_milli'], 
            "wallet_ton": u['wallet_ton'] or "", "joined_at": u['joined_at']
        }, 
        "total_orders": total["c"] if total else 0, 
        "today_otps": today["c"] if today else 0,
        "is_admin": is_admin(uid), 
        "referral_link": f"https://t.me/{BOT_USERNAME}?start={uid}"
    })

async def mini_leaderboard(request):
    # Lấy top 10 user có số dư cao nhất
    top_users = await db_exec("SELECT first_name, usd_milli FROM users ORDER BY usd_milli DESC LIMIT 10", fetch="all")
    return web.json_response({
        "leaderboard": [{"name": u["first_name"], "balance": u["usd_milli"]} for u in top_users] if top_users else []
    })

async def mini_active_orders(request):
    uid = mini_uid(request)
    rows = await db_exec("SELECT id, provider, phone, country, status, created_at, otp_code, platform FROM orders WHERE user_id=? AND status='PENDING' ORDER BY id DESC", (uid,), fetch="all")
    orders = []
    if rows:
        for r in rows:
            orders.append({
                "id": r["id"], "provider": r["provider"], "phone": r["phone"], "country": r["country"],
                "status": r["status"], "created_at": r["created_at"], "otp": r["otp_code"], "platform": r["platform"] or "",
                "flag": get_country_flag(r["country"])
            })
    return web.json_response({"orders": orders})

async def mini_history_orders(request):
    uid = mini_uid(request)
    try: page = int(request.query.get("page", "1"))
    except: page = 1
    
    if page < 1: page = 1
    offset = (page - 1) * HISTORY_PAGE_SIZE
    
    total_res = await db_exec("SELECT COUNT(*) as c FROM orders WHERE user_id=?", (uid,), fetch="one")
    total = total_res["c"] if total_res else 0
    total_pages = max(1, (total + HISTORY_PAGE_SIZE - 1) // HISTORY_PAGE_SIZE)
    
    if page > total_pages: page = total_pages
    offset = (page - 1) * HISTORY_PAGE_SIZE
    
    rows = await db_exec("SELECT id, provider, phone, country, status, created_at, otp_code, platform FROM orders WHERE user_id=? ORDER BY id DESC LIMIT ? OFFSET ?", (uid, HISTORY_PAGE_SIZE, offset), fetch="all")
    orders = []
    if rows:
        for r in rows:
            orders.append({
                "id": r["id"], "provider": r["provider"], "phone": r["phone"], "country": r["country"],
                "status": r["status"], "created_at": r["created_at"], "otp": r["otp_code"], "platform": r["platform"] or "",
                "flag": get_country_flag(r["country"])
            })
    return web.json_response({
        "orders": orders,
        "current_page": page,
        "total_pages": total_pages,
        "total_records": total
    })

async def mini_create_order(request):
    uid = mini_uid(request); body = await request.json()
    provider = body.get("provider")
    
    if provider == "MK":
        data, err = await api_request("POST", "getnum/number", {"range": body.get("range")})
        if err or not data: return web.json_response({"error": err or "Lỗi API MK"}, status=400)
        def find_id(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if ("id" in str(k).lower() or "request" in str(k).lower()) and str(v).isdigit(): return str(v)
                for v in obj.values():
                    res = find_id(v)
                    if res: return res
            elif isinstance(obj, list):
                for i in obj:
                    res = find_id(i)
                    if res: return res
            return None
        rid = find_id(data)
        phone = data.get("number") or data.get("phone") or "N/A"
        country = body.get("country_name") or "Unknown"
        await db_exec("INSERT INTO orders (user_id, request_id, provider, phone, country, range_code, status, created_at, expires_at) VALUES (?, ?, 'MK', ?, ?, ?, 'PENDING', ?, ?)", 
                      (uid, rid, str(phone), country, body.get("range"), now_text(), (now() + timedelta(minutes=15)).isoformat()))
        await clean_old_orders(uid)
        return web.json_response({"ok": True})

    elif provider == "NP":
        data, err = await api_request("POST", "request_number", {"service": body.get("service"), "country": body.get("country")}, api_type="NP")
        if err or not data: return web.json_response({"error": err or "Lỗi API NP"}, status=400)
        phone = data.get("number"); rid = data.get("id") or phone
        await db_exec("INSERT INTO orders (user_id, request_id, provider, phone, country, operator, range_code, status, created_at, expires_at) VALUES (?, ?, 'NP', ?, ?, ?, ?, 'PENDING', ?, ?)", 
                      (uid, str(rid), str(phone), body.get("country"), body.get("service"), body.get("service"), now_text(), (now() + timedelta(minutes=15)).isoformat()))
        await clean_old_orders(uid)
        return web.json_response({"ok": True})

    elif provider == "BASHA":
        row = await db_exec("SELECT phone, country FROM basha_numbers WHERE country=? ORDER BY RANDOM() LIMIT 1", (body.get("country"),), fetch="one")
        if not row: return web.json_response({"error": "Hết số BS"}, status=404)
        await db_exec("INSERT INTO orders (user_id, request_id, provider, phone, country, range_code, status, created_at, expires_at) VALUES (?, ?, 'BASHA', ?, ?, ?, 'PENDING', ?, ?)", 
                      (uid, row["phone"], row["phone"], row["country"], row["country"], now_text(), (now() + timedelta(minutes=15)).isoformat()))
        await clean_old_orders(uid)
        return web.json_response({"ok": True})

    elif provider == "SLVN":
        if not SLVN_API_KEY: return web.json_response({"error": "Chưa cấu hình SLVN_API_KEY trên server"}, status=400)
        
        payload = {
            "service": "ANY",
            "countryCode": body.get("country_code"),
            "tag": body.get("tag")
        }
        data, err = await api_request("POST", "rent", payload, api_type="SLVN")
        
        if err: return web.json_response({"error": f"Lỗi kết nối API: {err}"}, status=400)
        if not data or data.get("status") != "success":
            error_msg = data.get("message") if data else "Không có phản hồi"
            return web.json_response({"error": f"API báo lỗi: {error_msg}"}, status=400)
        
        order_data = data.get("data", {})
        rental_id = order_data.get("rentalId")
        phone = order_data.get("phoneNumber")
        country = order_data.get("country")
        
        await db_exec("INSERT INTO orders (user_id, request_id, provider, phone, country, range_code, status, created_at, expires_at) VALUES (?, ?, 'SLVN', ?, ?, ?, 'PENDING', ?, ?)", 
                      (uid, rental_id, phone, country, body.get("tag"), now_text(), (now() + timedelta(minutes=15)).isoformat()))
        await clean_old_orders(uid)
        return web.json_response({"ok": True})

    return web.json_response({"error": "Provider không hợp lệ"}, status=400)

async def mini_cancel_order(request):
    oid = int(request.match_info["oid"])
    order = await db_exec("SELECT provider, request_id FROM orders WHERE id=? AND user_id=?", (oid, mini_uid(request)), fetch="one")
    if not order: return web.json_response({"error": "Not found"}, status=404)
    
    if order["provider"] == "SLVN":
        await api_request("POST", f"cancel/{order['request_id']}", api_type="SLVN")
        
    await db_exec("UPDATE orders SET status='CANCELLED' WHERE id=?", (oid,))
    return web.json_response({"ok": True})

async def mini_save_wallet(request):
    uid = mini_uid(request); body = await request.json()
    address = str(body.get("address", "")).strip()
    if not re.fullmatch(r"(?:EQ|UQ)[a-zA-Z0-9_-]{46}", address):
        return web.json_response({"error": "Địa chỉ TON không đúng định dạng."}, status=400)
    await db_exec("UPDATE users SET wallet_ton=? WHERE user_id=?", (address, uid))
    return web.json_response({"ok": True})

async def mini_withdraw(request):
    uid = mini_uid(request); body = await request.json()
    amt_milli = int(float(body.get("amount", 0)) * 1000)
    u = await db_exec("SELECT wallet_ton, usd_milli FROM users WHERE user_id=?", (uid,), fetch="one")
    if not u or not u["wallet_ton"]: return web.json_response({"error": "Chưa cài ví TON"}, status=400)
    if amt_milli < MIN_WITHDRAW_MILLI or amt_milli > u["usd_milli"]: return web.json_response({"error": "Số dư không đủ hoặc dưới $1.00"}, status=400)
    
    ok, res = await change_usd(uid, -amt_milli, "WITHDRAW_HOLD", "TON Withdrawal")
    if not ok: return web.json_response({"error": res}, status=400)
    
    wid = await db_exec("INSERT INTO withdrawals (user_id, amount_milli, wallet_ton, status, created_at) VALUES (?, ?, ?, 'PENDING', ?)", (uid, amt_milli, u["wallet_ton"], now_text()))
    return web.json_response({"ok": True, "withdrawal_id": wid})

async def mini_mk_ranges(request):
    return web.json_response({"countries": [{"name": k, "range": v, "flag": get_country_flag(k)} for k, v in FALLBACK_COUNTRIES.items()]})

async def mini_np_services(request):
    data, err = await api_request("GET", "services", api_type="NP")
    srvs = data.get("services", []) if data and not err else []
    return web.json_response({"services": [{"name": s["name"], "key": s["key"], "count": s["count"]} for s in srvs if s.get("count", 0) > 0]})

async def mini_np_countries(request):
    service = request.match_info["service"]
    data, err = await api_request("GET", "countries", params={"service": service}, api_type="NP")
    countries = data.get("countries", []) if data and not err else []
    return web.json_response({"countries": [{"code": c["name"], "name": ISO_MAP.get(c["name"], c["name"]), "count": c["count"]} for c in countries if c.get("count", 0) > 0]})

async def mini_bs_countries(request):
    rows = await db_exec("SELECT country, flag, COUNT(*) as c FROM basha_numbers GROUP BY country, flag", fetch="all")
    return web.json_response({"countries": [{"name": r["country"], "flag": r["flag"], "count": r["c"]} for r in rows] if rows else []})

async def mini_slvn_countries(request):
    if not SLVN_API_KEY: return web.json_response({"countries": []})
    data, err = await api_request("GET", "available-countries", params={"service": "any"}, api_type="SLVN")
    if err or not data: return web.json_response({"countries": []})
    
    countries = []
    for c in data.get("data", []):
        countries.append({
            "name": c.get("country"),
            "code": c.get("countryCode"),
            "flag": c.get("flag"),
            "tag": c.get("tag"),
            "rate": c.get("rateUsd")
        })
    return web.json_response({"countries": countries})

async def mini_admin_data(request):
    if not mini_admin_guard(request): return web.json_response({"error": "Forbidden"}, status=403)
    users = await db_exec("SELECT COUNT(*) as c FROM users", fetch="one")
    orders = await db_exec("SELECT COUNT(*) as c FROM orders", fetch="one")
    pending_wd = await db_exec("SELECT COUNT(*) as c FROM withdrawals WHERE status='PENDING'", fetch="one")
    bs_count = await db_exec("SELECT COUNT(*) as c FROM basha_numbers", fetch="one")
    
    wd_list = await db_exec("SELECT w.id, w.user_id, w.amount_milli, w.wallet_ton, u.first_name FROM withdrawals w JOIN users u ON u.user_id=w.user_id WHERE w.status='PENDING' ORDER BY w.id DESC LIMIT 20", fetch="all")
    
    return web.json_response({
        "stats": {"users": users["c"], "orders": orders["c"], "pending_wd": pending_wd["c"], "bs_count": bs_count["c"]},
        "withdrawals": [{"id": r["id"], "user_id": r["user_id"], "amount": r["amount_milli"], "wallet": r["wallet_ton"], "name": r["first_name"]} for r in wd_list] if wd_list else []
    })

async def mini_admin_bs_add(request):
    if not mini_admin_guard(request): return web.json_response({"error": "Forbidden"}, status=403)
    body = await request.json(); raw = str(body.get("numbers", ""))
    lines = [x.strip().lstrip("+") for x in re.split(r"[\s,;]+", raw) if x.strip()]
    added = 0
    for phone in lines:
        if not phone.isdigit() or len(phone) < 7: continue
        country, flag = ("Unknown", "🌐")
        for pfx in SORTED_PREFIXES:
            if phone.startswith(pfx): country, flag = COUNTRY_CODES[pfx]; break
        exists = await db_exec("SELECT id FROM basha_numbers WHERE phone=?", (phone,), fetch="one")
        if not exists:
            res = await db_exec("INSERT INTO basha_numbers (phone, country, flag, added_at) VALUES (?,?,?,?)", (phone, country, flag, now_text()))
            if res: added += 1
    return web.json_response({"ok": True, "added": added})

async def mini_admin_wd_action(request):
    if not mini_admin_guard(request): return web.json_response({"error": "Forbidden"}, status=403)
    body = await request.json()
    wid = int(body.get("wid")); action = body.get("action")
    if action == "approve":
        await db_exec("UPDATE withdrawals SET status='APPROVED', processed_at=? WHERE id=?", (now_text(), wid))
        return web.json_response({"ok": True})
    elif action == "reject":
        row = await db_exec("SELECT user_id, amount_milli FROM withdrawals WHERE id=? AND status='PENDING'", (wid,), fetch="one")
        if not row: return web.json_response({"error": "Not found"}, status=404)
        uid, amt = row["user_id"], row["amount_milli"]
        await db_exec("UPDATE withdrawals SET status='REJECTED', processed_at=? WHERE id=?", (now_text(), wid))
        await change_usd(uid, amt, "WITHDRAW_REFUND", f"Refund #{wid}")
        return web.json_response({"ok": True})

MINIAPP_HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>FAST IVAS</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

        :root {
            --bg: #0B1120;
            --surface: rgba(30, 41, 59, 0.7);
            --surface-hover: rgba(51, 65, 85, 0.8);
            --primary: #3b82f6;
            --primary-gradient: linear-gradient(135deg, #3b82f6, #8b5cf6);
            --success: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --border: rgba(255, 255, 255, 0.1);
            --radius: 16px;
            --shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
            --glass-blur: blur(12px);
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Outfit', sans-serif; -webkit-tap-highlight-color: transparent; }
        body { 
            background-color: var(--bg); 
            background-image: radial-gradient(circle at 10% 20%, rgba(59, 130, 246, 0.15) 0%, transparent 20%), radial-gradient(circle at 90% 80%, rgba(139, 92, 246, 0.15) 0%, transparent 20%);
            color: var(--text); padding-bottom: 80px; overflow-x: hidden; min-height: 100vh;
        }
        button { cursor: pointer; font-family: inherit; border: none; outline: none; }

        /* --- CUSTOM CONFIRM MODAL --- */
        #custom-modal {
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background: rgba(0,0,0,0.7); backdrop-filter: blur(5px); z-index: 9999;
            display: none; justify-content: center; align-items: center; padding: 20px;
        }
        #custom-modal.open { display: flex; }
        .modal-content {
            background: var(--bg); border: 1px solid var(--border); border-radius: 20px;
            padding: 24px; width: 100%; max-width: 340px; text-align: center;
            box-shadow: var(--shadow); animation: popIn 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
        @keyframes popIn { from { transform: scale(0.8); opacity: 0; } to { transform: scale(1); opacity: 1; } }
        .modal-title { font-size: 20px; font-weight: 700; margin-bottom: 10px; color: var(--text); }
        .modal-msg { font-size: 15px; color: var(--text-muted); margin-bottom: 24px; line-height: 1.5; }
        .modal-actions { display: flex; gap: 12px; }
        .modal-actions button { flex: 1; padding: 14px; border-radius: 12px; font-weight: 600; font-size: 15px; }

        /* --- SIDEBAR --- */
        .sidebar {
            position: fixed; top: 0; left: -300px; width: 300px; height: 100vh;
            background: rgba(15, 23, 42, 0.95); backdrop-filter: var(--glass-blur);
            z-index: 1000; transition: 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 4px 0 24px rgba(0,0,0,0.5); display: flex; flex-direction: column;
            border-right: 1px solid var(--border);
        }
        .sidebar.open { left: 0; }
        .overlay {
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background: rgba(0,0,0,0.6); backdrop-filter: blur(4px); z-index: 999; display: none;
            opacity: 0; transition: opacity 0.3s;
        }
        .overlay.open { display: block; opacity: 1; }
        
        .sidebar-header { padding: 30px 20px; border-bottom: 1px solid var(--border); text-align: center; }
        .sidebar-header h2 { background: var(--primary-gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 24px; font-weight: 700; }
        .sidebar-user { font-size: 13px; color: var(--text-muted); margin-top: 5px; }
        
        .sidebar-menu { flex: 1; padding: 20px 10px; overflow-y: auto; }
        .menu-item {
            display: flex; align-items: center; padding: 15px 20px;
            color: var(--text-muted); text-decoration: none; transition: 0.2s;
            font-weight: 500; font-size: 16px; border-radius: 12px; margin-bottom: 5px;
        }
        .menu-item:hover, .menu-item.active { background: var(--surface-hover); color: var(--text); }
        .menu-item .icon { margin-right: 15px; font-size: 22px; }
        .menu-admin { border-top: 1px solid var(--border); margin-top: 10px; padding-top: 10px; color: var(--danger); }

        /* --- TOP BAR --- */
        .top-bar {
            display: flex; align-items: center; padding: 15px 20px;
            background: rgba(15, 23, 42, 0.8); backdrop-filter: var(--glass-blur);
            position: sticky; top: 0; z-index: 100; border-bottom: 1px solid var(--border);
        }
        .menu-btn { 
            background: var(--surface); border: 1px solid var(--border); font-size: 20px; 
            color: var(--text); margin-right: 15px; width: 40px; height: 40px; 
            border-radius: 10px; display: flex; align-items: center; justify-content: center;
            transition: 0.2s;
        }
        .menu-btn:active { transform: scale(0.9); }
        .page-title { font-size: 20px; font-weight: 700; color: var(--text); flex: 1; text-align: center; padding-right: 55px;}

        /* --- MAIN CONTENT --- */
        .container { padding: 20px; animation: fadeIn 0.4s ease; }
        .view { display: none; }
        .view.active { display: block; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(15px); } to { opacity: 1; transform: translateY(0); } }

        /* --- CARDS --- */
        .card {
            background: var(--surface); backdrop-filter: var(--glass-blur);
            border-radius: var(--radius); padding: 20px; margin-bottom: 20px;
            box-shadow: var(--shadow); border: 1px solid var(--border);
        }
        
        /* --- HOME STATS --- */
        .balance-card {
            background: var(--primary-gradient); border: none; position: relative; overflow: hidden;
        }
        .balance-card::before {
            content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.2) 0%, transparent 60%); opacity: 0.5;
        }
        .balance-title { font-size: 15px; color: rgba(255,255,255,0.8); font-weight: 500; }
        .balance-amount { font-size: 36px; font-weight: 700; color: #fff; margin-top: 5px; text-shadow: 0 2px 10px rgba(0,0,0,0.2); }
        
        .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px; }
        .stat-box { background: var(--surface); padding: 15px; border-radius: var(--radius); text-align: center; border: 1px solid var(--border); }
        .stat-box .value { font-size: 22px; font-weight: 700; color: var(--text); margin-top: 5px; }
        .stat-box .label { font-size: 13px; color: var(--text-muted); font-weight: 500; }

        /* --- FORMS & BUTTONS --- */
        .form-group { margin-bottom: 15px; }
        .form-label { display: block; font-size: 14px; color: var(--text-muted); margin-bottom: 8px; font-weight: 500; }
        .form-control {
            width: 100%; padding: 14px 16px; border-radius: 12px;
            background: rgba(15, 23, 42, 0.6); color: var(--text); border: 1px solid var(--border);
            font-size: 16px; transition: 0.2s; outline: none;
        }
        .form-control:focus { border-color: var(--primary); box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2); }
        
        .btn {
            width: 100%; padding: 15px; border-radius: 12px; font-size: 16px;
            font-weight: 600; display: flex; justify-content: center; align-items: center;
            gap: 8px; transition: 0.2s; margin-top: 10px; color: #fff;
        }
        .btn:active { transform: scale(0.97); }
        .btn-primary { background: var(--primary-gradient); box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3); }
        .btn-success { background: var(--success); box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3); }
        .btn-danger { background: var(--danger); box-shadow: 0 4px 15px rgba(239, 68, 68, 0.3); }
        .btn-outline { background: transparent; border: 1px solid var(--border); }
        
        /* --- ORDER CARDS --- */
        .order-card {
            background: var(--surface); border-radius: var(--radius); padding: 16px;
            margin-bottom: 15px; border: 1px solid var(--border);
            position: relative; overflow: hidden; transition: 0.3s;
        }
        .order-card.pending { border-left: 4px solid var(--warning); }
        .order-card.completed { border-left: 4px solid var(--success); background: rgba(16, 185, 129, 0.05); }
        .order-card.expired { border-left: 4px solid var(--danger); opacity: 0.6; }
        
        .order-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
        .order-phone { font-size: 18px; font-weight: 700; color: var(--text); letter-spacing: 0.5px; }
        .order-badge { 
            font-size: 12px; padding: 4px 10px; border-radius: 20px; font-weight: 600; 
            background: rgba(255,255,255,0.1); display: flex; align-items: center; gap: 5px;
        }
        
        .order-info { display: flex; gap: 15px; font-size: 13px; color: var(--text-muted); margin-bottom: 15px; flex-wrap: wrap;}
        .order-info span { display: flex; align-items: center; gap: 5px; }
        
        .otp-box {
            background: rgba(15, 23, 42, 0.8); padding: 12px; border-radius: 10px;
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 12px; border: 1px dashed rgba(16, 185, 129, 0.5);
        }
        .otp-code { font-size: 22px; font-weight: 700; color: var(--success); letter-spacing: 3px; font-family: monospace;}
        
        .action-row { display: flex; gap: 10px; margin-top: 10px; }
        .btn-small {
            flex: 1; padding: 10px; border-radius: 8px; font-size: 14px; font-weight: 600;
            display: flex; justify-content: center; align-items: center; gap: 5px; color: #fff;
        }
        .btn-small.copy { background: rgba(255,255,255,0.1); }
        .btn-small.cancel { background: rgba(239, 68, 68, 0.2); color: var(--danger); }
        
        /* --- LIST ITEMS (COUNTRIES/SERVICES) --- */
        .list-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .list-btn {
            background: var(--surface); border: 1px solid var(--border);
            padding: 14px; border-radius: 12px; text-align: left;
            color: var(--text); font-size: 14px; display: flex; flex-direction: column; gap: 6px;
            transition: 0.2s;
        }
        .list-btn:hover { background: var(--surface-hover); border-color: var(--primary); }
        .list-btn .name { font-weight: 600; display: flex; align-items: center; gap: 8px; font-size: 15px;}
        .list-btn .count { font-size: 12px; color: var(--text-muted); text-align: right; }

        /* --- PAGINATION --- */
        .pagination { display: flex; justify-content: space-between; align-items: center; margin-top: 20px; background: var(--surface); padding: 10px; border-radius: 12px; border: 1px solid var(--border); }
        .pagination button { flex: 1; padding: 10px; border-radius: 8px; background: rgba(255,255,255,0.1); color: var(--text); font-weight: 600; border: none; font-size: 14px; }
        .pagination button:disabled { opacity: 0.3; cursor: not-allowed; }
        .pagination span { flex: 1; text-align: center; font-size: 14px; color: var(--text-muted); font-weight: 500; }

        /* --- BOTTOM NAV --- */
        .bottom-nav {
            position: fixed; bottom: 0; left: 0; width: 100%; height: 70px;
            background: rgba(15, 23, 42, 0.9); backdrop-filter: var(--glass-blur);
            display: flex; justify-content: space-around; align-items: center; 
            border-top: 1px solid var(--border); z-index: 100;
        }
        .nav-item {
            display: flex; flex-direction: column; align-items: center;
            color: var(--text-muted); font-size: 11px; gap: 4px; background: none;
            transition: 0.2s; width: 25%; font-weight: 500;
        }
        .nav-item .icon { font-size: 24px; transition: 0.2s; }
        .nav-item.active { color: var(--primary); }
        .nav-item.active .icon { transform: translateY(-3px); }

        .loading { text-align: center; padding: 30px; color: var(--text-muted); }
        .spinner { border: 3px solid rgba(255,255,255,0.1); border-top-color: var(--primary); border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 0 auto 15px; }
        @keyframes spin { to { transform: rotate(360deg); } }
        
        #toast {
            position: fixed; bottom: 90px; left: 50%; transform: translateX(-50%) translateY(20px);
            background: var(--surface); backdrop-filter: var(--glass-blur);
            color: white; padding: 12px 24px; border-radius: 30px; font-weight: 500;
            border: 1px solid var(--border); box-shadow: var(--shadow);
            opacity: 0; transition: 0.3s; z-index: 2000; pointer-events: none;
        }
        #toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
    </style>
</head>
<body>
    <div id="toast">Copied!</div>

    <!-- CUSTOM CONFIRM MODAL -->
    <div id="custom-modal">
        <div class="modal-content">
            <div class="modal-title" id="modal-title">Xác nhận</div>
            <div class="modal-msg" id="modal-msg">Bạn có chắc chắn muốn thực hiện hành động này?</div>
            <div class="modal-actions">
                <button class="btn-outline" id="modal-btn-cancel">Hủy bỏ</button>
                <button class="btn-primary" id="modal-btn-confirm">Đồng ý</button>
            </div>
        </div>
    </div>

    <!-- Sidebar -->
    <div class="overlay" id="overlay" onclick="toggleSidebar()"></div>
    <div class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <h2>FAST IVAS</h2>
            <div class="sidebar-user" id="side-user-info">Loading...</div>
        </div>
        <div class="sidebar-menu">
            <a href="#" class="menu-item active" onclick="navTo('home')"><span class="icon">🏠</span> Trang chủ</a>
            <a href="#" class="menu-item" onclick="navTo('buy')"><span class="icon">🛒</span> Mua Số OTP</a>
            <a href="#" class="menu-item" onclick="navTo('history')"><span class="icon">📜</span> Lịch sử</a>
            <a href="#" class="menu-item" onclick="navTo('wallet')"><span class="icon">💵</span> Ví & Rút Tiền</a>
            <a href="#" class="menu-item" onclick="navTo('leaderboard')"><span class="icon">🏆</span> Bảng Xếp Hạng</a>
            <a href="#" class="menu-item" onclick="navTo('profile')"><span class="icon">👤</span> Hồ Sơ</a>
            
            <a href="#" class="menu-item menu-admin" id="menu-admin" onclick="navTo('admin')" style="display: none;">
                <span class="icon">🛡</span> ADMIN PANEL
            </a>
        </div>
    </div>

    <!-- Top Bar -->
    <div class="top-bar">
        <button class="menu-btn" onclick="toggleSidebar()">☰</button>
        <div class="page-title" id="top-title">Trang chủ</div>
    </div>

    <!-- Main Content -->
    <div class="container">
        
        <!-- VIEW: HOME -->
        <div id="view-home" class="view active">
            <div class="card balance-card">
                <div class="balance-title">Số dư khả dụng</div>
                <div class="balance-amount" id="home-balance">$0.000</div>
            </div>
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="label">OTP Hôm Nay</div>
                    <div class="value" id="home-today-otps">0</div>
                </div>
                <div class="stat-box">
                    <div class="label">Tổng Đơn</div>
                    <div class="value" id="home-total-orders">0</div>
                </div>
            </div>

            <h3 style="margin-bottom: 15px; font-size: 18px; font-weight: 600;">⏳ Đơn Đang Chờ</h3>
            <div id="active-orders-list">
                <div class="loading"><div class="spinner"></div>Đang tải...</div>
            </div>
        </div>

        <!-- VIEW: BUY -->
        <div id="view-buy" class="view">
            <div class="card">
                <div class="form-group">
                    <label class="form-label">Chọn Nguồn Số</label>
                    <select class="form-control" id="provider-select" onchange="renderBuyOptions()">
                        <option value="MK">🎱 Numbers 1 (MK)</option>
                        <option value="NP">📱 Numbers 2 (NP)</option>
                        <option value="BASHA">🔢 Numbers BS (Basha)</option>
                        <option value="SLVN">🌐 Numbers 4 (SLVN)</option>
                    </select>
                </div>
            </div>
            <div id="buy-list-container" class="list-grid">
                <!-- Rendered by JS -->
            </div>
        </div>

        <!-- VIEW: HISTORY -->
        <div id="view-history" class="view">
            <div id="history-list">
                <div class="loading"><div class="spinner"></div>Đang tải...</div>
            </div>
            
            <div class="pagination" id="history-pagination" style="display: none;">
                <button id="btn-prev" onclick="changeHistoryPage(-1)">← Trang trước</button>
                <span id="page-info">Trang 1 / 1</span>
                <button id="btn-next" onclick="changeHistoryPage(1)">Trang sau →</button>
            </div>
        </div>

        <!-- VIEW: WALLET -->
        <div id="view-wallet" class="view">
            <div class="card">
                <div class="form-label" style="font-size: 16px; color: var(--text); margin-bottom: 15px;">💵 Ví TON</div>
                <div class="form-group">
                    <input type="text" class="form-control" id="ton-address" placeholder="UQ... hoặc EQ...">
                </div>
                <button class="btn btn-primary" onclick="saveWallet()">Lưu Địa Chỉ</button>
            </div>
            <div class="card">
                <div class="form-label" style="font-size: 16px; color: var(--text); margin-bottom: 15px;">💰 Rút Tiền</div>
                
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 12px;">
                    <button class="btn-small copy" onclick="setWithdrawAmount(1)">$1</button>
                    <button class="btn-small copy" onclick="setWithdrawAmount(2)">$2</button>
                    <button class="btn-small copy" onclick="setWithdrawAmount(5)">$5</button>
                    <button class="btn-small copy" onclick="setWithdrawAmount(8)">$8</button>
                </div>
                <button class="btn-small copy" style="width: 100%; margin-bottom: 15px; background: rgba(59, 130, 246, 0.15); border-color: rgba(59, 130, 246, 0.4); color: #93c5fd;" onclick="setWithdrawAmount('max')">
                    ⚡ Rút Toàn Bộ (Phí $0.1)
                </button>

                <div class="form-group">
                    <input type="number" class="form-control" id="withdraw-amount" placeholder="Nhập số tiền ($)" step="0.1">
                </div>
                <button class="btn btn-success" onclick="requestWithdraw()">Gửi Yêu Cầu</button>
            </div>
            <div class="card">
                <div class="form-label" style="font-size: 16px; color: var(--text); margin-bottom: 15px;">💌 Mời Bạn Bè</div>
                <div style="background: rgba(15,23,42,0.6); padding: 12px; border-radius: 8px; word-break: break-all; font-size: 13px; margin-bottom: 10px; border: 1px solid var(--border);" id="ref-link"></div>
                <button class="btn btn-outline" onclick="copyRef()">📋 Sao Chép Link</button>
            </div>
        </div>

        <!-- VIEW: LEADERBOARD -->
        <div id="view-leaderboard" class="view">
            <div class="card">
                <div class="form-label" style="font-size: 16px; color: var(--text); margin-bottom: 15px;">🏆 TOP 10 CAO THỦ</div>
                <div id="leaderboard-list">
                    <div class="loading"><div class="spinner"></div>Đang tải...</div>
                </div>
            </div>
        </div>

        <!-- VIEW: PROFILE -->
        <div id="view-profile" class="view">
            <div class="card">
                <div class="form-label" style="font-size: 16px; color: var(--text); margin-bottom: 15px;">👤 HỒ SƠ CỦA BẠN</div>
                <div id="profile-info" style="font-size: 15px; line-height: 2;">
                    <!-- Rendered by JS -->
                </div>
            </div>
        </div>

        <!-- VIEW: ADMIN -->
        <div id="view-admin" class="view">
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="label">Users</div>
                    <div class="value" id="admin-total-users">0</div>
                </div>
                <div class="stat-box">
                    <div class="label">Orders</div>
                    <div class="value" id="admin-total-orders">0</div>
                </div>
            </div>
            
            <div class="card">
                <div class="form-label" style="font-size: 16px; color: var(--text); margin-bottom: 15px;">💸 Duyệt Rút Tiền</div>
                <div id="admin-wd-list" style="margin-top: 15px;"></div>
            </div>

            <div class="card">
                <div class="form-label" style="font-size: 16px; color: var(--text); margin-bottom: 15px;">➕ Thêm Số BS</div>
                <div class="form-group">
                    <textarea class="form-control" id="bs-input" rows="4" placeholder="Mỗi dòng 1 số..."></textarea>
                </div>
                <button class="btn btn-success" onclick="addBsNumbers()">Thêm Số</button>
            </div>
        </div>

    </div>

    <!-- Bottom Nav -->
    <div class="bottom-nav">
        <button class="nav-item active" id="nav-home" onclick="navTo('home')"><span class="icon">🏠</span>Trang chủ</button>
        <button class="nav-item" id="nav-buy" onclick="navTo('buy')"><span class="icon">🛒</span>Mua số</button>
        <button class="nav-item" id="nav-history" onclick="navTo('history')"><span class="icon">📜</span>Lịch sử</button>
        <button class="nav-item" id="nav-wallet" onclick="navTo('wallet')"><span class="icon">💵</span>Ví</button>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();
        tg.setHeaderColor('#0B1120');
        tg.setBackgroundColor('#0B1120');

        let userData = null;
        let autoRefreshInterval = null;
        let currentHistoryPage = 1;
        let totalHistoryPages = 1;

        function showCustomModal(title, msg) {
            return new Promise((resolve) => {
                document.getElementById('modal-title').innerText = title;
                document.getElementById('modal-msg').innerText = msg;
                document.getElementById('custom-modal').classList.add('open');

                const btnConfirm = document.getElementById('modal-btn-confirm');
                const btnCancel = document.getElementById('modal-btn-cancel');

                const handleConfirm = () => { cleanup(); resolve(true); };
                const handleCancel = () => { cleanup(); resolve(false); };
                const cleanup = () => {
                    document.getElementById('custom-modal').classList.remove('open');
                    btnConfirm.removeEventListener('click', handleConfirm);
                    btnCancel.removeEventListener('click', handleCancel);
                };

                btnConfirm.addEventListener('click', handleConfirm);
                btnCancel.addEventListener('click', handleCancel);
            });
        }

        function showToast(msg) {
            const toast = document.getElementById('toast');
            toast.innerText = msg;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 2000);
        }

        async function api(path, method = 'GET', body = null) {
            const opts = {
                method,
                headers: { 'X-Telegram-Init-Data': tg.initData, 'Content-Type': 'application/json' }
            };
            if (body) opts.body = JSON.stringify(body);
            try {
                const res = await fetch(path, opts);
                return await res.json();
            } catch (e) {
                return { error: 'Lỗi kết nối máy chủ!' };
            }
        }

        function toggleSidebar() {
            document.getElementById('sidebar').classList.toggle('open');
            document.getElementById('overlay').classList.toggle('open');
        }

        function navTo(viewId) {
            document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(v => v.classList.remove('active'));
            document.querySelectorAll('.menu-item').forEach(v => v.classList.remove('active'));

            document.getElementById('view-' + viewId).classList.add('active');
            
            const navBtn = document.getElementById('nav-' + viewId);
            if (navBtn) navBtn.classList.add('active');

            const titles = { home: 'Trang chủ', buy: 'Mua Số OTP', history: 'Lịch Sử', wallet: 'Ví & Rút Tiền', leaderboard: 'Bảng Xếp Hạng', profile: 'Hồ Sơ', admin: 'Admin Panel' };
            document.getElementById('top-title').innerText = titles[viewId];

            if (document.getElementById('sidebar').classList.contains('open')) toggleSidebar();

            if (viewId === 'home') loadHome();
            if (viewId === 'buy') renderBuyOptions();
            if (viewId === 'history') loadHistory(1);
            if (viewId === 'wallet') loadWallet();
            if (viewId === 'leaderboard') loadLeaderboard();
            if (viewId === 'profile') loadProfile();
            if (viewId === 'admin') loadAdmin();
        }

        async function loadUserData() {
            const data = await api('/api/mini/me');
            if (data.error) return showToast(data.error);
            
            userData = data;
            document.getElementById('home-balance').innerText = '$' + (data.user.usd_milli / 1000).toFixed(3);
            document.getElementById('home-today-otps').innerText = data.today_otps;
            document.getElementById('home-total-orders').innerText = data.total_orders;
            document.getElementById('side-user-info').innerText = 'ID: ' + data.user.id + ' | ' + data.user.first_name;
            document.getElementById('ton-address').value = data.user.wallet_ton || '';
            document.getElementById('ref-link').innerText = data.referral_link;
            
            if (data.is_admin) {
                document.getElementById('menu-admin').style.display = 'flex';
            } else {
                document.getElementById('menu-admin').style.display = 'none';
            }
        }

        async function loadHome() {
            loadUserData();
            const listDiv = document.getElementById('active-orders-list');
            
            const data = await api('/api/mini/orders/active');
            if (!data.orders) return;
            
            if (data.orders.length === 0) {
                listDiv.innerHTML = '<div class="loading" style="background: var(--surface); border-radius: 16px; border: 1px dashed var(--border);">Không có đơn nào đang chờ.</div>';
                return;
            }

            listDiv.innerHTML = data.orders.map(o => renderOrderCard(o, false)).join('');
        }

        async function loadHistory(page = 1) {
            currentHistoryPage = page;
            const listDiv = document.getElementById('history-list');
            const pagDiv = document.getElementById('history-pagination');
            
            listDiv.innerHTML = '<div class="loading"><div class="spinner"></div>Đang tải...</div>';
            
            const data = await api('/api/mini/orders?page=' + page);
            
            if (!data.orders || data.orders.length === 0) {
                listDiv.innerHTML = '<div class="loading">Chưa có lịch sử giao dịch.</div>';
                pagDiv.style.display = 'none';
                return;
            }

            listDiv.innerHTML = data.orders.map(o => renderOrderCard(o, true)).join('');
            
            totalHistoryPages = data.total_pages || 1;
            currentHistoryPage = data.current_page || 1;
            
            if (totalHistoryPages > 1) {
                pagDiv.style.display = 'flex';
                document.getElementById('page-info').innerText = `Trang ${currentHistoryPage} / ${totalHistoryPages}`;
                document.getElementById('btn-prev').disabled = currentHistoryPage <= 1;
                document.getElementById('btn-next').disabled = currentHistoryPage >= totalHistoryPages;
            } else {
                pagDiv.style.display = 'none';
            }
        }

        function changeHistoryPage(delta) {
            const newPage = currentHistoryPage + delta;
            if (newPage >= 1 && newPage <= totalHistoryPages) {
                loadHistory(newPage);
            }
        }

        function renderOrderCard(o, isHistory) {
            const statusColors = {
                'PENDING': 'var(--warning)',
                'COMPLETED': 'var(--success)',
                'EXPIRED': 'var(--danger)',
                'CANCELLED': 'var(--danger)'
            };
            const statusTexts = {
                'PENDING': '⏳ Chờ OTP',
                'COMPLETED': '✅ Đã nhận',
                'EXPIRED': '⌛ Hết hạn',
                'CANCELLED': '🚫 Đã hủy'
            };
            
            const color = statusColors[o.status] || 'var(--text-muted)';
            const text = statusTexts[o.status] || o.status;
            
            let dateStr = o.created_at ? new Date(o.created_at).toLocaleString('vi-VN') : '';
            
            let otpHtml = '';
            if (o.status === 'COMPLETED' && o.otp) {
                otpHtml = `
                    <div class="otp-box">
                        <div>
                            <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 4px;">Mã OTP:</div>
                            <div class="otp-code">${o.otp}</div>
                        </div>
                        <button class="btn-small copy" style="background: var(--success); width: 80px;" onclick="copyText('${o.otp}')">📋 Copy</button>
                    </div>
                `;
            }

            return `
                <div class="order-card ${o.status.toLowerCase()}">
                    <div class="order-header">
                        <div class="order-phone">${o.phone}</div>
                        <div class="order-badge" style="color: ${color};">${text}</div>
                    </div>
                    <div class="order-info">
                        <span>${o.flag} ${o.country}</span>
                        <span>🔧 ${o.provider}</span>
                        ${o.platform ? `<span>🌐 ${o.platform}</span>` : ''}
                        <span>🕒 ${dateStr}</span>
                    </div>
                    
                    ${otpHtml}
                    
                    <div class="action-row">
                        <button class="btn-small copy" onclick="copyText('${o.phone}')">📋 Copy Số</button>
                        ${o.status === 'PENDING' && !isHistory ? `<button class="btn-small cancel" onclick="cancelOrder(${o.id})">❌ Hủy</button>` : ''}
                    </div>
                </div>
            `;
        }

        function copyText(text) {
            navigator.clipboard.writeText(text).then(() => {
                showToast('Đã sao chép: ' + text);
            });
        }

        async function cancelOrder(oid) {
            const confirmed = await showCustomModal('Hủy Đơn', 'Bạn chắc chắn muốn hủy đơn này?');
            if (!confirmed) return;
            const res = await api('/api/mini/orders/' + oid + '/cancel', 'POST');
            if (res.ok) { loadHome(); showToast('Đã hủy đơn'); }
            else { tg.showAlert('Lỗi: ' + res.error); }
        }

        async function renderBuyOptions() {
            const provider = document.getElementById('provider-select').value;
            const container = document.getElementById('buy-list-container');
            container.innerHTML = '<div class="loading" style="grid-column: 1/-1;"><div class="spinner"></div>Đang tải...</div>';

            if (provider === 'MK') {
                const data = await api('/api/mini/mk/ranges');
                container.innerHTML = data.countries.map(c => `
                    <button class="list-btn" onclick="buyNumber('MK', '${c.range}', '${c.name}')">
                        <div class="name">${c.flag} ${c.name}</div>
                    </button>
                `).join('');
            } 
            else if (provider === 'NP') {
                const data = await api('/api/mini/np/services');
                container.innerHTML = data.services.map(s => `
                    <button class="list-btn" onclick="loadNpCountries('${s.key}')">
                        <div class="name">🔧 ${s.name}</div>
                        <div class="count">Còn ${s.count} số</div>
                    </button>
                `).join('');
            }
            else if (provider === 'BASHA') {
                const data = await api('/api/mini/bs/countries');
                if (data.countries.length === 0) container.innerHTML = '<div class="loading" style="grid-column: 1/-1;">Chưa có số BS.</div>';
                else container.innerHTML = data.countries.map(c => `
                    <button class="list-btn" onclick="buyNumber('BASHA', '${c.name}', '${c.name}')">
                        <div class="name">${c.flag} ${c.name}</div>
                        <div class="count">Còn ${c.count} số</div>
                    </button>
                `).join('');
            }
            else if (provider === 'SLVN') {
                const data = await api('/api/mini/slvn/countries');
                if (!data.countries || data.countries.length === 0) container.innerHTML = '<div class="loading" style="grid-column: 1/-1;">Chưa có số (Hoặc lỗi API Key).</div>';
                else container.innerHTML = data.countries.map(c => `
                    <button class="list-btn" onclick="buyNumber('SLVN', '${c.code}', '${c.name}', '${c.tag}')">
                        <div class="name">${c.flag} ${c.name}</div>
                        <div class="count">Rate: $${c.rate}</div>
                    </button>
                `).join('');
            }
        }

        async function loadNpCountries(service) {
            const container = document.getElementById('buy-list-container');
            container.innerHTML = '<div class="loading" style="grid-column: 1/-1;"><div class="spinner"></div>Đang tải...</div>';
            const data = await api('/api/mini/np/countries/' + service);
            container.innerHTML = data.countries.map(c => `
                <button class="list-btn" onclick="buyNumber('NP', '${c.code}', '${c.name}', '${service}')">
                    <div class="name">🌍 ${c.name}</div>
                    <div class="count">Còn ${c.count} số</div>
                </button>
            `).join('');
        }

        async function buyNumber(provider, code, name, param3 = null) {
            const confirmed = await showCustomModal('Xác Nhận', `Bạn có chắc muốn lấy số ${name} không?`);
            if (!confirmed) return;

            tg.showLoading();
            let body = { provider };
            if (provider === 'MK') { body.range = code; body.country_name = name; }
            if (provider === 'NP') { body.country = code; body.service = param3; }
            if (provider === 'BASHA') { body.country = code; }
            if (provider === 'SLVN') { body.country_code = code; body.tag = param3; }

            try {
                const res = await api('/api/mini/orders', 'POST', body);
                tg.hideLoading();
                if (res.ok) {
                    showToast('✅ Đã lấy số thành công!');
                    navTo('home');
                } else {
                    tg.showAlert('❌ Lỗi: ' + (res.error || 'Không thể lấy số'));
                }
            } catch (err) {
                tg.hideLoading();
                tg.showAlert('❌ Lỗi kết nối máy chủ!');
            }
        }

        function loadWallet() { loadUserData(); }

        async function loadLeaderboard() {
            const listDiv = document.getElementById('leaderboard-list');
            const data = await api('/api/mini/leaderboard');
            if (!data.leaderboard || data.leaderboard.length === 0) {
                listDiv.innerHTML = '<div class="loading">Chưa có dữ liệu.</div>';
                return;
            }
            
            listDiv.innerHTML = data.leaderboard.map((u, i) => {
                let medal = i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : '🔹';
                return `
                    <div style="display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid var(--border);">
                        <span>${medal} ${u.name}</span>
                        <strong style="color: var(--success);">$${(u.balance/1000).toFixed(3)}</strong>
                    </div>
                `;
            }).join('');
        }

        function loadProfile() {
            if (!userData || !userData.user) return;
            const u = userData.user;
            document.getElementById('profile-info').innerHTML = `
                <div style="padding: 10px 0; border-bottom: 1px solid var(--border);">🆔 Telegram ID: <b>${u.id}</b></div>
                <div style="padding: 10px 0; border-bottom: 1px solid var(--border);">👤 Tên: <b>${u.first_name}</b></div>
                <div style="padding: 10px 0; border-bottom: 1px solid var(--border);">💰 Số dư: <b style="color: var(--success);">$${(u.usd_milli/1000).toFixed(3)}</b></div>
                <div style="padding: 10px 0;">📅 Ngày tham gia: <b>${new Date(u.joined_at).toLocaleDateString('vi-VN')}</b></div>
            `;
        }

        function setWithdrawAmount(type) {
            const input = document.getElementById('withdraw-amount');
            if (type === 'max') {
                if (!userData || !userData.user) return;
                const maxAmount = (userData.user.usd_milli / 1000).toFixed(3);
                let finalAmt = parseFloat(maxAmount) - 0.1;
                if (finalAmt < 0) finalAmt = 0;
                input.value = finalAmt.toFixed(3);
                showToast('Đã trừ phí rút toàn bộ $0.1');
            } else {
                input.value = type;
            }
        }

        async function saveWallet() {
            const address = document.getElementById('ton-address').value;
            const res = await api('/api/mini/wallet/address', 'POST', { address });
            if (res.ok) showToast('Đã lưu địa chỉ ví!');
            else tg.showAlert('Lỗi: ' + res.error);
        }

        async function requestWithdraw() {
            const amount = document.getElementById('withdraw-amount').value;
            if (!amount || amount < 1) return tg.showAlert('Số tiền tối thiểu là $1.00');
            const res = await api('/api/mini/wallet/withdraw', 'POST', { amount });
            if (res.ok) {
                tg.showAlert('Đã gửi yêu cầu rút tiền. Vui lòng chờ Admin duyệt.');
                loadUserData();
            } else {
                tg.showAlert('Lỗi: ' + res.error);
            }
        }

        function copyRef() {
            const text = document.getElementById('ref-link').innerText;
            navigator.clipboard.writeText(text).then(() => showToast('Đã sao chép link!'));
        }

        async function loadAdmin() {
            const data = await api('/api/mini/admin/data');
            if (data.error) return tg.showAlert(data.error);
            
            document.getElementById('admin-total-users').innerText = data.stats.users;
            document.getElementById('admin-total-orders').innerText = data.stats.orders;

            const wdDiv = document.getElementById('admin-wd-list');
            if (!data.withdrawals || data.withdrawals.length === 0) {
                wdDiv.innerHTML = '<div style="color: var(--text-muted); font-size: 14px;">Không có yêu cầu rút tiền.</div>';
            } else {
                wdDiv.innerHTML = data.withdrawals.map(w => `
                    <div class="order-card" style="border-left-color: var(--primary);">
                        <div class="order-header">
                            <div class="order-phone">${w.name} (${w.user_id})</div>
                            <div class="order-badge" style="color: var(--primary);">$${(w.amount/1000).toFixed(3)}</div>
                        </div>
                        <div style="font-size: 13px; color: var(--text-muted); word-break: break-all; margin-bottom: 12px;">Ví: ${w.wallet}</div>
                        <div class="action-row">
                            <button class="btn-small" style="background: var(--success);" onclick="adminWdAction(${w.id}, 'approve')">✅ Duyệt</button>
                            <button class="btn-small" style="background: var(--danger);" onclick="adminWdAction(${w.id}, 'reject')">❌ Từ chối</button>
                        </div>
                    </div>
                `).join('');
            }
        }

        async function adminWdAction(wid, action) {
            const confirmed = await showCustomModal('Xác Nhận', `Bạn chắc chắn muốn ${action === 'approve' ? 'DUYỆT' : 'TỪ CHỐI'} yêu cầu này?`);
            if (!confirmed) return;
            const res = await api('/api/mini/admin/withdraw/action', 'POST', { wid, action });
            if (res.ok) { loadAdmin(); showToast('Thành công!'); }
            else tg.showAlert(res.error);
        }

        async function addBsNumbers() {
            const numbers = document.getElementById('bs-input').value;
            if (!numbers) return tg.showAlert('Vui lòng nhập số!');
            const res = await api('/api/mini/admin/bs/add', 'POST', { numbers });
            if (res.ok) {
                tg.showAlert(`Đã thêm ${res.added} số`);
                document.getElementById('bs-input').value = '';
            } else tg.showAlert(res.error);
        }

        function startAutoRefresh() {
            if (autoRefreshInterval) clearInterval(autoRefreshInterval);
            autoRefreshInterval = setInterval(() => {
                const activeView = document.querySelector('.view.active').id;
                if (activeView === 'view-home') {
                    loadHome();
                }
            }, 5000); 
        }

        tg.ready();
        tg.expand();
        loadUserData();
        loadHome();
        startAutoRefresh();

    </script>
</body>
</html>
"""

async def web_server():
    app = web.Application(middlewares=[mini_auth_middleware], client_max_size=1024 * 1024)
    
    async def serve_html(request):
        return web.Response(text=MINIAPP_HTML, content_type='text/html')
        
    async def health(request): return web.json_response({"ok": True})
        
    app.router.add_get('/', serve_html)
    app.router.add_get('/miniapp', serve_html)
    app.router.add_get('/health', health)
    
    app.router.add_get('/api/mini/me', mini_me)
    app.router.add_get('/api/mini/leaderboard', mini_leaderboard)
    app.router.add_get('/api/mini/orders/active', mini_active_orders)
    app.router.add_get('/api/mini/orders', mini_history_orders)
    app.router.add_post('/api/mini/orders', mini_create_order)
    app.router.add_post('/api/mini/orders/{oid}/cancel', mini_cancel_order)
    app.router.add_get('/api/mini/mk/ranges', mini_mk_ranges)
    app.router.add_get('/api/mini/np/services', mini_np_services)
    app.router.add_get('/api/mini/np/countries/{service}', mini_np_countries)
    app.router.add_get('/api/mini/bs/countries', mini_bs_countries)
    app.router.add_get('/api/mini/slvn/countries', mini_slvn_countries)
    
    app.router.add_post('/api/mini/wallet/address', mini_save_wallet)
    app.router.add_post('/api/mini/wallet/withdraw', mini_withdraw)
    
    app.router.add_get('/api/mini/admin/data', mini_admin_data)
    app.router.add_post('/api/mini/admin/withdraw/action', mini_admin_wd_action)
    app.router.add_post('/api/mini/admin/bs/add', mini_admin_bs_add)
    
    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app); await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port); await site.start()
    logger.info("FAST IVAS Mini App server started on port %s", port)

async def set_bot_commands():
    user_commands = [BotCommand(command="start", description="Open main menu")]
    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())
    admin_commands = user_commands + [BotCommand(command="admin", description="[Admin] Panel"), BotCommand(command="broadcast", description="[Admin] Broadcast"), BotCommand(command="addbal", description="[Admin] Add bal"), BotCommand(command="deductbal", description="[Admin] Deduct bal")]
    try: await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=ADMIN_ID))
    except Exception as e: logger.error(f"Error: {e}")

class MkOtpPoller:
    def __init__(self):
        self.interval = 10
        self._consecutive_errors = 0

    async def _process_otp(self, row, otp, sms):
        reward = REWARD_MILLI_PER_OTP
        if row.get("provider") in ["NP", "SLVN"]: reward = 0; platform = row.get("operator", "Other").capitalize()
        elif row.get("provider") == "BASHA": reward = 0; platform = "Basha Service"
        else: platform = detect_otp_platform(sms)
        
        db = open_db()
        try:
            db.execute("BEGIN IMMEDIATE")
            chk = db.execute("SELECT status FROM orders WHERE id=?", (row["id"],)).fetchone()
            if not chk or chk[0] != "PENDING": db.rollback(); return False
            db.execute("UPDATE orders SET status='COMPLETED', otp_code=?, full_sms=?, platform=?, reward_milli=?, updated_at=? WHERE id=?", (otp, sms, platform, reward, now_text(), row["id"])); db.commit()
        except Exception: db.rollback(); return False
        finally: db.close()
        
        if reward > 0:
            await change_usd(row["user_id"], reward, "OTP_REWARD", f"Reward OTP #{row['id']}")
            
        u = await get_user(row["user_id"])
        user_name = u["first_name"] if u else "User"
        flag = get_country_flag(row['country'])
        
        user_text = f"📱 <b>{platform}</b> 🌍 {row['country']}\n<b>OTP Received</b>\n👤 User: <a href='tg://user?id={row['user_id']}'>{user_name}</a>\n\n🔒 <b>OTP :</b> <code>{otp}</code>\n📞 <code>{row['phone']}</code>"
        await bot.send_message(row["user_id"], user_text)
        
        if OTP_GROUP_ID:
            group_text = f"📱 <b>{platform}</b> 🌍 {row['country']} {flag}\n<b>OTP Received</b>\n👤 User: <a href='tg://user?id={row['user_id']}'>{user_name}</a>\n\n🔒 <b>OTP :</b> <code>{otp}</code>\n📞 <code>{mask_phone(row['phone'])}</code>"
            if sms: group_text += f"\n<blockquote>💬 {safe(sms, 300)}</blockquote>"
            try: await bot.send_message(OTP_GROUP_ID, group_text)
            except: pass
        return True

    async def _poll_once(self):
        rows = await db_exec("SELECT * FROM orders WHERE status='PENDING' LIMIT 100", fetch="all")
        if not rows: return 0, 0, False
        checked = new_otp = 0
        
        for r in rows:
            if r["provider"] == "MK":
                checked += 1
                data, err = await api_request("POST", "check/status", {"request_ids": [int(r["request_id"])]})
                if not err and data:
                    inner = data.get("data", {})
                    res = inner.get("results", [])
                    if res and res[0].get("status") == "success":
                        if await self._process_otp(r, res[0]["otp_code"], res[0].get("full_sms", "")): new_otp += 1
            elif r["provider"] == "NP":
                checked += 1
                data, err = await api_request("GET", "latest_otp", params={"number": r["phone"]}, api_type="NP")
                if not err and data and data.get("has_otp"):
                    if await self._process_otp(r, data["otp_code"], f"OTP: {data['otp_code']}"): new_otp += 1
            elif r["provider"] == "BASHA":
                checked += 1
                data, err = await api_request("POST", "legacy/get-last-sms", {"number": r["phone"]}, api_type="BASHA")
                if not err and data and data.get("message"):
                    otp_match = re.search(r'\b(\d{4,8})\b', data["message"])
                    if otp_match and await self._process_otp(r, otp_match.group(1), data["message"]): new_otp += 1
            elif r["provider"] == "SLVN":
                checked += 1
                data, err = await api_request("GET", f"check-otp/{r['request_id']}", api_type="SLVN")
                if not err and data and data.get("status") == "success":
                    inner = data.get("data", {})
                    if inner.get("status") == "RECEIVED":
                        if await self._process_otp(r, inner.get("otpCode"), inner.get("fullSms", "")): new_otp += 1
        return checked, new_otp, False

    async def run_forever(self):
        while True:
            try:
                await self._poll_once()
            except Exception as e: logger.error(f"Poller error: {e}")
            await asyncio.sleep(10)

async def main():
    global BOT_USERNAME
    try: 
        me = await bot.get_me(); BOT_USERNAME = me.username; await set_bot_commands()
        if WEBAPP_URL.startswith("https://"):
            await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="FAST IVAS", web_app=WebAppInfo(url=WEBAPP_URL)))
    except Exception as e: logger.error(f"Error setting menu: {e}")
    
    await init_db()
    asyncio.create_task(web_server())
    
    poller = MkOtpPoller()
    asyncio.create_task(poller.run_forever())
    
    logger.info("FAST IVAS starting...")
    await dp.start_polling(bot, drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())