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
import base64
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
    ReplyKeyboardRemove, MenuButtonWebApp, WebAppInfo, BufferedInputFile
)
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

# =====================================================
# CẤU HÌNH HỆ THỐNG
# =====================================================
BOT_TOKEN      = os.getenv("BOT_TOKEN", "").strip()
WEBAPP_URL     = os.getenv("WEBAPP_URL", "").strip()
ADMIN_ID       = int(os.getenv("ADMIN_ID", "0") or 0)

OTP_GROUP_ID   = int(os.getenv("OTP_GROUP_ID", "-1004341368656"))
OTP_GROUP_URL  = "https://t.me/LIVEOTPIVAS"
MAIN_CHANNEL_URL = "https://t.me/FastNode_1"

MK_API_KEY     = os.getenv("MK_API_KEY", "badacaa33d287233567a49db").strip()
MK_API_BASE    = "https://mknetworkbd.com/api/v3/public"

NP_API_KEY     = os.getenv("NP_API_KEY", "np_live_lrRtdKcOeg-syi8UCpmaA_idYmBZY0zbpwl5P--gF-g").strip()
NP_API_BASE    = "https://numberpanel.tech/api"

BASHA_API_KEY  = os.getenv("BASHA_API_KEY", "").strip()
BASHA_API_BASE = "https://basha.cc/api"

SLVN_API_KEY   = os.getenv("SLVN_API_KEY", "").strip()
SLVN_API_BASE  = "https://slvirtualnumber.com/api/v1/developer"

TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL", "").strip()
TURSO_AUTH_TOKEN   = os.getenv("TURSO_AUTH_TOKEN", "").strip()
SQLITE_PATH        = os.getenv("SQLITE_PATH", "fast_ivas.db")
PORT               = int(os.getenv("PORT", "10000"))

ORDER_LIFETIME_MINUTES = 15
REWARD_MILLI_PER_OTP   = 20
MIN_WITHDRAW_MILLI     = 1000
MAX_WITHDRAW_MILLI     = 1000000
WITHDRAW_FEE_MILLI     = 100
HISTORY_PAGE_SIZE      = 10
MAX_HISTORY_PAGES      = 100
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

def get_network_icon(net):
    net = str(net).upper()
    return "📘" if "FACEBOOK" in net else "📸" if "INSTAGRAM" in net else "💬" if "WHATSAPP" in net else "✈️" if "TELEGRAM" in net else "📱" if "TIKTOK" in net else "🧵" if "THREADS" in net else "🇬" if "GOOGLE" in net else "🐦" if "TWITTER" in net or "X" in net else "🌐"

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

async def api_request(method: str, endpoint: str, payload: dict = None, params: dict = None, api_type: str = "MK") -> tuple:
    base_urls = {
        "MK":    MK_API_BASE,
        "NP":    NP_API_BASE,
        "BASHA": BASHA_API_BASE,
        "SLVN":  SLVN_API_BASE,
    }
    keys = {
        "MK":    MK_API_KEY,
        "NP":    NP_API_KEY,
        "BASHA": BASHA_API_KEY,
        "SLVN":  SLVN_API_KEY,
    }
    url = base_urls.get(api_type, "")
    key = keys.get(api_type, "")
    if not url or not key:
        return None, f"API key cho {api_type} chưa được cấu hình."
    
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if str(api_type).upper() == "MK":
        headers["mknetwork-key"] = key
    else:
        headers["Authorization"] = f"Bearer {key}"
        
    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method, url + "/" + endpoint.lstrip("/"),
                json=payload, params=params, headers=headers,
                timeout=aiohttp.ClientTimeout(total=25)
            ) as resp:
                text = await resp.text()
                if resp.status in (401, 403):
                    return None, f"Lỗi xác thực API ({resp.status})."
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    return None, f"Phản hồi không phải JSON (HTTP {resp.status})."
                meta = data.get("meta", {})
                if meta.get("code") and meta.get("code") != 200:
                    return None, data.get("message") or meta.get("status") or "Lỗi API."
                return data, None
    except asyncio.TimeoutError:
        return None, "Timeout – API không phản hồi sau 25s."
    except Exception as e:
        return None, f"Lỗi mạng: {str(e)}"

@dp.message(CommandStart())
async def cmd_start(message: Message):
    try: await message.delete()
    except: pass
    args = message.text.split(maxsplit=1)
    ref = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    await register_user(message.from_user, ref)
    
    if await get_setting("maintenance", "off") == "on" and not is_admin(message.from_user.id):
        return await message.answer("🛠 <b>HỆ THỐNG ĐANG BẢO TRÌ</b>\n\nVui lòng quay lại sau.")
    
    webapp_link = WEBAPP_URL
    if webapp_link.startswith("https://"):
        webapp_link += ("&" if "?" in webapp_link else "?") + "v=7" # Tăng version để phá cache
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚡ MỞ ỨNG DỤNG FAST IVAS", web_app=WebAppInfo(url=webapp_link))]])
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
    
    if await get_setting("maintenance", "off") == "on" and not is_admin(message.from_user.id):
        return await message.answer("🛠 <b>HỆ THỐNG ĐANG BẢO TRÌ</b>\n\nVui lòng quay lại sau.")
        
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
        if not tg_user:
            return web.json_response({"error": "Invalid session", "orders": []}, status=401)
        request["tg_user"] = tg_user
        try:
            await register_user(SimpleNamespace(id=int(tg_user["id"]), username=tg_user.get("username"), first_name=tg_user.get("first_name") or "User"))
        except:
            pass
    return await handler(request)

def mini_uid(request): return int(request["tg_user"]["id"])
def mini_admin_guard(request): return is_admin(mini_uid(request))

# ==================== CÁC API ĐÃ ĐƯỢC BỌC THÉP AN TOÀN ====================

async def mini_me(request):
    """API lấy thông tin user. Luôn trả về 200 OK, không bao giờ sập 500."""
    try:
        uid = mini_uid(request)
        u = await get_user(uid)
        
        if not u:
            return web.json_response({
                "user": {"id": uid, "first_name": "User", "usd_milli": 0, "wallet_ton": "", "joined_at": now_text(), "language": "vi"},
                "total_orders": 0, "today_otps": 0, "total_otps": 0, "is_admin": False,
                "referral_link": f"https://t.me/{BOT_USERNAME}?start={uid}",
                "maintenance": "off", "maint_message": "", "maint_image": ""
            }, status=200)

        total = await db_exec("SELECT COUNT(*) as c FROM orders WHERE user_id=?", (uid,), fetch="one")
        today = await db_exec("SELECT COUNT(*) as c FROM orders WHERE user_id=? AND status='COMPLETED' AND created_at >= ?", (uid, now().strftime("%Y-%m-%d")), fetch="one")
        total_otps = await db_exec("SELECT COUNT(*) as c FROM orders WHERE user_id=? AND status='COMPLETED'", (uid,), fetch="one")
        
        return web.json_response({
            "user": {
                "id": u['user_id'], "first_name": u['first_name'], "usd_milli": u['usd_milli'], 
                "wallet_ton": u['wallet_ton'] or "", "joined_at": u['joined_at'], "language": u.get('language', 'vi')
            }, 
            "total_orders": total["c"] if total else 0, 
            "today_otps": today["c"] if today else 0,
            "total_otps": total_otps["c"] if total_otps else 0,
            "is_admin": is_admin(uid), 
            "referral_link": f"https://t.me/{BOT_USERNAME}?start={uid}",
            "maintenance": await get_setting("maintenance", "off"),
            "maint_message": await get_setting("maint_message", ""),
            "maint_image": await get_setting("maint_image", "")
        }, status=200)
    except Exception as e:
        logger.error(f"mini_me error: {e}")
        return web.json_response({
            "user": {"id": 0, "first_name": "Error", "usd_milli": 0, "wallet_ton": "", "joined_at": "", "language": "vi"},
            "total_orders": 0, "today_otps": 0, "total_otps": 0, "is_admin": False,
            "referral_link": "", "maintenance": "off", "maint_message": "", "maint_image": ""
        }, status=200)

async def mini_get_orders(request: web.Request) -> web.Response:
    """API lấy danh sách đơn. Bọc 3 lớp try/except, mọi lỗi trả về {'orders': []}."""
    columns = ("id", "request_id", "provider", "phone", "country", "status", "otp_code", "full_sms", "created_at", "expires_at")
    try:
        try:
            uid = mini_uid(request)
        except Exception:
            return web.json_response({"orders": []}, status=200)

        if uid is None:
            return web.json_response({"orders": []}, status=200)

        try:
            rows = await asyncio.wait_for(
                db_exec(
                    "SELECT id, request_id, provider, phone, country, status, otp_code, full_sms, created_at, expires_at FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 20",
                    (uid,), fetch="all",
                ),
                timeout=5.0
            )
        except Exception:
            rows = []

        orders = []
        try:
            for row in (rows or []):
                if row is None: continue
                if isinstance(row, dict):
                    item = row
                elif hasattr(row, "keys"):
                    try: item = {key: row[key] for key in row.keys()}
                    except Exception: item = dict(zip(columns, tuple(row)))
                else:
                    item = dict(zip(columns, row))
                
                orders.append({
                    "id": item.get("id"),
                    "request_id": item.get("request_id"),
                    "provider": item.get("provider") or "Unknown",
                    "phone": item.get("phone") or "",
                    "country": item.get("country") or "Unknown",
                    "status": item.get("status") or "PENDING",
                    "otp_code": item.get("otp_code") or "",
                    "full_sms": item.get("full_sms") or "",
                    "created_at": item.get("created_at") or "",
                    "expires_at": item.get("expires_at") or "",
                })
        except Exception:
            orders = []

        return web.json_response({"orders": orders}, status=200)

    except Exception:
        logger.exception("mini_get_orders: catastrophic failure")
        return web.json_response({"orders": []}, status=200)

# ==================== CÁC API KHÁC (GIỮ NGUYÊN LOGIC) ====================

async def mini_language_update(request):
    uid = mini_uid(request)
    body = await request.json()
    lang = body.get("language", "vi")
    await db_exec("UPDATE users SET language=? WHERE user_id=?", (lang, uid))
    return web.json_response({"ok": True})

async def mini_stats(request):
    try:
        today_str = now().strftime("%Y-%m-%d")
        total_otps = await db_exec("SELECT COUNT(*) FROM orders WHERE status='COMPLETED' AND created_at >= ?", (today_str,), fetch='one')
        countries = await db_exec("SELECT country, COUNT(id) FROM orders WHERE status='COMPLETED' AND created_at >= ? GROUP BY country ORDER BY COUNT(id) DESC", (today_str,), fetch='all')
        platforms = await db_exec("SELECT COALESCE(NULLIF(platform, ''), 'Other') as p, COUNT(id) FROM orders WHERE status='COMPLETED' AND created_at >= ? GROUP BY p ORDER BY COUNT(id) DESC", (today_str,), fetch='all')

        return web.json_response({
            "total_otps": total_otps[0] if total_otps else 0,
            "countries": [{"country": r[0], "count": r[1], "flag": get_country_flag(r[0])} for r in (countries or [])],
            "platforms": [{"platform": r[0], "count": r[1], "icon": get_network_icon(r[0])} for r in (platforms or [])]
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def mini_leaderboard(request):
    top_users = await db_exec("""
        SELECT u.user_id, u.first_name, u.usd_milli, 
        (SELECT COUNT(*) FROM orders WHERE user_id = u.user_id AND status = 'COMPLETED') as total_otps 
        FROM users u ORDER BY u.usd_milli DESC LIMIT 10
    """, fetch="all")
    return web.json_response({
        "leaderboard": [{"name": u["first_name"], "balance": u["usd_milli"], "total_otps": u["total_otps"]} for u in top_users] if top_users else []
    })

async def mini_active_orders(request):
    uid = mini_uid(request)
    rows = await db_exec("SELECT id, provider, phone, country, status, created_at, expires_at, otp_code, platform FROM orders WHERE user_id=? AND status='PENDING' ORDER BY id DESC", (uid,), fetch="all")
    orders = []
    if rows:
        for r in rows:
            orders.append({
                "id": r["id"], "provider": r["provider"], "phone": r["phone"], "country": r["country"],
                "status": r["status"], "created_at": r["created_at"], "expires_at": r["expires_at"], 
                "otp": r["otp_code"], "platform": r["platform"] or "",
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
    return web.json_response({"orders": orders, "current_page": page, "total_pages": total_pages, "total_records": total})

async def mini_create_order(request: web.Request) -> web.Response:
    uid = mini_uid(request)
    if uid is None:
        return web.json_response({"error": "Xác thực thất bại."}, status=401)
    maint = await get_setting("maintenance", "off")
    if maint == "on" and not await is_admin(uid):
        return web.json_response({"error": "Hệ thống đang bảo trì."}, status=403)
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Dữ liệu không hợp lệ."}, status=400)
        
    provider = (body.get("provider") or "").upper().strip()
    
    if provider == "MK":
        range_val = body.get("range", "").strip()
        if not range_val:
            return web.json_response({"error": "Thiếu mã range."}, status=400)
        data, err = await api_request("POST", "getnum/number", {"range": range_val}, api_type="MK")
        if err:
            return web.json_response({"error": f"Lỗi từ MK: {err}"}, status=400)
        if not data or "data" not in data:
            return web.json_response({"error": "Phản hồi MK không hợp lệ."}, status=502)
        inner = data["data"]
        rid   = inner.get("request_id")
        phone = inner.get("number") or inner.get("full_number") or ""
        ctry  = inner.get("country") or body.get("country_name") or "Unknown"
        exp   = inner.get("expires_at") or ""
        if not rid or not phone:
            return web.json_response({"error": "MK không trả về request_id hoặc số điện thoại."}, status=502)
        now_iso = now_text()
        await db_exec(
            "INSERT INTO orders (user_id, request_id, provider, phone, country, range_code, status, created_at, expires_at) VALUES (?, ?, 'MK', ?, ?, ?, 'PENDING', ?, ?)",
            (uid, str(rid), phone, ctry, range_val, now_iso, exp or now_iso)
        )
        await clean_old_orders(uid)
        return web.json_response({"ok": True, "request_id": str(rid), "phone": phone})
        
    elif provider == "NP":
        data, err = await api_request("POST", "request_number", {"service": body.get("service"), "country": body.get("country")}, api_type="NP")
        if err: return web.json_response({"error": f"Lỗi NP: {err}"}, status=400)
        phone = data.get("number"); rid = data.get("id") or phone
        if not phone: return web.json_response({"error": f"Lỗi NP: API không trả về số."}, status=400)
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
        payload = {"service": "ANY", "countryCode": body.get("country_code"), "tag": body.get("tag")}
        data, err = await api_request("POST", "rent", payload, api_type="SLVN")
        if err: return web.json_response({"error": f"Lỗi SLVN: {err}"}, status=400)
        order_data = data.get("data", {})
        rental_id = order_data.get("rentalId")
        phone = order_data.get("phoneNumber")
        country = order_data.get("country")
        await db_exec("INSERT INTO orders (user_id, request_id, provider, phone, country, range_code, status, created_at, expires_at) VALUES (?, ?, 'SLVN', ?, ?, ?, 'PENDING', ?, ?)", 
                      (uid, rental_id, phone, country, body.get("tag"), now_text(), (now() + timedelta(minutes=15)).isoformat()))
        await clean_old_orders(uid)
        return web.json_response({"ok": True})

    return web.json_response({"error": f"Provider '{provider}' không hợp lệ."}, status=400)

async def mini_cancel_order(request):
    oid = int(request.match_info["oid"])
    order = await db_exec("SELECT provider, request_id, phone FROM orders WHERE id=? AND user_id=?", (oid, mini_uid(request)), fetch="one")
    if not order: return web.json_response({"error": "Not found"}, status=404)
    if order["provider"] == "SLVN": await api_request("POST", f"cancel/{order['request_id']}", api_type="SLVN")
    elif order["provider"] == "NP": await api_request("POST", "release_number", {"number": order["phone"]}, api_type="NP")
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
    if await get_setting("maintenance", "off") == "on":
        return web.json_response({"error": "Hệ thống đang bảo trì."}, status=403)
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
    data, err = await api_request("GET", "access_list", params={"limit": 1000}, api_type="MK")
    countries = []
    if not err and data and "data" in data and "items" in data["data"]:
        c_map = {}
        for item in data["data"]["items"]:
            c_name = item.get("country")
            if c_name not in c_map: c_map[c_name] = []
            c_map[c_name].append(item.get("range"))
        for c_name, ranges in c_map.items():
            countries.append({"name": c_name, "range": ranges[0], "flag": get_country_flag(c_name)})
        return web.json_response({"countries": countries})
    return web.json_response({"countries": [{"name": k, "range": v, "flag": get_country_flag(k)} for k, v in FALLBACK_COUNTRIES.items()]})

async def mini_np_services(request):
    data, err = await api_request("GET", "services", api_type="NP")
    srvs = data.get("services", []) if data and not err else []
    return web.json_response({"services": [{"name": s["name"], "key": s["name"], "count": s["count"]} for s in srvs if s.get("count", 0) > 0]})

async def mini_np_countries(request):
    service = request.match_info["service"]
    data, err = await api_request("GET", "countries", params={"service": service}, api_type="NP")
    countries = data.get("countries", []) if data and not err else []
    return web.json_response({"countries": [{"code": c["name"], "name": ISO_MAP.get(c["name"], c["name"]), "count": c["count"]} for c in countries if c.get("count", 0) > 0]})

async def mini_bs_countries(request):
    rows = await db_exec("SELECT country, flag, COUNT(*) as c FROM basha_numbers GROUP BY country, flag", fetch="all")
    return web.json_response({"countries": [{"name": r["country"], "flag": r["flag"], "count": r["c"]} for r in rows] if rows else []})

async def mini_slvn_countries(request):
    data, err = await api_request("GET", "available-countries", params={"service": "any"}, api_type="SLVN")
    if err or not data: return web.json_response({"countries": []})
    return web.json_response({"countries": [{"name": c.get("country"), "code": c.get("countryCode"), "flag": c.get("flag"), "tag": c.get("tag"), "rate": c.get("rateUsd")} for c in data.get("data", [])]})

async def mini_admin_data(request):
    if not mini_admin_guard(request): return web.json_response({"error": "Forbidden"}, status=403)
    users = await db_exec("SELECT COUNT(*) as c FROM users", fetch="one")
    orders = await db_exec("SELECT COUNT(*) as c FROM orders", fetch="one")
    pending_wd = await db_exec("SELECT COUNT(*) as c FROM withdrawals WHERE status='PENDING'", fetch="one")
    bs_count = await db_exec("SELECT COUNT(*) as c FROM basha_numbers", fetch="one")
    wd_list = await db_exec("SELECT w.id, w.user_id, w.amount_milli, w.wallet_ton, u.first_name FROM withdrawals w JOIN users u ON u.user_id=w.user_id WHERE w.status='PENDING' ORDER BY w.id DESC LIMIT 20", fetch="all")
    return web.json_response({
        "stats": {"users": users["c"], "orders": orders["c"], "pending_wd": pending_wd["c"], "bs_count": bs_count["c"]},
        "withdrawals": [{"id": r["id"], "user_id": r["user_id"], "amount": r["amount_milli"], "wallet": r["wallet_ton"], "name": r["first_name"]} for r in wd_list] if wd_list else [],
        "maintenance": await get_setting("maintenance", "off")
    })

async def mini_admin_users(request):
    if not mini_admin_guard(request): return web.json_response({"error": "Forbidden"}, status=403)
    users = await db_exec("SELECT user_id, first_name, username, usd_milli, joined_at FROM users ORDER BY joined_at DESC LIMIT 50", fetch="all")
    return web.json_response({"users": [{"id": r["user_id"], "name": r["first_name"], "username": r["username"], "balance": r["usd_milli"], "joined": r["joined_at"]} for r in users]})

async def mini_admin_user_detail(request):
    if not mini_admin_guard(request): return web.json_response({"error": "Forbidden"}, status=403)
    uid = int(request.match_info["uid"])
    page = int(request.query.get("page", "1"))
    u = await db_exec("SELECT user_id, first_name, username, usd_milli, joined_at FROM users WHERE user_id=?", (uid,), fetch="one")
    if not u: return web.json_response({"error": "User not found"}, status=404)
    total_res = await db_exec("SELECT COUNT(*) as c FROM orders WHERE user_id=?", (uid,), fetch="one")
    total = total_res["c"] if total_res else 0
    total_pages = max(1, (total + HISTORY_PAGE_SIZE - 1) // HISTORY_PAGE_SIZE)
    if page > total_pages: page = total_pages
    offset = (page - 1) * HISTORY_PAGE_SIZE
    orders = await db_exec("SELECT id, provider, phone, status, created_at FROM orders WHERE user_id=? ORDER BY id DESC LIMIT ? OFFSET ?", (uid, HISTORY_PAGE_SIZE, offset), fetch="all")
    stats = await db_exec("SELECT provider, COUNT(*) as c FROM orders WHERE user_id=? GROUP BY provider", (uid,), fetch="all")
    s_map = {"MK": 0, "NP": 0, "BASHA": 0, "SLVN": 0}
    for s in (stats or []): s_map[s["provider"]] = s["c"]
    return web.json_response({
        "user": {"id": u["user_id"], "name": u["first_name"], "username": u["username"], "balance": u["usd_milli"], "joined": u["joined_at"]},
        "stats": s_map,
        "orders": [{"id": r["id"], "provider": r["provider"], "phone": r["phone"], "status": r["status"], "date": r["created_at"]} for r in (orders or [])],
        "current_page": page, "total_pages": total_pages
    })

async def mini_admin_cmd(request):
    if not mini_admin_guard(request): return web.json_response({"error": "Forbidden"}, status=403)
    body = await request.json()
    cmd = body.get("cmd")
    
    try:
        if cmd == "pollnow":
            if not _mk_poller: return web.json_response({"error": "Poller not running"})
            c, n, err = await _mk_poller._poll_once()
            if err: return web.json_response({"ok": True, "msg": f"Lỗi khi Poll OTP: {err}"})
            return web.json_response({"ok": True, "msg": f"Checked: {c} đơn.\nNew OTPs: {n}\nTrạng thái: OK"})
        elif cmd == "health":
            pending = await db_exec("SELECT COUNT(*) FROM orders WHERE status='PENDING'", fetch='one')
            poller = "OFF" if not _mk_poller else f"ON ({_mk_poller.interval}s, err={_mk_poller._consecutive_errors})"
            mk_status = "OK" if MK_API_KEY else "MISSING"
            np_status = "OK" if NP_API_KEY else "MISSING"
            return web.json_response({"ok": True, "msg": f"DB: Turso\nMK Key: {mk_status}\nNP Key: {np_status}\nPending Orders: {pending[0] if pending else 0}\nPoller: {poller}"})
        elif cmd == "whoami":
            data, err = await api_request("GET", "whoami", api_type="MK")
            if err: return web.json_response({"ok": True, "msg": f"API Error: {err}"})
            return web.json_response({"ok": True, "msg": json.dumps(data, indent=2, ensure_ascii=False)})
        elif cmd == "testnp":
            data, err = await api_request("GET", "services", api_type="NP")
            if err: return web.json_response({"ok": True, "msg": f"API Error: {err}"})
            return web.json_response({"ok": True, "msg": json.dumps(data, indent=2, ensure_ascii=False)[:1000]})
        elif cmd == "radar":
            data, err = await api_request("GET", "radar", params={"limit": 10}, api_type="MK")
            if err: return web.json_response({"ok": True, "msg": f"API Error: {err}"})
            return web.json_response({"ok": True, "msg": json.dumps(data, indent=2, ensure_ascii=False)[:2000]})
        return web.json_response({"error": "Unknown command"})
    except Exception as e:
        return web.json_response({"error": f"Lỗi thực thi: {str(e)}"}, status=500)

async def mini_admin_maintenance(request: web.Request) -> web.Response:
    if not mini_admin_guard(request):
        return web.json_response({"error": "Forbidden."}, status=403)
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "JSON không hợp lệ."}, status=400)
    action = body.get("action")
    if action == "enable":
        await set_setting("maintenance", "off")
        await set_setting("maint_message", "")
        await set_setting("maint_image", "")
        return web.json_response({"ok": True, "msg": "Đã TẮT bảo trì. Bot hoạt động bình thường."})
    elif action == "disable":
        message   = (body.get("message") or "").strip()
        image_b64 = body.get("image_b64", "")
        if not message:
            return web.json_response({"error": "Vui lòng nhập nội dung thông báo bảo trì."}, status=400)
        if image_b64 and len(image_b64) > 5_333_333:
            return web.json_response({"error": "Ảnh quá lớn (tối đa 4MB)."}, status=400)
        
        await set_setting("maintenance", "on")
        await set_setting("maint_message", message)
        await set_setting("maint_image", image_b64)
        
        sent = 0
        photo_bytes = None
        if image_b64:
            try:
                _, encoded_part = image_b64.split(",", 1)
                photo_bytes = base64.b64decode(encoded_part)
            except Exception:
                photo_bytes = None
        users = await db_exec("SELECT user_id FROM users", fetch="all") or []
        for row in users:
            try:
                target = int(row["user_id"])
                if photo_bytes:
                    photo = BufferedInputFile(photo_bytes, filename="maintenance.jpg")
                    await bot.send_photo(target, photo=photo, caption=f"🛠 <b>THÔNG BÁO BẢO TRÌ</b>\n\n{message}")
                else:
                    await bot.send_message(target, f"🛠 <b>THÔNG BÁO BẢO TRÌ</b>\n\n{message}", parse_mode="HTML")
                sent += 1
                await asyncio.sleep(0.05)
            except Exception:
                pass
        return web.json_response({"ok": True, "msg": f"Đã BẬT bảo trì. Gửi tới {sent}/{len(users)} user."})
    return web.json_response({"error": "Action không hợp lệ."}, status=400)

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

async def mini_admin_bs_delete(request):
    if not mini_admin_guard(request): return web.json_response({"error": "Forbidden"}, status=403)
    body = await request.json()
    country = body.get("country")
    if country == "ALL": await db_exec("DELETE FROM basha_numbers")
    else: await db_exec("DELETE FROM basha_numbers WHERE country=?", (country,))
    return web.json_response({"ok": True})

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


# ==================== WEB SERVER & STATIC FILE SERVING ====================

async def web_server():
    # Đảm bảo thư mục static tồn tại trước khi serve
    os.makedirs('static', exist_ok=True)
    
    app = web.Application(
        middlewares=[mini_auth_middleware],
        client_max_size=10 * 1024 * 1024,
    )
    
    async def serve_index(request):
        """Trả về file static/index.html kèm header chống cache tuyệt đối"""
        html_path = os.path.join('static', 'index.html')
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                content = f.read()
            response = web.Response(text=content, content_type='text/html')
            
            # CHỐNG CACHE TUYỆT ĐỐI
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
        except FileNotFoundError:
            logger.error("Không tìm thấy file static/index.html")
            return web.Response(text="<h1>Lỗi: Chưa có file static/index.html</h1>", content_type='text/html', status=404)
            
    async def health(request): return web.json_response({"ok": True})
        
    # Đăng ký route
    app.router.add_get('/', serve_index)
    app.router.add_get('/mini', serve_index)
    app.router.add_get('/health', health)
    
    # Serve thư mục static (CSS, JS, images,...)
    app.router.add_static('/static/', path='static', name='static')
    
    # API routes
    app.router.add_get('/api/mini/me', mini_me)
    app.router.add_post('/api/mini/language', mini_language_update)
    app.router.add_get('/api/mini/stats', mini_stats)
    app.router.add_get('/api/mini/leaderboard', mini_leaderboard)
    app.router.add_get('/api/mini/orders', mini_get_orders)
    app.router.add_get('/api/mini/orders/active', mini_active_orders)
    app.router.add_get('/api/mini/orders/history', mini_history_orders)
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
    app.router.add_get('/api/mini/admin/users', mini_admin_users)
    app.router.add_get('/api/mini/admin/users/{uid}', mini_admin_user_detail)
    app.router.add_post('/api/mini/admin/cmd', mini_admin_cmd)
    app.router.add_post('/api/mini/admin/maintenance', mini_admin_maintenance)
    app.router.add_post('/api/mini/admin/withdraw/action', mini_admin_wd_action)
    app.router.add_post('/api/mini/admin/bs/add', mini_admin_bs_add)
    app.router.add_post('/api/mini/admin/bs/delete', mini_admin_bs_delete)
    
    runner = web.AppRunner(app); await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT); await site.start()
    logger.info("FAST IVAS Mini App server started on port %s", PORT)

async def set_bot_commands():
    user_commands = [BotCommand(command="start", description="Open main menu")]
    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())
    admin_commands = user_commands + [BotCommand(command="admin", description="[Admin] Panel"), BotCommand(command="broadcast", description="[Admin] Broadcast")]
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
        if not rows: return 0, 0, None
        checked = new_otp = 0
        error_msg = None
        
        for r in rows:
            if r["provider"] == "MK":
                checked += 1
                data, err = await api_request("POST", "check/status", {"request_ids": [int(r["request_id"])]})
                if err: error_msg = err
                elif data:
                    inner = data.get("data", {})
                    res = inner.get("results", [])
                    if res and res[0].get("status") == "success":
                        if await self._process_otp(r, res[0]["otp_code"], res[0].get("full_sms", "")): new_otp += 1
            elif r["provider"] == "NP":
                checked += 1
                data, err = await api_request("GET", "latest_otp", params={"number": r["phone"]}, api_type="NP")
                if err: error_msg = err
                elif data and data.get("has_otp"):
                    if await self._process_otp(r, data["otp_code"], f"OTP: {data['otp_code']}"): new_otp += 1
            elif r["provider"] == "BASHA":
                checked += 1
                data, err = await api_request("POST", "legacy/get-last-sms", {"number": r["phone"]}, api_type="BASHA")
                if err: error_msg = err
                elif data and data.get("message"):
                    otp_match = re.search(r'\b(\d{4,8})\b', data["message"])
                    if otp_match and await self._process_otp(r, otp_match.group(1), data["message"]): new_otp += 1
            elif r["provider"] == "SLVN":
                checked += 1
                data, err = await api_request("GET", f"check-otp/{r['request_id']}", api_type="SLVN")
                if err: error_msg = err
                elif data and data.get("status") == "success":
                    inner = data.get("data", {})
                    if inner.get("status") == "RECEIVED":
                        if await self._process_otp(r, inner.get("otpCode"), inner.get("fullSms", "")): new_otp += 1
        return checked, new_otp, error_msg

    async def run_forever(self):
        while True:
            try: 
                await self._poll_once()
            except Exception as e: logger.error(f"Poller error: {e}")
            await asyncio.sleep(10)

async def main():
    global BOT_USERNAME, _mk_poller
    try: 
        me = await bot.get_me(); BOT_USERNAME = me.username; await set_bot_commands()
        if WEBAPP_URL.startswith("https://"):
            await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="FAST IVAS", web_app=WebAppInfo(url=WEBAPP_URL + "?v=7")))
    except Exception as e: logger.error(f"Error setting menu: {e}")
    
    await init_db()
    asyncio.create_task(web_server())
    
    _mk_poller = MkOtpPoller()
    asyncio.create_task(_mk_poller.run_forever())
    
    logger.info("FAST IVAS starting...")
    await dp.start_polling(bot, drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())