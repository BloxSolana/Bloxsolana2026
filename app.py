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
from aiogram import Bot, Dispatcher, F, BaseMiddleware
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand, BotCommandScopeChat, BotCommandScopeDefault, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest

# =====================================================
# CONFIG
# =====================================================
BOT_TOKEN      = "8622066775:AAE0b37izrhaG8ZKrGqmCVS_5tTPQS9hzMo" # Nhớ thay token mới của bro vào đây
ADMIN_ID       = 6726769296
OTP_GROUP_ID   = -1004341368656
OTP_GROUP_URL  = "https://t.me/LIVEOTPIVAS"
MAIN_CHANNEL_URL = "https://t.me/FastNode_1"

MK_API_KEY     = "badacaa33d287233567a49db" 
MK_API_BASE    = "https://mknetworkbd.com/api/v3/public"

NP_API_KEY     = "np_live_lrRtdKcOeg-syi8UCpmaA_idYmBZY0zbpwl5P--gF-g"
NP_API_BASE    = "https://numberpanel.tech/api" 

BASHA_API_KEY  = "bsh_OIU1o9DdaQLzznNZ1VyNgS8OknJqIYVh"
BASHA_API_BASE = "https://basha.cc/api"

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
VN_TZ = timezone(timedelta(hours=7))

# =====================================================
# MIDDLEWARE BẮT LỖI
# =====================================================
class ErrorMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        try:
            return await handler(event, data)
        except Exception as e:
            logger.error(f"Handler error: {e}")
            try:
                if isinstance(event, Message):
                    await event.answer(f"⚠️ <b>Lỗi xử lý:</b> <code>{safe(str(e))}</code>\nVui lòng thử lại.")
                elif isinstance(event, CallbackQuery):
                    await event.answer(f"⚠️ Lỗi: {safe(str(e))}", show_alert=True)
            except: pass

dp.message.middleware(ErrorMiddleware())
dp.callback_query.middleware(ErrorMiddleware())

# =====================================================
# TỪ ĐIỂN QUỐC GIA VÀ MÃ VÙNG
# =====================================================
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

def detect_country_from_phone(phone):
    clean_phone = phone.lstrip('+').strip()
    for prefix in SORTED_PREFIXES:
        if clean_phone.startswith(prefix):
            return COUNTRY_CODES[prefix]
    return ("Unknown", "🌐")

def get_country_flag(c):
    if not c: return "🌐"
    for k, v in COUNTRY_CODES.items():
        if v[0].lower() == str(c).lower(): return v[1]
    return "🌐"

def get_network_icon(net):
    net = str(net).upper()
    return "📘" if "FACEBOOK" in net else "📸" if "INSTAGRAM" in net else "💬" if "WHATSAPP" in net else "✈️" if "TELEGRAM" in net else "📱" if "TIKTOK" in net else "🧵" if "THREADS" in net else "🇬" if "GOOGLE" in net else "🐦" if "TWITTER" in net or "X" in net else "🌐"

ADMIN_PENDING_APPROVE = {} 
MSG_TO_DELETE = {}
_mk_poller = None

# =====================================================
# LANGUAGE SETTINGS
# =====================================================
LANGUAGES = [("en", "🇺🇸 English"), ("vi", "🇻🇳 Tiếng Việt")]
LANGUAGE_PAGE_SIZE = 10

TRANSLATIONS = {
    "en": {
        "app": "📱 App", "account": "👤 Account", "number1": "🎱 Number", "number2": "📱 Numbers 2", "number3": "🔢 BS",
        "withdraw": "💰 Withdraw", "invite": "💌 Invite", "stats": "📊 Ranges Stats",
        "leaderboard": "🏆 Leaderboard", "history": "📜 History", "wallet": "💵 Wallet",
        "otp_group": "📢 OTP Group", "language": "🌐 Language", "admin_panel": "🛡 ADMIN PANEL",
        "welcome": "Welcome!\nSelect an option below:",
        "select_country": "🌍 <b>SELECT COUNTRY (MK)</b>\n\nClick a country to get a number:",
        "numbers_assigned": "✅ <b>Numbers Assigned!</b>",
        "service": "🔧 Service", "country": "🌍 Country",
        "number": "Number", "wait_otp": "⏳ Waiting for OTP...",
        "remove_code": "❌ Remove Country Code", "change_num": "🔄 Change Number",
        "main_menu": "🏠 Main Menu", "back": "⬅️ Back",
        "cancel_order": "❌ Cancel Order", "new_numbers": "🔢 New Numbers"
    },
    "vi": {
        "app": "📱 Ứng dụng", "account": "👤 Tài khoản", "number1": "🎱 Số (MK)", "number2": "📱 Số (NP)", "number3": "🔢 BS",
        "withdraw": "💰 Rút tiền", "invite": "💌 Mời bạn bè", "stats": "📊 Thống kê",
        "leaderboard": "🏆 Bảng xếp hạng", "history": "📜 Lịch sử", "wallet": "💵 Ví",
        "otp_group": "📢 Nhóm OTP", "language": "🌐 Ngôn ngữ", "admin_panel": "🛡 QUẢN TRỊ",
        "welcome": "Chào mừng!\nVui lòng chọn một tùy chọn bên dưới:",
        "select_country": "🌍 <b>CHỌN QUỐC GIA (MK)</b>\n\nBấm vào quốc gia để lấy số:",
        "numbers_assigned": "✅ <b>Đã lấy số thành công!</b>",
        "service": "🔧 Dịch vụ", "country": "🌍 Quốc gia",
        "number": "Số", "wait_otp": "⏳ Đang chờ OTP...",
        "remove_code": "❌ Xóa mã quốc gia", "change_num": "🔄 Đổi số",
        "main_menu": "🏠 Menu chính", "back": "⬅️ Quay lại",
        "cancel_order": "❌ Hủy đơn", "new_numbers": "🔢 Lấy số mới"
    }
}

async def get_user_language(uid):
    res = await db_exec("SELECT language FROM users WHERE user_id=?", (uid,), fetch='one')
    return res[0] if res and res[0] else "en"

async def get_text(uid, key):
    lang = await get_user_language(uid)
    lang_dict = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    return lang_dict.get(key, TRANSLATIONS["en"].get(key, key))

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
        "PENDING": "⏳ Pending", "EXPIRED": "⌛ Expired", "COMPLETED": "✅ Received",
        "FAILED": "❌ Failed", "APPROVED": "✅ Approved", "REJECTED": "❌ Rejected", "CANCELLED": "🚫 Cancelled"
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
    while len(MSG_TO_DELETE[chat_id]) > 1:
        old_msg = MSG_TO_DELETE[chat_id].pop(0)
        asyncio.create_task(safe_delete_msg(chat_id, old_msg))

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def detect_otp_platform(full_sms):
    if not full_sms: return "Other"
    sms = full_sms.lower()
    for name, kw in {"TikTok": ["tiktok"], "Facebook": ["facebook", "fb"], "Instagram": ["instagram"], "Threads": ["threads"], "Google": ["google", "gmail"], "Telegram": ["telegram"], "WhatsApp": ["whatsapp"], "Zalo": ["zalo"], "Twitter": ["twitter"], "Shopee": ["shopee"], "Apple": ["apple"], "Microsoft": ["microsoft"]}.items():
        if any(k in sms for k in kw): return name
    return "Other"

def fmt_date(iso_str):
    if not iso_str: return "N/A"
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.astimezone(VN_TZ).strftime("%d/%m %H:%M")
    except: return iso_str[:16].replace("T", " ")

def fmt_date_full(iso_str):
    if not iso_str: return "N/A"
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.astimezone(VN_TZ).strftime("%H:%M:%S - %d/%m/%Y")
    except: return iso_str[:16].replace("T", " ")

# =====================================================
# DATABASE (GIA CỐ CHỐNG TREO & FIX LỖI INSERT)
# =====================================================
def get_db():
    if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
        try: return libsql.connect("local_replica.db", sync_url=TURSO_DATABASE_URL, auth_token=TURSO_AUTH_TOKEN)
        except Exception: return libsql.connect("local.db")
    return libsql.connect("local.db")

def _sync_db_exec(query, params=None, fetch=None, dict_mode=False):
    db = None
    try:
        db = get_db()
        cursor = db.execute(query, params or ())
        res = None
        if fetch == 'one':
            row = cursor.fetchone()
            res = dict_factory(cursor, row) if dict_mode and row else row
        elif fetch == 'all':
            rows = cursor.fetchall()
            res = [dict_factory(cursor, r) for r in rows] if dict_mode else rows
        else:
            db.commit()
            res = cursor.lastrowid if cursor.lastrowid else True
        return res
    except Exception as e:
        logger.error(f"DB Error: {e}")
        return None
    finally:
        if db:
            try: db.close()
            except: pass

async def db_exec(query, params=None, fetch=None, dict_mode=False):
    loop = asyncio.get_running_loop()
    try:
        return await asyncio.wait_for(loop.run_in_executor(None, _sync_db_exec, query, params, fetch, dict_mode), timeout=10.0)
    except asyncio.TimeoutError:
        logger.error("DB Timeout - Turso is slow!")
        return None

async def init_db():
    await db_exec("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, usd_milli INTEGER NOT NULL DEFAULT 0, wallet_ton TEXT, referrer INTEGER, joined_at TEXT)")
    await db_exec("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, request_id TEXT UNIQUE, provider TEXT DEFAULT 'MK', platform TEXT, phone TEXT, country TEXT, operator TEXT, range_code TEXT, status TEXT NOT NULL DEFAULT 'PENDING', otp_code TEXT, full_sms TEXT, reward_milli INTEGER NOT NULL DEFAULT 0, msg_id INTEGER, created_at TEXT, expires_at TEXT, updated_at TEXT)")
    await db_exec("CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, amount INTEGER NOT NULL, tx_type TEXT, note TEXT, created_at TEXT)")
    await db_exec("CREATE TABLE IF NOT EXISTS withdrawals (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, amount_milli INTEGER NOT NULL, wallet_ton TEXT, status TEXT NOT NULL DEFAULT 'PENDING', reject_reason TEXT, tx_hash TEXT, proof_photo TEXT, created_at TEXT, processed_at TEXT)")
    await db_exec("CREATE TABLE IF NOT EXISTS basha_numbers (id INTEGER PRIMARY KEY AUTOINCREMENT, phone TEXT UNIQUE NOT NULL, country TEXT NOT NULL, flag TEXT NOT NULL, added_at TEXT)")
    
    for q in [
        "ALTER TABLE withdrawals ADD COLUMN reject_reason TEXT", "ALTER TABLE withdrawals ADD COLUMN tx_hash TEXT",
        "ALTER TABLE withdrawals ADD COLUMN proof_photo TEXT", "ALTER TABLE orders ADD COLUMN provider TEXT DEFAULT 'MK'",
        "ALTER TABLE orders ADD COLUMN platform TEXT", "ALTER TABLE users ADD COLUMN language TEXT NOT NULL DEFAULT 'en'"
    ]:
        await db_exec(q)

async def register_user(tg_user, referrer=None):
    name = tg_user.first_name or "User"
    res = await db_exec("SELECT user_id FROM users WHERE user_id=?", (tg_user.id,), fetch='one')
    if res:
        await db_exec("UPDATE users SET username=?, first_name=? WHERE user_id=?", (tg_user.username, name, tg_user.id))
        return False
    if referrer == tg_user.id: referrer = None
    await db_exec("INSERT INTO users (user_id, username, first_name, usd_milli, referrer, joined_at) VALUES (?, ?, ?, 0, ?, ?)", (tg_user.id, tg_user.username, name, referrer, now_text()))
    return True

async def get_user(uid):
    return await db_exec("SELECT * FROM users WHERE user_id=?", (uid,), fetch='one', dict_mode=True)

async def set_wallet_ton(uid, wallet_ton):
    await db_exec("UPDATE users SET wallet_ton=? WHERE user_id=?", (wallet_ton, uid))

async def change_usd(uid, amount_milli, tx_type, note):
    def _tx():
        db = get_db()
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
            db.rollback()
            return False, str(e)
        finally: db.close()
    return await asyncio.to_thread(_tx) if hasattr(asyncio, 'to_thread') else await asyncio.get_running_loop().run_in_executor(None, _tx)

async def create_withdrawal(uid, amount_milli, wallet_ton):
    return await db_exec("INSERT INTO withdrawals (user_id, amount_milli, wallet_ton, status, created_at) VALUES (?, ?, ?, 'PENDING', ?)", (uid, amount_milli, wallet_ton, now_text()))

async def expire_old_orders():
    t = now_text()
    rows = await db_exec("SELECT id, user_id, msg_id, phone, country FROM orders WHERE status='PENDING' AND expires_at IS NOT NULL AND expires_at<=?", (t,), fetch='all')
    if not rows: return
    for r in rows:
        oid, uid, msg_id, phone, country = r
        await db_exec("UPDATE orders SET status='EXPIRED', updated_at=? WHERE id=?", (t, oid))
        if msg_id:
            try: 
                await bot.edit_message_text(chat_id=uid, message_id=msg_id, text=f"⌛ <b>ORDER EXPIRED</b>\n\nNumber: <code>{safe(phone)}</code> ({safe(country)})\nStatus: Expired.\n\nPlease choose an action below:", reply_markup=expired_kb())
            except Exception: pass

async def set_user_language(uid, lang):
    allowed = {item[0] for item in LANGUAGES}
    if lang not in allowed: return False
    await db_exec("UPDATE users SET language=? WHERE user_id=?", (lang, uid))
    return True

async def get_user_orders(uid, limit=HISTORY_PER_PAGE, offset=0):
    await expire_old_orders()
    rows = await db_exec("SELECT id, request_id, provider, phone, country, operator, status, created_at, expires_at FROM orders WHERE user_id=? ORDER BY id DESC LIMIT ? OFFSET ?", (uid, limit, offset), fetch='all')
    return rows or []

async def get_order(oid, uid=None):
    if uid is None: return await db_exec("SELECT * FROM orders WHERE id=?", (oid,), fetch='one', dict_mode=True)
    return await db_exec("SELECT * FROM orders WHERE id=? AND user_id=?", (oid, uid), fetch='one', dict_mode=True)

async def get_all_orders(limit=15):
    await expire_old_orders()
    rows = await db_exec("SELECT id, user_id, request_id, phone, status FROM orders ORDER BY id DESC LIMIT ?", (limit,), fetch='all')
    return rows or []

async def get_pending_requests(limit=100):
    rows = await db_exec("SELECT id, user_id, request_id, provider, phone, msg_id, range_code, country, operator FROM orders WHERE status='PENDING' ORDER BY id ASC LIMIT ?", (limit,), fetch='all')
    if not rows: return []
    return [{"id": r[0], "user_id": r[1], "request_id": r[2], "provider": r[3], "phone": r[4], "msg_id": r[5], "range_code": r[6], "country": r[7], "operator": r[8]} for r in rows]

# =====================================================
# API CORE
# =====================================================
HTTP_ERRORS = {401: "Invalid API key.", 403: "API locked.", 404: "Out of stock.", 429: "Rate limit.", 500: "API Error."}

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
                if r.status >= 400: return None, HTTP_ERRORS.get(r.status, f"API Error ({r.status})")
                if isinstance(data, dict) and data.get("success") is False: return None, str(data.get("message") or "API Error")
                return data, None
    except asyncio.TimeoutError: return None, "Connection timeout."
    except Exception: return None, "Cannot connect to API."

async def api_get(ep, params=None): return await api_request("GET", ep, params=params)

async def np_api_request(method, endpoint, payload=None, params=None):
    headers = {"Authorization": f"Bearer {NP_API_KEY}", "Accept": "application/json", "User-Agent": "Mozilla/5.0"}
    if payload is not None: headers["Content-Type"] = "application/json"
    url = f"{NP_API_BASE}/{endpoint.lstrip('/')}"
    timeout = aiohttp.ClientTimeout(total=25)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.request(method, url, headers=headers, json=payload, params=params) as r:
                raw = await r.text()
                try: data = json.loads(raw)
                except json.JSONDecodeError: data = {"response": raw[:1000]}
                if r.status >= 400: return None, f"NP API Error ({r.status})"
                if isinstance(data, dict) and data.get("success") is False: return None, str(data.get("message") or "API Error")
                return data, None
    except asyncio.TimeoutError: return None, "Connection timeout."
    except Exception: return None, "Cannot connect to NP API."

async def basha_api_request(method, endpoint, payload=None):
    headers = {"Authorization": f"Bearer {BASHA_API_KEY}", "Content-Type": "application/json", "Accept": "application/json"}
    url = f"{BASHA_API_BASE}/{endpoint.lstrip('/')}"
    timeout = aiohttp.ClientTimeout(total=25)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.request(method, url, headers=headers, json=payload) as r:
                raw = await r.text()
                try: data = json.loads(raw)
                except json.JSONDecodeError: data = {"response": raw[:1000]}
                if r.status >= 400: return None, f"Basha API Error ({r.status}): {raw[:100]}"
                return data, None
    except asyncio.TimeoutError: return None, "Connection timeout."
    except Exception as e: return None, f"Cannot connect to Basha API: {e}"

def unwrap(d):
    if not isinstance(d, dict): return {}
    for k in ("data", "result", "response"):
        v = d.get(k)
        if isinstance(v, dict): return v
    return d

def field(d, *names, default=""):
    if not isinstance(d, dict): return default
    sources = [d, unwrap(d)]
    if isinstance(d.get("data"), dict): sources.append(d.get("data"))
    for src in sources:
        for n in names:
            val = src.get(n)
            if val is not None and str(val).strip() != "": return val
    return default

def strip_secrets(obj):
    blocked = {"otp","otp_code","code","full_sms","sms","message", "api_key","token","authorization","password"}
    if isinstance(obj, dict): return {k: strip_secrets(v) for k, v in obj.items() if k.lower() not in blocked}
    if isinstance(obj, list): return [strip_secrets(x) for x in obj[:30]]
    return obj

def fmt_api(d): return html.escape(json.dumps(strip_secrets(d), ensure_ascii=False, indent=2, default=str)[:3500])

# =====================================================
# TẠO ĐƠN & HELPER
# =====================================================
async def create_number_order(uid, range_code, msg_id=None):
    if not range_code or len(range_code) > 80 or any(c.isspace() for c in range_code): return False, "Invalid range code."
    data, err = await api_request("POST", "getnum/number", {"range": range_code})
    if err: return False, err

    def find_valid_id(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                k_lower = str(k).lower()
                if ("id" in k_lower or "request" in k_lower) and str(v).isdigit(): return str(v)
            for v in obj.values():
                res = find_valid_id(v)
                if res is not None: return res
        elif isinstance(obj, list):
            for item in obj:
                res = find_valid_id(item)
                if res is not None: return res
        return None

    rid_str = find_valid_id(data)
    if rid_str is None: return False, "No ID found in API response."

    phone, country, operator = field(data, "number", "phone", "phone_number"), field(data, "country", "country_name"), field(data, "operator", "network", "carrier")
    exp = (now() + timedelta(minutes=ORDER_LIFETIME_MINUTES)).isoformat(timespec="seconds")
    
    res = await db_exec("INSERT INTO orders (user_id, request_id, provider, phone, country, operator, range_code, status, created_at, expires_at, updated_at, msg_id) VALUES (?, ?, 'MK', ?, ?, ?, ?, 'PENDING', ?, ?, ?, ?)", (uid, rid_str, str(phone or "N/A"), str(country or "?"), str(operator or "?"), range_code, now_text(), exp, now_text(), msg_id))
    if res is None: return False, "Database error."

    return True, {"request_id": rid_str, "phone": phone or "N/A", "country": country or "?", "operator": operator or "?", "expires_at": exp}

# =====================================================
# MAIN MENU HANDLERS
# =====================================================
async def logic_profile(message: Message):
    await register_user(message.from_user)
    u = await get_user(message.from_user.id)
    if not u: await message.answer("Lỗi tải dữ liệu."); return
    msg = await message.answer("👤 <b>ACCOUNT</b>\n\n" f"ID: <code>{u['user_id']}</code>\nName: {safe(u['first_name'])}\nUsername: @{safe(u['username'] or '—')}\nJoined: {safe(u['joined_at'][:10])}\n\n" f"💵 Balance: <b>{usd(u['usd_milli'])}</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")]]))
    track_msg(message.from_user.id, msg.message_id)

async def logic_numbers2(message: Message):
    loading_msg = await message.answer("⏳ Đang tải danh sách dịch vụ...")
    data, err = await np_api_request("GET", "services")
    services = data.get("services") or data.get("data", {}).get("services", []) if not err and data else []
    try: await loading_msg.delete()
    except: pass
    
    if not services:
        msg = await message.answer("⚠️ <b>LỖI KẾT NỐI NUMBER PANEL</b>\n\nHệ thống đang bảo trì.")
        track_msg(message.from_user.id, msg.message_id)
        return
        
    buttons = []; row = []
    for svc in services:
        if svc.get("count", 0) > 0:
            name = svc.get("name", "Unknown"); key = svc.get("key", name)
            row.append(InlineKeyboardButton(text=f"{get_network_icon(name)} {name} ({svc['count']})", callback_data=f"np_svc_{key}"))
            if len(row) == 2: buttons.append(row); row = []
    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")])
    msg = await message.answer("📱 <b>NUMBER PANEL (NEW)</b>\n\nVui lòng chọn Dịch vụ:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    track_msg(message.from_user.id, msg.message_id)

async def logic_withdraw(message: Message):
    u = await get_user(message.from_user.id)
    if not u: return
    wallet = u["wallet_ton"] or "Not set"
    text = f"💸 <b>WITHDRAW USD VIA TON</b>\n\nCurrent Balance: <b>{usd(u['usd_milli'])}</b>\nTON Wallet: <code>{wallet}</code>\n\nPlease select an action:"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚙️ Setup TON Wallet", callback_data="wd_setup_addr")], [InlineKeyboardButton(text="💵 Withdraw", callback_data="wd_choose_amount")], [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")]])
    msg = await message.answer(text, reply_markup=kb)
    track_msg(message.from_user.id, msg.message_id)

async def logic_referral(message: Message):
    link = f"https://t.me/{BOT_USERNAME}?start={message.from_user.id}"
    text = f"👥 <b>INVITE FRIENDS</b>\n\nInvite your friends:\n<code>{link}</code>"
    msg = await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")]]))
    track_msg(message.from_user.id, msg.message_id)

async def logic_wallet(message: Message):
    await register_user(message.from_user)
    u = await get_user(message.from_user.id)
    if not u: return
    msg = await message.answer("💵 <b>WALLET</b>\n\n" f"Balance: <b>{usd(u['usd_milli'])}</b>\nReward/OTP: <b>{usd(REWARD_MILLI_PER_OTP)}</b>\nMin Withdraw: <b>{usd(MIN_WITHDRAW_MILLI)}</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")]]))
    track_msg(message.from_user.id, msg.message_id)

async def logic_group(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👉 Join OTP Group", url=OTP_GROUP_URL)], [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")]])
    msg = await message.answer("Join the OTP group for latest updates:", reply_markup=kb)
    track_msg(message.from_user.id, msg.message_id)

async def logic_language(message: Message):
    await register_user(message.from_user)
    current = await get_user_language(message.from_user.id)
    current_name = next((name for code, name in LANGUAGES if code == current), "🇺🇸 English")
    await message.answer(f"🌐 <b>LANGUAGE</b>\n\nCurrent: {safe(current_name)}\nChoose:", reply_markup=language_picker_kb(0))

async def logic_admin(message: Message):
    if not is_admin(message.from_user.id): return
    msg = await message.answer("🛡 <b>ADMIN PANEL</b>", reply_markup=admin_kb())
    track_msg(message.from_user.id, msg.message_id)

# HÀM APP DASHBOARD (GỘP CHUNG)
async def logic_app(message: Message):
    uid = message.from_user.id
    u = await get_user(uid)
    if not u:
        await register_user(message.from_user)
        u = await get_user(uid)

    # Lấy thông tin nhanh
    total_orders = await db_exec("SELECT COUNT(*) FROM orders WHERE user_id=?", (uid,), fetch='one')
    today_otps = await db_exec("SELECT COUNT(*) FROM orders WHERE user_id=? AND status='COMPLETED' AND created_at >= ?", (uid, now().strftime("%Y-%m-%d")), fetch='one')
    
    text = (
        f"🚀 <b>FAST IVAS DASHBOARD</b> 🚀\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>User:</b> {safe(u['first_name'])}\n"
        f"🆔 <b>ID:</b> <code>{uid}</code>\n"
        f"💵 <b>Balance:</b> <b>{usd(u['usd_milli'])}</b>\n"
        f"🔑 <b>Today OTPs:</b> {today_otps[0] if today_otps else 0}\n"
        f"📦 <b>Total Orders:</b> {total_orders[0] if total_orders else 0}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👇 Chọn thao tác bên dưới để tiếp tục:"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎱 Numbers 1 (MK)", callback_data="list_countries"), InlineKeyboardButton(text="📱 Numbers 2 (NP)", callback_data="app_np")],
        [InlineKeyboardButton(text="🔢 Numbers BS", callback_data="list_basha_countries"), InlineKeyboardButton(text="💵 Nạp / Rút", callback_data="app_wallet")],
        [InlineKeyboardButton(text="📜 Lịch sử", callback_data="user_orders_history"), InlineKeyboardButton(text="📊 Thống kê", callback_data="ranges_stats")],
        [InlineKeyboardButton(text="💌 Mời bạn bè", callback_data="app_invite"), InlineKeyboardButton(text="🌐 Ngôn ngữ", callback_data="app_lang")],
        [InlineKeyboardButton(text="⬅️ Về Menu Chính", callback_data="home")]
    ])
    
    msg = await message.answer(text, reply_markup=kb)
    track_msg(uid, msg.message_id)

# =====================================================
# KEYBOARDS
# =====================================================
async def get_main_reply_kb(uid):
    lang = await get_user_language(uid)
    t = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    keyboard = [
        [KeyboardButton(text=t["app"]), KeyboardButton(text=t["account"])],
        [KeyboardButton(text=t["number1"]), KeyboardButton(text=t["number2"])],
        [KeyboardButton(text=t["number3"]), KeyboardButton(text=t["withdraw"])],
        [KeyboardButton(text=t["invite"]), KeyboardButton(text=t["stats"])],
        [KeyboardButton(text=t["leaderboard"]), KeyboardButton(text=t["history"])],
        [KeyboardButton(text=t["wallet"]), KeyboardButton(text=t["otp_group"])],
        [KeyboardButton(text=t["language"])]
    ]
    if is_admin(uid):
        keyboard.append([KeyboardButton(text=t["admin_panel"])])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def order_status_kb(order_id=None):
    rows = []
    if order_id:
        rows.append([InlineKeyboardButton(text="🔄 Refresh", callback_data=f"refresh_order_{order_id}"), InlineKeyboardButton(text="📜 Check OTP", callback_data="user_orders_history")])
    else:
        rows.append([InlineKeyboardButton(text="📜 Check OTP", callback_data="user_orders_history")])
    rows.append([InlineKeyboardButton(text="❌ Cancel", callback_data=f"cancel_num_{order_id}" if order_id else "cancel_num_0")])
    rows.append([InlineKeyboardButton(text="🌍 Change Country", callback_data="list_countries")])
    rows.append([InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistics", callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 User List", callback_data="admin_users")],
        [InlineKeyboardButton(text="📦 Orders", callback_data="admin_orders")],
        [InlineKeyboardButton(text="💸 Approve TON", callback_data="admin_withdraws")],
        [InlineKeyboardButton(text="✅ Approve History", callback_data="admin_withdraws_history")],
        [InlineKeyboardButton(text="➕ Add BS Numbers (Text/File)", callback_data="admin_add_bs")],
        [InlineKeyboardButton(text="⚙️ Manage BS Numbers", callback_data="admin_manage_bs")],
        [InlineKeyboardButton(text="🛠 Admin Commands", callback_data="admin_cmds")],
        [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")]
    ])

def admin_cmds_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Force Poll OTP (/pollnow)", callback_data="run_cmd_pollnow")],
        [InlineKeyboardButton(text="🟢 Health Check (/health)", callback_data="run_cmd_health")],
        [InlineKeyboardButton(text="📊 MK Account (/whoami)", callback_data="run_cmd_whoami")],
        [InlineKeyboardButton(text="🗺 MK Ranges (/access_list)", callback_data="run_cmd_access_list")],
        [InlineKeyboardButton(text="📡 MK Radar (/radar)", callback_data="run_cmd_radar")],
        [InlineKeyboardButton(text="🧪 Test NP API", callback_data="run_cmd_testnp")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="admin_menu")]
    ])

def expired_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Get New Number", callback_data="list_countries")],
        [InlineKeyboardButton(text="📜 Check History", callback_data="user_orders_history")],
        [InlineKeyboardButton(text="🏠 Home", callback_data="home")]
    ])

def language_picker_kb(page=0):
    start = page * LANGUAGE_PAGE_SIZE
    subset = LANGUAGES[start:start + LANGUAGE_PAGE_SIZE]
    rows = [[InlineKeyboardButton(text=label, callback_data=f"lang_set_{code}")] for code, label in subset]
    nav = []
    if page > 0: nav.append(InlineKeyboardButton(text="⬅️ Previous", callback_data=f"lang_page_{page-1}"))
    if start + LANGUAGE_PAGE_SIZE < len(LANGUAGES): nav.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"lang_page_{page+1}"))
    if nav: rows.append(nav)
    rows.append([InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# =====================================================
# TEXT HANDLERS
# =====================================================
@dp.message(CommandStart())
async def cmd_start(message: Message):
    try: await message.delete()
    except: pass
    args = message.text.split(maxsplit=1)
    ref = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    
    try:
        await register_user(message.from_user, ref)
    except Exception as e:
        logger.error(f"Error registering user: {e}")
    
    welcome_text = await get_text(message.from_user.id, "welcome")
    kb = await get_main_reply_kb(message.from_user.id)
    msg = await message.answer(f"🚀 <b>FAST IVAS</b>\n\n{welcome_text}", reply_markup=kb)
    track_msg(message.from_user.id, msg.message_id)

@dp.message(F.text)
async def handle_all_text(message: Message):
    if message.text.startswith('/'): return
    try: await message.delete()
    except: pass

    uid = message.from_user.id
    lang = await get_user_language(uid)
    t = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    text = message.text.strip()

    if text == t["app"] or "📱" in text or "App" in text: await logic_app(message)
    elif text == t["account"] or "👤" in text: await logic_profile(message)
    elif text == t["number1"] or "🎱" in text: await cb_list_countries_internal(uid, message.chat.id)
    elif text == t["number2"] or "📱" in text and "Số" in text: await logic_numbers2(message)
    elif text == t["number3"] or "🔢" in text or "BS" in text: await cb_list_basha_countries_internal(uid, message.chat.id)
    elif text == t["withdraw"] or "💰" in text: await logic_withdraw(message)
    elif text == t["invite"] or "💌" in text: await logic_referral(message)
    elif text == t["stats"] or "📊" in text: await cb_ranges_stats_internal(uid, message.chat.id)
    elif text == t["leaderboard"] or "🏆" in text: await cb_leaderboard_internal(uid, message.chat.id)
    elif text == t["history"] or "📜" in text: await cb_user_orders_history_internal(uid, message.chat.id, page=1)
    elif text == t["wallet"] or "💵" in text: await logic_wallet(message)
    elif text == t["otp_group"] or "📢" in text: await logic_group(message)
    elif text == t["language"] or "🌐" in text: await logic_language(message)
    elif text == t["admin_panel"] or "🛡" in text: await logic_admin(message)
    else:
        welcome_text = await get_text(uid, "welcome")
        kb = await get_main_reply_kb(uid)
        msg = await message.answer(f"🚀 <b>FAST IVAS</b>\n\n{welcome_text}", reply_markup=kb)
        track_msg(uid, msg.message_id)

# =====================================================
# CALLBACK QUERIES
# =====================================================
@dp.callback_query(F.data == "home")
async def cb_home(call: CallbackQuery):
    try: await call.message.delete()
    except: pass
    welcome_text = await get_text(call.from_user.id, "welcome")
    kb = await get_main_reply_kb(call.from_user.id)
    msg = await call.message.answer(f"🚀 <b>FAST IVAS</b>\n\n{welcome_text}", reply_markup=kb)
    track_msg(call.from_user.id, msg.message_id)
    await call.answer()

@dp.callback_query(F.data.startswith("lang_page_"))
async def cb_language_page(call: CallbackQuery):
    page = int(call.data.rsplit("_", 1)[1])
    await call.message.edit_reply_markup(reply_markup=language_picker_kb(max(0, page)))
    await call.answer()

@dp.callback_query(F.data.startswith("lang_set_"))
async def cb_language_set(call: CallbackQuery):
    lang = call.data.replace("lang_set_", "", 1)
    if not await set_user_language(call.from_user.id, lang):
        await call.answer("Language unavailable.", show_alert=True); return
    await call.message.edit_text(f"✅ <b>Language saved!</b>\nVui lòng nhấn /start để làm mới Menu.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Home", callback_data="home")]]))
    await call.answer("Saved!")

# App Dashboard Callbacks (Chuyển hướng)
@dp.callback_query(F.data == "app_np")
async def cb_app_np(call: CallbackQuery):
    await call.answer()
    await logic_numbers2(call.message)
@dp.callback_query(F.data == "app_wallet")
async def cb_app_wallet(call: CallbackQuery):
    await call.answer()
    await logic_withdraw(call.message)
@dp.callback_query(F.data == "app_invite")
async def cb_app_invite(call: CallbackQuery):
    await call.answer()
    await logic_referral(call.message)
@dp.callback_query(F.data == "app_lang")
async def cb_app_lang(call: CallbackQuery):
    await call.answer()
    await logic_language(call.message)

# --- NUMBER PANEL ---
@dp.callback_query(F.data.startswith("np_svc_"))
async def cb_np_service(call: CallbackQuery):
    service_key = call.data.replace("np_svc_", "")
    await call.answer("Đang tải...")
    try: await call.message.edit_text("⏳ <i>Đang tải quốc gia...</i>")
    except: pass
    data, err = await np_api_request("GET", "countries", params={"service": service_key})
    countries = data.get("countries") or data.get("data", {}).get("countries", []) if not err and data else []
        
    if not countries:
        await call.message.edit_text("⚠️ <b>HẾT SỐ</b>\nVui lòng chọn dịch vụ khác.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Quay lại", callback_data="list_np_services")]]))
        return
    buttons = []; row = []
    for c in countries:
        if c.get("count", 0) > 0:
            c_code = c["name"]; c_full = ISO_MAP.get(c_code, c_code)
            row.append(InlineKeyboardButton(text=f"{get_country_flag(c_full)} {c_full} ({c['count']})", callback_data=f"np_cty_{service_key}_{c_code}"))
            if len(row) == 2: buttons.append(row); row = []
    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton(text="⬅️ Quay lại", callback_data="list_np_services")])
    await call.message.edit_text(f"🌍 <b>CHỌN QUỐC GIA</b>\nDịch vụ: <b>{service_key.capitalize()}</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data == "list_np_services")
async def cb_list_np_services(call: CallbackQuery):
    await call.answer()
    data, err = await np_api_request("GET", "services")
    services = data.get("services") or data.get("data", {}).get("services", []) if not err and data else []
    if not services:
        await call.message.edit_text("⚠️ Không thể tải dịch vụ lúc này."); return
    buttons = []; row = []
    for svc in services:
        if svc.get("count", 0) > 0:
            name = svc.get("name", "Unknown"); key = svc.get("key", name)
            row.append(InlineKeyboardButton(text=f"{get_network_icon(name)} {name} ({svc['count']})", callback_data=f"np_svc_{key}"))
            if len(row) == 2: buttons.append(row); row = []
    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")])
    await call.message.edit_text("📱 <b>NUMBER PANEL (NEW)</b>\n\nVui lòng chọn Dịch vụ:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("np_cty_"))
async def cb_np_country(call: CallbackQuery):
    parts = call.data.replace("np_cty_", "").split("_", 1)
    service, country_code = parts[0], parts[1]
    await call.answer("Đang lấy số...")
    
    async def fetch_one():
        data, err = await np_api_request("POST", "request_number", payload={"service": service, "country": country_code})
        if err: return None
        phone = data.get("number"); rid = data.get("id") or phone
        return {"request_id": rid, "phone": phone, "country": country_code, "operator": service} if phone and rid else None
        
    res1 = await fetch_one(); res2 = await fetch_one()
    results = [r for r in [res1, res2] if r]
    if not results:
        await call.message.edit_text(f"⚠️ <b>LỖI LẤY SỐ</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Quay lại", callback_data=f"np_svc_{service}")]]))
        return
    exp = (now() + timedelta(minutes=ORDER_LIFETIME_MINUTES)).isoformat(timespec="seconds")
    
    order_ids = []
    for res in results:
        cur = await db_exec("INSERT INTO orders (user_id, request_id, provider, phone, country, operator, range_code, status, created_at, expires_at, updated_at, msg_id) VALUES (?, ?, 'NP', ?, ?, ?, ?, 'PENDING', ?, ?, ?, ?)", (call.from_user.id, str(res["request_id"]), str(res["phone"]), str(country_code), service, service, now_text(), exp, now_text(), call.message.message_id))
        if cur: order_ids.append(cur)
    
    text = f"✅ <b>Numbers Assigned!</b>\n\n🔧 Service: {service.capitalize()}\n🌍 Country: {get_country_flag(ISO_MAP.get(country_code, country_code))} {ISO_MAP.get(country_code, country_code)}\n\n"
    for i, r in enumerate(results, 1):
        text += f"📱 Number {i}: <code>{r['phone'] if r['phone'].startswith('+') else '+' + r['phone']}</code>\n"
    text += f"\n⚠️ Use within 15 minutes!\n⏳ Waiting for OTP..."
    
    buttons = []
    if results and order_ids: buttons.append([InlineKeyboardButton(text=await get_text(call.from_user.id, "remove_code"), callback_data=f"rm_code_{order_ids[0]}")])
    buttons.append([InlineKeyboardButton(text=await get_text(call.from_user.id, "change_num"), callback_data=f"np_svc_{service}"), InlineKeyboardButton(text="💬 OTP Group", url=OTP_GROUP_URL)])
    cancel_data = f"cancel_multi_{'_'.join(map(str, order_ids))}"
    buttons.append([InlineKeyboardButton(text=await get_text(call.from_user.id, "cancel_order"), callback_data=cancel_data), InlineKeyboardButton(text=await get_text(call.from_user.id, "new_numbers"), callback_data=f"np_svc_{service}")])
    buttons.append([InlineKeyboardButton(text=await get_text(call.from_user.id, "back"), callback_data=f"list_np_services"), InlineKeyboardButton(text=await get_text(call.from_user.id, "main_menu"), callback_data="home")])
    
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

# --- MK NETWORK ---
async def cb_list_countries_internal(uid, chat_id, message_id=None):
    try:
        country_dict = FALLBACK_COUNTRIES.copy(); sorted_countries = sorted(list(country_dict.keys()))[:50]
        buttons = []
        for i in range(0, len(sorted_countries), 2):
            row = []
            c1 = sorted_countries[i]; row.append(InlineKeyboardButton(text=f"{get_country_flag(c1)} {c1}", callback_data=f"rng_{country_dict[c1]}"))
            if i + 1 < len(sorted_countries):
                c2 = sorted_countries[i+1]; row.append(InlineKeyboardButton(text=f"{get_country_flag(c2)} {c2}", callback_data=f"rng_{country_dict[c2]}"))
            buttons.append(row)
        buttons.append([InlineKeyboardButton(text=await get_text(uid, "back"), callback_data="home")])
        if message_id:
            try: await bot.delete_message(chat_id, message_id)
            except: pass
        msg = await bot.send_message(chat_id, await get_text(uid, "select_country"), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        track_msg(chat_id, msg.message_id)
    except Exception as e: logger.error(f"Lỗi tạo bảng quốc gia: {e}")

@dp.callback_query(F.data == "list_countries")
async def cb_list_countries(call: CallbackQuery):
    await call.answer("Loading...")
    await cb_list_countries_internal(call.from_user.id, call.message.chat.id, call.message.message_id)

@dp.callback_query(F.data.startswith("rng_"))
async def cb_choose_range(call: CallbackQuery):
    range_code = call.data.replace("rng_", "")
    await call.answer("Getting numbers...")
    res1 = await create_number_order(call.from_user.id, range_code, msg_id=call.message.message_id)
    res2 = await create_number_order(call.from_user.id, range_code, msg_id=call.message.message_id)
    success_results = [r for ok, r in [res1, res2] if ok]
        
    if not success_results:
        error_msg = res1[1] if not res1[0] else res2[1]
        await call.message.edit_text(f"⚠️ <b>UNABLE TO GET NUMBER</b>\n\n{error_msg}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="list_countries")]])); return
    
    order_ids = []
    for r in success_results:
        row = await db_exec("SELECT id FROM orders WHERE request_id=?", (r['request_id'],), fetch='one')
        if row: order_ids.append(row[0])
    
    c_full = success_results[0]['country']; operator = success_results[0]['operator'].capitalize()
    text = f"✅ <b>Numbers Assigned!</b>\n\n🔧 Service: {operator}\n🌍 Country: {get_country_flag(c_full)} {c_full}\n\n"
    for i, r in enumerate(success_results, 1):
        text += f"📱 Number {i}: <code>{r['phone'] if r['phone'].startswith('+') else '+' + r['phone']}</code>\n"
    text += f"\n⚠️ Use within 15 minutes!\n⏳ Waiting for OTP..."
    
    buttons = []
    if success_results and order_ids: buttons.append([InlineKeyboardButton(text=await get_text(call.from_user.id, "remove_code"), callback_data=f"rm_code_{order_ids[0]}")])
    buttons.append([InlineKeyboardButton(text=await get_text(call.from_user.id, "change_num"), callback_data=f"rng_{range_code}"), InlineKeyboardButton(text="💬 OTP Group", url=OTP_GROUP_URL)])
    cancel_data = f"cancel_multi_{'_'.join(map(str, order_ids))}"
    buttons.append([InlineKeyboardButton(text=await get_text(call.from_user.id, "cancel_order"), callback_data=cancel_data), InlineKeyboardButton(text=await get_text(call.from_user.id, "new_numbers"), callback_data="list_countries")])
    buttons.append([InlineKeyboardButton(text=await get_text(call.from_user.id, "back"), callback_data="list_countries"), InlineKeyboardButton(text=await get_text(call.from_user.id, "main_menu"), callback_data="home")])
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

# --- BASHA FLOW ---
async def cb_list_basha_countries_internal(uid, chat_id, message_id=None):
    try:
        rows = await db_exec("SELECT country, flag, COUNT(*) FROM basha_numbers GROUP BY country, flag", fetch='all')
        if not rows:
            if message_id:
                try: await bot.delete_message(chat_id, message_id)
                except: pass
            msg = await bot.send_message(chat_id, "⚠️ <b>Chưa có số BS nào trong hệ thống.</b>\nVui lòng liên hệ Admin để thêm số.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")]]))
            track_msg(chat_id, msg.message_id); return
        buttons = []; row_btns = []
        for c_name, flag, count in rows:
            row_btns.append(InlineKeyboardButton(text=f"{flag} {c_name} ({count})", callback_data=f"basha_rng_{c_name}"))
            if len(row_btns) == 2: buttons.append(row_btns); row_btns = []
        if row_btns: buttons.append(row_btns)
        
        # Đã thêm nút quay lại
        buttons.append([InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")])
        
        if message_id:
            try: await bot.delete_message(chat_id, message_id)
            except: pass
        msg = await bot.send_message(chat_id, "🔢 <b>BASHA NUMBERS</b>\n\nSelect a country to get a number:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        track_msg(chat_id, msg.message_id)
    except Exception as e: logger.error(f"Lỗi tạo bảng quốc gia Basha: {e}")

@dp.callback_query(F.data == "list_basha_countries")
async def cb_list_basha_countries(call: CallbackQuery):
    await cb_list_basha_countries_internal(call.from_user.id, call.message.chat.id, call.message.message_id); await call.answer()

@dp.callback_query(F.data.startswith("basha_rng_"))
async def cb_choose_basha_range(call: CallbackQuery):
    country = call.data.replace("basha_rng_", ""); await call.answer("Getting numbers...")
    row = await db_exec("SELECT phone, flag FROM basha_numbers WHERE country=? ORDER BY RANDOM() LIMIT 1", (country,), fetch='one')

    if not row:
        await call.message.edit_text("⚠️ Hết số cho quốc gia này.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="list_basha_countries")]])); return
        
    phone, flag = row; exp = (now() + timedelta(minutes=ORDER_LIFETIME_MINUTES)).isoformat(timespec="seconds")
    order_id = await db_exec("INSERT INTO orders (user_id, request_id, provider, phone, country, operator, range_code, status, created_at, expires_at, updated_at, msg_id) VALUES (?, ?, 'BASHA', ?, ?, 'Basha', ?, 'PENDING', ?, ?, ?, ?)", (call.from_user.id, phone, phone, country, country, now_text(), exp, now_text(), call.message.message_id))
    
    text = f"✅ <b>Number Assigned (Basha)!</b>\n\n🔧 Service: Basha API\n🌍 Country: {flag} {country}\n\n📱 Number: <code>{phone if phone.startswith('+') else '+' + phone}</code>\n\n⚠️ Use within 15 minutes!\n⏳ Waiting for OTP..."
    buttons = [[InlineKeyboardButton(text=await get_text(call.from_user.id, "remove_code"), callback_data=f"rm_code_{order_id}")], [InlineKeyboardButton(text=await get_text(call.from_user.id, "change_num"), callback_data=f"basha_rng_{country}"), InlineKeyboardButton(text="💬 OTP Group", url=OTP_GROUP_URL)], [InlineKeyboardButton(text=await get_text(call.from_user.id, "cancel_order"), callback_data=f"cancel_multi_{order_id}"), InlineKeyboardButton(text=await get_text(call.from_user.id, "new_numbers"), callback_data="list_basha_countries")], [InlineKeyboardButton(text=await get_text(call.from_user.id, "back"), callback_data="list_basha_countries"), InlineKeyboardButton(text=await get_text(call.from_user.id, "main_menu"), callback_data="home")]]
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

# --- SHARED CALLBACKS ---
@dp.callback_query(F.data.startswith("rm_code_"))
async def cb_remove_code(call: CallbackQuery):
    order_id = int(call.data.replace("rm_code_", ""))
    row = await db_exec("SELECT country, phone FROM orders WHERE id=?", (order_id,), fetch='one')
    if not row: await call.answer("Order not found", show_alert=True); return
    country, phone = row
    
    clean_phone = phone.lstrip("+")
    for prefix in SORTED_PREFIXES:
        if clean_phone.startswith(prefix): clean_phone = clean_phone[len(prefix):]; break
    clean_phone = clean_phone.lstrip("0")
    
    text = call.message.html_text; old_disp = phone if phone.startswith('+') else f"+{phone}"
    text = text.replace(f"<code>{old_disp}</code>", f"<code>{clean_phone}</code>") if f"<code>{old_disp}</code>" in text else text.replace(old_disp, clean_phone)
    
    # FIX LỖI TẠI ĐÂY: Thêm điều kiện btn.callback_data is not None
    new_kb = []
    for row_kb in call.message.reply_markup.inline_keyboard:
        new_row = []
        for btn in row_kb:
            if btn.callback_data and btn.callback_data.startswith("rm_code_"):
                continue
            new_row.append(btn)
        if new_row: new_kb.append(new_row)
        
    try:
        await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=new_kb)); await call.answer("Removed!")
    except: await call.answer("Error!")

@dp.callback_query(F.data.startswith("cancel_multi_"))
async def cb_cancel_multi(call: CallbackQuery):
    ids = [int(x) for x in call.data.replace("cancel_multi_", "").split("_") if x.isdigit()]
    for oid in ids:
        row = await db_exec("SELECT provider, phone, request_id FROM orders WHERE id=? AND status='PENDING'", (oid,), fetch='one')
        if row:
            if row[0] == "NP": await np_api_request("POST", "release_number", payload={"number": row[1]})
            await db_exec("UPDATE orders SET status='CANCELLED', updated_at=? WHERE id=?", (now_text(), oid))
    await call.answer("Cancelled...")
    try: await call.message.delete()
    except: pass
    msg = await call.message.answer("🚫 Order cancelled successfully.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 Get New Number", callback_data="list_countries")], [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")]]))
    track_msg(call.from_user.id, msg.message_id)

async def cb_ranges_stats_internal(uid, chat_id, message_id=None):
    today_str = now().strftime("%Y-%m-%d")
    db_stats = {}
    rows = await db_exec("SELECT country, COUNT(id) FROM orders WHERE status='COMPLETED' AND created_at >= ? GROUP BY country", (today_str,), fetch='all')
    if rows:
        for r in rows: db_stats[r[0]] = r[1]

    api_networks = {}
    data, err = await api_get("access_list", params={"limit": 50})
    if not err and isinstance(data, dict):
        for item in data.get("data", {}).get("items", []):
            if item.get("country"): api_networks[item.get("country")] = item.get("networks") or []

    text = f"📊 <b>RANGES STATS TODAY</b>\n\nTổng OTP hôm nay: <b>{sum(db_stats.values())}</b>\n──────────────────\n"
    for c_name in sorted(set(list(db_stats.keys()) + list(api_networks.keys()))):
        count = db_stats.get(c_name, 0)
        nets = api_networks.get(c_name, [])
        net_str = f"\n   ↳ <i>Support: {', '.join([f'{get_network_icon(n)} {n.capitalize()}' for n in nets])}</i>" if nets else ""
        text += f"{get_country_flag(c_name)} <b>{c_name}</b>: {count} OTPs{net_str}\n"
    if len(text) > 4000: text = text[:4000] + "\n\n<i>(...)</i>"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📱 Platform Activity", callback_data="platform_stats")], [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")]])
    if message_id:
        try: await bot.delete_message(chat_id, message_id)
        except: pass
    msg = await bot.send_message(chat_id, text, reply_markup=kb)
    track_msg(chat_id, msg.message_id)

@dp.callback_query(F.data == "ranges_stats")
async def cb_ranges_stats(call: CallbackQuery):
    await cb_ranges_stats_internal(call.from_user.id, call.message.chat.id, call.message.message_id); await call.answer()

@dp.callback_query(F.data == "platform_stats")
async def cb_platform_stats(call: CallbackQuery):
    await call.answer("Đang tải...")
    rows = await db_exec("SELECT COALESCE(NULLIF(platform, ''), 'Other') as p, COUNT(id) FROM orders WHERE status='COMPLETED' AND created_at >= ? GROUP BY p ORDER BY COUNT(id) DESC", (now().strftime("%Y-%m-%d"),), fetch='all')
    text = "📱 <b>PLATFORM ACTIVITY (REAL-TIME)</b>\n\n"
    text += f"Tổng OTP hôm nay: <b>{sum(r[1] for r in rows)}</b>\n──────────────────\n" if rows else "Chưa có OTP nào hôm nay."
    if rows:
        for r in rows: text += f"{get_network_icon(r[0])} <b>{r[0].capitalize()}</b>: {r[1]} OTPs\n"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 Làm mới", callback_data="platform_stats")], [InlineKeyboardButton(text="⬅️ Quay lại Stats", callback_data="ranges_stats")]])
    try: await call.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest: pass 

async def cb_leaderboard_internal(uid, chat_id, message_id=None):
    rows = await db_exec("SELECT o.user_id, COUNT(o.id) as otp_count, u.first_name, u.usd_milli, (SELECT COUNT(*) FROM users ref WHERE ref.referrer = o.user_id) as ref_count FROM orders o JOIN users u ON o.user_id = u.user_id WHERE o.status='COMPLETED' AND o.created_at >= ? GROUP BY o.user_id ORDER BY otp_count DESC LIMIT 10", (now().strftime("%Y-%m-%d"),), fetch='all')
    text = "🏆 <b>LEADERBOARD TODAY</b>\n\n"
    text += "No OTPs today." if not rows else "\n".join([f"{i}. <b>{safe(r[2] or f'User {r[0]}')}</b> (<code>{r[0]}</code>)\n   ├ 🔑 OTPs: <b>{r[1]}</b>\n   ├ 💵 Balance: <b>{usd(r[3])}</b>\n   └ 👥 Invites: <b>{r[4]}</b>\n" for i, r in enumerate(rows, 1)])
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")]])
    if message_id:
        try: await bot.delete_message(chat_id, message_id)
        except: pass
    msg = await bot.send_message(chat_id, text, reply_markup=kb)
    track_msg(chat_id, msg.message_id)

@dp.callback_query(F.data == "leaderboard")
async def cb_leaderboard(call: CallbackQuery):
    await cb_leaderboard_internal(call.from_user.id, call.message.chat.id, call.message.message_id); await call.answer()

async def cb_user_orders_history_internal(uid, chat_id, message_id=None, page=1):
    if page < 1: page = 1
    max_page = MAX_HISTORY_RECORDS // HISTORY_PER_PAGE
    if page > max_page: page = max_page
    rows = await get_user_orders(uid, limit=HISTORY_PER_PAGE, offset=(page - 1) * HISTORY_PER_PAGE)
    
    if not rows and page > 1: return await cb_user_orders_history_internal(uid, chat_id, message_id, page - 1)
    if not rows:
        msg = await bot.send_message(chat_id, "Chưa có lịch sử!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")]]))
        track_msg(chat_id, msg.message_id); return
    
    buttons = [[InlineKeyboardButton(text=f"{'✅' if r[6]=='COMPLETED' else '⌛' if r[6]=='EXPIRED' else '🚫' if r[6]=='CANCELLED' else '❌' if r[6]=='FAILED' else '⏳'} {get_country_flag(r[4])} {mask_phone(r[3])} [{'MK' if r[2]=='MK' else 'NP' if r[2]=='NP' else 'BS'}]| {fmt_date(r[7])}", callback_data=f"view_history_{r[0]}")] for r in rows]
    
    nav_row = []
    if page > 1: nav_row.append(InlineKeyboardButton(text="⬅️ Prev", callback_data=f"hist_page_{page-1}"))
    if len(rows) == HISTORY_PER_PAGE and page < max_page: nav_row.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"hist_page_{page+1}"))
    if nav_row: buttons.append(nav_row)
    buttons.append([InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")])
    
    if message_id:
        try: await bot.delete_message(chat_id, message_id)
        except: pass
    msg = await bot.send_message(chat_id, f"📜 <b>RECENT HISTORY (Page {page}/{max_page})</b>\n\nClick a number to view details:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    track_msg(chat_id, msg.message_id)

@dp.callback_query(F.data == "user_orders_history")
async def cb_user_orders_history(call: CallbackQuery):
    await cb_user_orders_history_internal(call.from_user.id, call.message.chat.id, call.message.message_id, page=1); await call.answer()

@dp.callback_query(F.data.startswith("hist_page_"))
async def cb_hist_page(call: CallbackQuery):
    page = int(call.data.replace("hist_page_", ""))
    await cb_user_orders_history_internal(call.from_user.id, call.message.chat.id, call.message.message_id, page=page); await call.answer(f"Page {page}")

# =====================================================
# RÚT TIỀN
# =====================================================
@dp.message(Command("withdraw"))
async def cmd_rut_menu(message: Message):
    try: await message.delete()
    except: pass
    await logic_withdraw(message)

@dp.callback_query(F.data == "wd_menu")
async def cb_wd_menu(call: CallbackQuery):
    u = await get_user(call.from_user.id)
    if not u: return
    text = f"💸 <b>WITHDRAW USD VIA TON</b>\n\nCurrent Balance: <b>{usd(u['usd_milli'])}</b>\nTON Wallet: <code>{u['wallet_ton'] or 'Not set'}</code>\n\nPlease select:"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚙️ Setup TON Wallet", callback_data="wd_setup_addr")], [InlineKeyboardButton(text="💵 Withdraw", callback_data="wd_choose_amount")], [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")]])
    await call.message.edit_text(text, reply_markup=kb); await call.answer()

@dp.callback_query(F.data == "wd_setup_addr")
async def cb_wd_setup_addr(call: CallbackQuery):
    await call.message.edit_text("⚙️ <b>SETUP TON WALLET</b>\n\nPlease send your TON wallet address below.\nExample: <code>UQBfFHeVzZyixLYup3rvCkRaSVJTOc8UtCeqksenDoMxSvOS</code>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="wd_menu")]])); await call.answer()

@dp.message(F.text.regexp(r"^(EQ|UQ)[a-zA-Z0-9_-]{46}$"))
async def handle_wallet_input(message: Message):
    try: await message.delete()
    except: pass
    wallet = message.text.strip(); await set_wallet_ton(message.from_user.id, wallet)
    msg = await message.answer(f"✅ <b>TON WALLET SAVED</b>\n\nYour wallet:\n<code>{wallet}</code>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back to Withdraw", callback_data="wd_menu")]]))
    track_msg(message.from_user.id, msg.message_id)

@dp.callback_query(F.data == "wd_choose_amount")
async def cb_wd_choose_amount(call: CallbackQuery):
    u = await get_user(call.from_user.id)
    if not u or not u["wallet_ton"]: await call.answer("Please setup TON wallet first!", show_alert=True); return
    balance = int(u['usd_milli'])
    buttons = []; row = []
    for i in [1, 2, 4, 6, 8, 10]:
        row.append(InlineKeyboardButton(text=f"${i}", callback_data=f"wd_amt_{i}"))
        if len(row) == 3: buttons.append(row); row = []
    if row: buttons.append(row)
    if balance - 100 >= MIN_WITHDRAW_MILLI: buttons.append([InlineKeyboardButton(text=f"💰 Withdraw All (~{usd(balance - 100)})", callback_data=f"wd_amt_all")])
    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="wd_menu")])
    await call.message.edit_text(f"💵 <b>SELECT AMOUNT TO WITHDRAW</b>\n\nBalance: <b>{usd(balance)}</b>\n\n<i>(* Note: Withdraw All applies a ~$0.1 TON network fee)</i>", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)); await call.answer()

@dp.callback_query(F.data.startswith("wd_amt_"))
async def cb_wd_amt(call: CallbackQuery):
    u = await get_user(call.from_user.id)
    if not u: return
    balance = int(u["usd_milli"])
    if call.data == "wd_amt_all":
        amt_milli = balance - 100; amt_usd = 0
        if amt_milli < MIN_WITHDRAW_MILLI: await call.answer("Insufficient after fee!", show_alert=True); return
        text_amt = f"All {usd(amt_milli)} (after fee)"
    else:
        amt_usd = int(call.data.replace("wd_amt_", "")); amt_milli = amt_usd * 1000
        if balance < amt_milli: await call.answer(f"Insufficient!", show_alert=True); return
        text_amt = f"${amt_usd}.000"
    
    callback_conf = "wd_conf_all" if call.data == "wd_amt_all" else f"wd_conf_{amt_usd}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Confirm", callback_data=callback_conf)], [InlineKeyboardButton(text="❌ Cancel", callback_data="wd_choose_amount")]])
    await call.message.edit_text(f"⚠️ <b>CONFIRM WITHDRAWAL</b>\n\nWithdraw <b>{text_amt}</b> to:\n<code>{u['wallet_ton']}</code>?\n\n<i>(Funds will be deducted immediately)</i>", reply_markup=kb); await call.answer()

@dp.callback_query(F.data.startswith("wd_conf_"))
async def cb_wd_conf(call: CallbackQuery):
    u = await get_user(call.from_user.id)
    if not u: return
    balance = int(u["usd_milli"])
    if call.data == "wd_conf_all": amt_milli = balance - 100
    else: amt_milli = int(call.data.replace("wd_conf_", "")) * 1000
    
    ok, new_usd = await change_usd(call.from_user.id, -amt_milli, "WITHDRAW_HOLD", "TON Withdrawal Request")
    if not ok: await call.answer(safe(new_usd), show_alert=True); return
    wid = await create_withdrawal(call.from_user.id, amt_milli, u["wallet_ton"])
    await call.message.edit_text(f"✅ <b>WITHDRAWAL CREATED</b>\n\nID: <code>#{wid}</code>\nAmount: <b>{usd(amt_milli)}</b>\nTON Wallet: <code>{u['wallet_ton']}</code>\nRemaining: <b>{usd(new_usd)}</b>\n\nPlease wait for Admin approval.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")]]))
    try:
        pending_count = await db_exec("SELECT COUNT(*) FROM withdrawals WHERE status='PENDING'", fetch='one')
        admin_msg = await bot.send_message(ADMIN_ID, f"🔔 <b>WITHDRAWAL NOTIFICATION</b>\n\nThere are <b>{pending_count[0] if pending_count else 0}</b> pending withdrawals.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👉 Process Now", callback_data="admin_withdraws")]]))
        track_msg(ADMIN_ID, admin_msg.message_id)
    except Exception as e: logger.error(f"Error notifying admin: {e}")
    await call.answer("Withdrawal created!")

@dp.callback_query(F.data.startswith("refresh_order_"))
async def cb_refresh_order(call: CallbackQuery):
    oid = int(call.data.replace("refresh_order_", "")); row = await get_order(oid, call.from_user.id)
    if not row: await call.answer("Order not found!", show_alert=True); return
    await call.answer("Checking...")
    if row["status"] == "COMPLETED":
        text = f"✅ <b>OTP RECEIVED</b>\n\nNumber: <code>{row['phone']}</code>\nCountry: {safe(row['country'])}\nOTP: <code>{safe(row['otp_code'])}</code>"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📜 History", callback_data="user_orders_history")], [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home")]])
    elif row["status"] == "EXPIRED":
        text = f"⌛ <b>EXPIRED</b>\n\nNumber: <code>{row['phone']}</code>"; kb = order_status_kb()
    else:
        text = f"⏳ <b>WAITING FOR OTP</b>\n\nNumber: <code>{row['phone']}</code>\nExpires: {safe(row['expires_at'])}"; kb = order_status_kb(oid)
    await call.message.edit_text(text, reply_markup=kb)

@dp.callback_query(F.data.startswith("view_history_"))
async def cb_view_history(call: CallbackQuery):
    oid = int(call.data.replace("view_history_", "")); row = await get_order(oid, call.from_user.id)
    if not row: await call.answer("Not found!", show_alert=True); return
    provider_tag = "MK" if row.get("provider") == "MK" else "NP" if row.get("provider") == "NP" else "BS"
    text = f"📦 <b>ORDER DETAILS #{oid}</b> ({provider_tag})\n\nNumber: <code>{safe(row['phone'])}</code>\nCountry: {safe(row['country'])}\nStatus: <b>{status_text(row['status'])}</b>\nCreated: {fmt_date(row.get('created_at'))}\nExpires: {fmt_date(row.get('expires_at'))}\n"
    if row["status"] == "COMPLETED" and row.get("otp_code"):
        text += f"\n🔑 <b>OTP:</b> <code>{safe(row['otp_code'])}</code>\n💬 {safe(row.get('full_sms'))}"
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="user_orders_history")]])); await call.answer()

# =====================================================
# ADMIN PANEL
# =====================================================
@dp.callback_query(F.data == "admin_menu")
async def cb_admin_menu(call: CallbackQuery):
    if not is_admin(call.from_user.id): await call.answer("Access denied.", show_alert=True); return
    try: await call.message.edit_text("🛡 <b>ADMIN PANEL</b>", reply_markup=admin_kb())
    except: pass
    await call.answer()

@dp.callback_query(F.data == "admin_cmds")
async def cb_admin_cmds(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    await call.message.edit_text("🛠 <b>ADMIN COMMANDS</b>", reply_markup=admin_cmds_kb()); await call.answer()

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
            await msg.edit_text(f"⚠️ API Error: {err}" if err else f"✅ Checked: {c} · New OTPs: {n}")
        except Exception as e: await msg.edit_text(f"❌ {safe(str(e))}")
    elif cmd == "health":
        pending = await db_exec("SELECT COUNT(*) FROM orders WHERE status='PENDING'", fetch='one')
        poller = "OFF" if not _mk_poller else f"ON ({_mk_poller.interval}s, err={_mk_poller._consecutive_errors})"
        text = f"🟢 <b>FAST IVAS ONLINE</b>\n\nDB: <code>Turso Cloud</code>\nMK Key: {'✓' if MK_API_KEY else '✗'}\nNP Key: {'✓' if NP_API_KEY else '✗'}\nBasha Key: {'✓' if BASHA_API_KEY else '✗'}\nPending Orders: <b>{pending[0] if pending else 0}</b>\nPoller: {safe(poller)}\nReward/OTP: <b>{usd(REWARD_MILLI_PER_OTP)}</b>"
        await call.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="admin_menu")]]))
    elif cmd == "whoami":
        data, err = await api_get("whoami"); await call.message.answer(f"❌ {safe(err)}" if err else f"📊 <b>MK ACCOUNT</b>\n\n<pre>{fmt_api(data)}</pre>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="admin_menu")]]))
    elif cmd == "testnp":
        msg = await call.message.answer("🔄 Đang test API Number Panel...")
        data, err = await np_api_request("GET", "services")
        await msg.edit_text(f"❌ <b>LỖI KẾT NỐI NP</b>\n\nLỗi trả về: <code>{err}</code>" if err else f"✅ <b>KẾT NỐI NP THÀNH CÔNG</b>\n\n<pre>{safe(json.dumps(data, indent=2, ensure_ascii=False), 3500)}</pre>")
        return
    await call.answer()

# QUẢN LÝ SỐ BS
@dp.callback_query(F.data == "admin_manage_bs")
async def cb_admin_manage_bs(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    rows = await db_exec("SELECT country, flag, COUNT(*) FROM basha_numbers GROUP BY country, flag", fetch='all')
    if not rows:
        await call.message.edit_text("⚠️ Database trống. Không có số BS nào.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="admin_menu")]]))
        await call.answer(); return

    buttons = []; row_btns = []
    for c_name, flag, count in rows:
        row_btns.append(InlineKeyboardButton(text=f"{flag} {c_name} ({count})", callback_data=f"adm_bs_cty_{c_name}"))
        if len(row_btns) == 2: buttons.append(row_btns); row_btns = []
    if row_btns: buttons.append(row_btns)
    
    buttons.append([InlineKeyboardButton(text="🚨 XÓA TOÀN BỘ SỐ BS", callback_data="adm_bs_del_all")])
    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="admin_menu")])
    await call.message.edit_text("⚙️ <b>QUẢN LÝ SỐ BS</b>\n\nChọn quốc gia để quản lý hoặc xóa toàn bộ:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await call.answer()

@dp.callback_query(F.data.startswith("adm_bs_cty_"))
async def cb_adm_bs_country(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    country = call.data.replace("adm_bs_cty_", "")
    count = await db_exec("SELECT COUNT(*) FROM basha_numbers WHERE country=?", (country,), fetch='one')
    
    text = f"🌍 <b>QUỐC GIA: {country.upper()}</b>\n\nTổng số đang có: <b>{count[0] if count else 0}</b>\n\nBạn có chắc chắn muốn xóa toàn bộ số của quốc gia này không?"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🗑 XÓA TOÀN BỘ {country.upper()}", callback_data=f"adm_bs_del_{country}")],
        [InlineKeyboardButton(text="⬅️ Quay lại", callback_data="admin_manage_bs")]
    ])
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()

@dp.callback_query(F.data.startswith("adm_bs_del_"))
async def cb_adm_bs_del(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    if call.data == "adm_bs_del_all":
        await db_exec("DELETE FROM basha_numbers")
        msg_text = "🚨 <b>ĐÃ XÓA TOÀN BỘ SỐ BS TRONG HỆ THỐNG!</b>"
    else:
        country = call.data.replace("adm_bs_del_", "")
        await db_exec("DELETE FROM basha_numbers WHERE country=?", (country,))
        msg_text = f"🗑 <b>ĐÃ XÓA TOÀN BỘ SỐ CỦA {country.upper()}!</b>"
        
    await call.message.edit_text(msg_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Quay lại", callback_data="admin_manage_bs")]]))
    await call.answer("Đã xóa!")

# HÀM XỬ LÝ THÊM SỐ BASHA CHUNG
async def process_basha_numbers(message: Message, text_data: str):
    raw_text = text_data.replace(",", "\n")
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    added, dup, invalid = 0, 0, 0
    
    wait_msg = await message.answer(f"⏳ Đang xử lý {len(lines)} số...")
    
    for phone in lines:
        clean = phone.lstrip('+').strip()
        if not clean.isdigit() or len(clean) < 7: invalid += 1; continue
        country, flag = detect_country_from_phone(clean)
        if country == "Unknown": invalid += 1; continue
        
        # Kiểm tra tồn tại trước khi thêm
        exists = await db_exec("SELECT id FROM basha_numbers WHERE phone=?", (clean,), fetch='one')
        if exists:
            dup += 1
        else:
            res = await db_exec("INSERT INTO basha_numbers (phone, country, flag, added_at) VALUES (?, ?, ?, ?)", (clean, country, flag, now_text()))
            if res: added += 1
            else: invalid += 1
            
    await wait_msg.delete()
    msg = await message.answer(f"✅ <b>Hoàn tất!</b>\n\nThêm thành công: <b>{added}</b>\nBị trùng: <b>{dup}</b>\nKhông hợp lệ: <b>{invalid}</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Về Admin Panel", callback_data="admin_menu")]]))
    track_msg(message.from_user.id, msg.message_id)

@dp.callback_query(F.data == "admin_add_bs")
async def cb_admin_add_bs(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    ADMIN_PENDING_APPROVE[ADMIN_ID] = {"step": "waiting_basha_numbers"}
    text = "➕ <b>THÊM SỐ BASHA (BS)</b>\n\nVui lòng gửi danh sách số điện thoại (Mỗi số 1 dòng hoặc cách nhau bằng dấu phẩy).\nHoặc bro có thể <b>Gửi File .txt</b> chứa danh sách số.\n\nVí dụ:\n<code>84987654321, 628123456789</code>"
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Hủy", callback_data="admin_menu")]])); await call.answer()

@dp.message(F.document)
async def handle_basha_file(message: Message):
    if not is_admin(message.from_user.id): return
    state = ADMIN_PENDING_APPROVE.get(ADMIN_ID)
    if not state or state.get("step") != "waiting_basha_numbers": return
    
    if not message.document.file_name.endswith('.txt'):
        await message.answer("⚠️ Vui lòng gửi file định dạng <b>.txt</b>.")
        return
        
    ADMIN_PENDING_APPROVE.pop(ADMIN_ID, None)
    wait_msg = await message.answer("⏳ Đang tải file...")
    
    try:
        file_info = await bot.get_file(message.document.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        content = downloaded_file.read().decode('utf-8')
        await wait_msg.delete()
        await process_basha_numbers(message, content)
    except Exception as e:
        await wait_msg.delete()
        await message.answer(f"❌ Lỗi đọc file: {e}")

@dp.message(F.text.regexp(r"^[0-9\+\s\,\n]+$"))
async def handle_add_basha_numbers(message: Message):
    if not is_admin(message.from_user.id): return
    state = ADMIN_PENDING_APPROVE.get(ADMIN_ID)
    if not state or state.get("step") != "waiting_basha_numbers": return
    ADMIN_PENDING_APPROVE.pop(ADMIN_ID, None)
    await process_basha_numbers(message, message.text)

@dp.callback_query(F.data == "admin_stats")
async def cb_admin_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    await expire_old_orders()
    users = await db_exec("SELECT COUNT(*) FROM users", fetch='one')
    tot_usd = await db_exec("SELECT COALESCE(SUM(usd_milli),0) FROM users", fetch='one')
    orders = await db_exec("SELECT COUNT(*) FROM orders", fetch='one')
    pending = await db_exec("SELECT COUNT(*) FROM orders WHERE status='PENDING'", fetch='one')
    completed = await db_exec("SELECT COUNT(*) FROM orders WHERE status='COMPLETED'", fetch='one')
    wd = await db_exec("SELECT COUNT(*) FROM withdrawals WHERE status='PENDING'", fetch='one')
    bs_count = await db_exec("SELECT COUNT(*) FROM basha_numbers", fetch='one')
    
    text = f"📊 <b>STATISTICS</b>\n\n👥 Users: <b>{users[0] if users else 0}</b>\n📦 Orders: <b>{orders[0] if orders else 0}</b> (pending <b>{pending[0] if pending else 0}</b>, completed <b>{completed[0] if completed else 0}</b>)\n💵 Total USD: <b>{usd(tot_usd[0] if tot_usd else 0)}</b>\n💸 Pending Withdrawals: <b>{wd[0] if wd else 0}</b>\n🔢 BS Numbers in DB: <b>{bs_count[0] if bs_count else 0}</b>"
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="admin_menu")]]))
    await call.answer()

@dp.callback_query(F.data == "admin_users")
async def cb_admin_users(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    users = await db_exec("SELECT joined_at, user_id, first_name FROM users ORDER BY joined_at DESC LIMIT 50", fetch='all')
    if not users: await call.message.edit_text("No users yet.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="admin_menu")]]))
    else:
        buttons = [[InlineKeyboardButton(text=f"👤 {name} ({uid})", callback_data=f"adm_u_{uid}")] for joined, uid, name in users]
        buttons.append([InlineKeyboardButton(text="🗑 Clear Chat History", callback_data="admin_clear_chat")])
        buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="admin_menu")])
        await call.message.edit_text("👥 <b>USER LIST</b>\n\nClick a user:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await call.answer()

@dp.callback_query(F.data == "admin_clear_chat")
async def cb_admin_clear_chat(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    try: await call.message.delete(); await call.message.answer("🗑 Chat history cleared.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back to Admin", callback_data="admin_menu")]]))
    except Exception: pass
    await call.answer("Cleared!")

@dp.callback_query(F.data == "admin_orders")
async def cb_admin_orders(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    rows = await get_all_orders()
    text = "No orders." if not rows else "\n\n".join([f"#{r[0]} | User <code>{r[1]}</code>\nRequest: <code>{safe(r[2])}</code>\nNumber: <code>{safe(r[3])}</code>\nStatus: {safe(r[4])}" for r in rows])
    await call.message.edit_text(f"📦 <b>RECENT ORDERS</b>\n\n{text}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="admin_menu")]])); await call.answer()

@dp.callback_query(F.data == "admin_withdraws")
async def cb_admin_withdraws(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    rows = await db_exec("SELECT w.id, w.user_id, w.amount_milli, w.wallet_ton, u.first_name FROM withdrawals w JOIN users u ON w.user_id = u.user_id WHERE w.status='PENDING' ORDER BY w.id DESC LIMIT 15", fetch='all')
    if not rows: await call.message.edit_text("No pending withdrawals.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="admin_menu")]]))
    else:
        buttons = [[InlineKeyboardButton(text=f"{i}. {name} - {usd(amt)}", callback_data=f"wd_admin_view_{rid}")] for i, (rid, uid, amt, wallet, name) in enumerate(rows, 1)]
        buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="admin_menu")])
        await call.message.edit_text("💸 <b>PENDING WITHDRAWALS</b>\n\nClick a User:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await call.answer()

@dp.callback_query(F.data == "admin_withdraws_history")
async def cb_admin_withdraws_history(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    rows = await db_exec("SELECT w.id, w.user_id, w.amount_milli, w.status, w.processed_at, w.reject_reason, u.first_name FROM withdrawals w JOIN users u ON w.user_id = u.user_id WHERE w.status IN ('APPROVED', 'REJECTED') ORDER BY w.processed_at DESC LIMIT 20", fetch='all')
    text = "No history." if not rows else "\n".join([f"{'✅' if status == 'APPROVED' else '❌'} <b>Order #{rid}</b> | {p_at[:16] if p_at else ''}\n👤 {name} (<code>{uid}</code>)\n💵 {usd(amt)}{f' - Reason: {reason}' if reason else ''}\n" for rid, uid, amt, status, p_at, reason, name in rows])
    await call.message.edit_text(f"📜 <b>APPROVAL HISTORY</b>\n\n{text}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🗑 Clear History", callback_data="admin_clear_history")], [InlineKeyboardButton(text="⬅️ Back", callback_data="admin_menu")]]))
    await call.answer()

@dp.callback_query(F.data == "admin_clear_history")
async def cb_admin_clear_history(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    try: await call.message.delete(); await call.message.answer("🗑 History cleared.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="admin_menu")]]))
    except Exception: pass
    await call.answer("Cleared!")

@dp.callback_query(F.data.startswith("adm_u_"))
async def cb_adm_user_detail(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    uid = int(call.data.replace("adm_u_", "")); u = await get_user(uid)
    if not u: await call.answer("User not found.", show_alert=True); return
    counts = await db_exec("SELECT provider, COUNT(*) FROM orders WHERE user_id=? GROUP BY provider", (uid,), fetch='all')
    mk = next((c[1] for c in counts if c[0] == "MK"), 0) if counts else 0
    np = next((c[1] for c in counts if c[0] == "NP"), 0) if counts else 0
    bs = next((c[1] for c in counts if c[0] == "BASHA"), 0) if counts else 0

    text = f"👤 <b>USER DETAILS</b>\n\nID: <code>{uid}</code>\nName: {safe(u['first_name'])}\nUsername: @{safe(u['username'] or '—')}\nJoined: <b>{fmt_date_full(u['joined_at'])}</b>\nBalance: <b>{usd(u['usd_milli'])}</b>\n🎱 Numbers 1: <b>{mk}</b> | 📱 Numbers 2: <b>{np}</b> | 🔢 BS: <b>{bs}</b>\n\n👇 Choose action:"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="➕ Add Balance", callback_data=f"adm_cong_help_{uid}")], [InlineKeyboardButton(text="➖ Deduct Balance", callback_data=f"adm_tru_help_{uid}")], [InlineKeyboardButton(text="📜 Numbers History", callback_data=f"adm_numhist_{uid}_0")], [InlineKeyboardButton(text="⬅️ Back", callback_data="admin_users")]])
    await call.message.edit_text(text, reply_markup=kb); await call.answer()

@dp.callback_query(F.data.startswith("adm_numhist_"))
async def cb_adm_numbers_history(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    try:
        _, _, uid_text, page_text = call.data.split("_", 3)
        uid, page = int(uid_text), max(0, int(page_text))
    except: await call.answer("Invalid!", show_alert=True); return

    await expire_old_orders(); per_page = 6
    total = await db_exec("SELECT COUNT(*) FROM orders WHERE user_id=?", (uid,), fetch='one')
    rows = await db_exec("SELECT id, request_id, provider, phone, country, status, created_at, expires_at, updated_at, platform FROM orders WHERE user_id=? ORDER BY id DESC LIMIT ? OFFSET ?", (uid, per_page, page * per_page), fetch='all')

    if not total or total[0] == 0: body = f"📜 <b>NUMBERS HISTORY</b>\nUser ID: <code>{uid}</code>\n\nNo orders."
    else:
        lines = [f"📜 <b>NUMBERS HISTORY</b>\nUser ID: <code>{uid}</code>\nTotal: <b>{total[0]}</b>\n"]
        for oid, request_id, provider, phone, country, status, created, expires, updated, platform in rows:
            source = "🎱 Numbers 1 (MK)" if provider == "MK" else "📱 Numbers 2 (NP)" if provider == "NP" else "🔢 BS (Basha)"
            lines.append(f"<b>Order #{oid}</b> | {status_text(status or 'UNKNOWN')}\nNguồn: <b>{source}</b>{f'\nPlatform: {safe(platform)}' if platform else ''}\nNumber: <code>{safe(mask_phone(phone) or '—')}</code>\nCountry: {safe(country or '—')}\nRequest ID: <code>{safe(request_id or '—')}</code>\nCreated: {safe(fmt_date(created))}\nExpires: {safe(fmt_date(expires))}\nStatus updated: {safe(fmt_date(updated))}")
        body = "\n\n".join(lines)

    nav = []
    if page > 0: nav.append(InlineKeyboardButton(text="⬅️ Newer", callback_data=f"adm_numhist_{uid}_{page-1}"))
    if (page + 1) * per_page < total[0]: nav.append(InlineKeyboardButton(text="Older ➡️", callback_data=f"adm_numhist_{uid}_{page+1}"))
    buttons = [nav] if nav else []
    buttons.append([InlineKeyboardButton(text="⬅️ Back to User Details", callback_data=f"adm_u_{uid}")])
    await call.message.edit_text(body, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)); await call.answer()

@dp.callback_query(F.data.startswith("adm_cong_help_"))
async def cb_adm_cong_help(call: CallbackQuery):
    uid = call.data.replace("adm_cong_help_", "")
    await call.message.edit_text(f"➕ <b>ADD BALANCE</b>\n\nType in chat:\n<code>/addbal {uid} 10$</code>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data=f"adm_u_{uid}")]])); await call.answer()

@dp.callback_query(F.data.startswith("adm_tru_help_"))
async def cb_adm_tru_help(call: CallbackQuery):
    uid = call.data.replace("adm_tru_help_", "")
    await call.message.edit_text(f"➖ <b>DEDUCT BALANCE</b>\n\nType in chat:\n<code>/deductbal {uid} 10$</code>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data=f"adm_u_{uid}")]])); await call.answer()

@dp.callback_query(F.data.startswith("wd_admin_view_"))
async def cb_wd_admin_view(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    wid = int(call.data.replace("wd_admin_view_", ""))
    row = await db_exec("SELECT w.id, w.user_id, w.amount_milli, w.wallet_ton, w.status, u.first_name FROM withdrawals w JOIN users u ON w.user_id = u.user_id WHERE w.id=?", (wid,), fetch='one')
    if not row or row[4] != "PENDING": await call.answer("Processed!", show_alert=True); return
    rid, uid, amt, wallet, status, name = row
    text = f"💸 <b>WITHDRAWAL REQUEST</b>\n\n👤 User: <b>{name}</b> (<code>{uid}</code>)\n💵 Amount: <b>{usd(amt)}</b>\n🔗 TON Wallet: <code>{wallet}</code>\n\n👇 Choose action:"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Approve", callback_data=f"wd_approve_step1_{rid}")], [InlineKeyboardButton(text="⏳ Later", callback_data="admin_withdraws")], [InlineKeyboardButton(text="❌ Reject", callback_data=f"wd_reject_list_{rid}")]])
    await call.message.edit_text(text, reply_markup=kb); await call.answer()

@dp.callback_query(F.data.startswith("wd_approve_step1_"))
async def cb_wd_approve_step1(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    wid = int(call.data.replace("wd_approve_step1_", "")); ADMIN_PENDING_APPROVE[ADMIN_ID] = {"wid": wid, "step": "waiting_link"}
    await call.message.edit_text("🔗 <b>ADD TX HASH</b>\n\nPlease send the <b>TON Transaction Link</b> to this chat.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data=f"wd_admin_view_{wid}")]])); await call.answer()

@dp.message(F.text.regexp(r"^https?://"))
async def handle_admin_tx_hash(message: Message):
    if not is_admin(message.from_user.id): return
    state = ADMIN_PENDING_APPROVE.get(ADMIN_ID)
    if not state or state["step"] != "waiting_link": return
    wid = state["wid"]; state["tx_hash"] = message.text.strip(); state["step"] = "confirm_link"; ADMIN_PENDING_APPROVE[ADMIN_ID] = state
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Confirm", callback_data="wd_confirm_link")], [InlineKeyboardButton(text="❌ Cancel", callback_data=f"wd_admin_view_{wid}")]])
    msg = await message.answer(f"🔗 <b>CONFIRM TX HASH</b>\n\nLink: <code>{safe(state['tx_hash'])}</code>", reply_markup=kb)
    track_msg(message.from_user.id, msg.message_id)

@dp.callback_query(F.data == "wd_confirm_link")
async def cb_wd_confirm_link(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    state = ADMIN_PENDING_APPROVE.get(ADMIN_ID)
    if not state or state["step"] != "confirm_link": return
    wid = state["wid"]; state["step"] = "waiting_photo"; ADMIN_PENDING_APPROVE[ADMIN_ID] = state
    await call.message.edit_text("🖼 <b>ADD PROOF PHOTO</b>\n\nPlease send a <b>Photo of the receipt</b> to this chat.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data=f"wd_admin_view_{wid}")]])); await call.answer()

@dp.message(F.photo)
async def handle_admin_photo(message: Message):
    if not is_admin(message.from_user.id): return
    state = ADMIN_PENDING_APPROVE.get(ADMIN_ID)
    if not state or state["step"] != "waiting_photo": return
    wid = state["wid"]; state["photo_id"] = message.photo[-1].file_id; state["step"] = "confirm_photo"; ADMIN_PENDING_APPROVE[ADMIN_ID] = state
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Confirm Approval", callback_data="wd_confirm_photo")], [InlineKeyboardButton(text="❌ Cancel", callback_data=f"wd_admin_view_{wid}")]])
    msg = await message.answer_photo(state["photo_id"], caption=f"🖼 <b>CONFIRM PROOF</b>\n\nSend bill to User for order <code>#{wid}</code>?", reply_markup=kb)
    track_msg(message.from_user.id, msg.message_id)

@dp.callback_query(F.data == "wd_confirm_photo")
async def cb_wd_confirm_photo(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    state = ADMIN_PENDING_APPROVE.get(ADMIN_ID)
    if not state or state["step"] != "confirm_photo": return
    wid, tx_hash, photo_id = state["wid"], state["tx_hash"], state["photo_id"]; ADMIN_PENDING_APPROVE.pop(ADMIN_ID, None)
    
    await db_exec("UPDATE withdrawals SET status='APPROVED', processed_at=?, tx_hash=?, proof_photo=? WHERE id=?", (now_text(), tx_hash, photo_id, wid))
    row = await db_exec("SELECT user_id, amount_milli, wallet_ton FROM withdrawals WHERE id=?", (wid,), fetch='one')
    if not row: await call.answer("Lỗi dữ liệu!", show_alert=True); return
    uid, amt, wallet = row
    
    text = f"🎉 <b>WITHDRAWAL SUCCESSFUL</b> 🎉\n\nWithdrawal of <b>{usd(amt)}</b> approved.\nWallet: <code>{wallet}</code>\n"
    if tx_hash: text += f"TX: <code>{tx_hash}</code>\n<a href='{tx_hash if tx_hash.startswith('http') else f'https://tonscan.org/tx/{tx_hash}'}'>👉 View on Tonscan</a>\n"
    try: await bot.send_photo(uid, photo_id, caption=text)
    except Exception as e: logger.error(f"Error: {e}")
    await call.message.edit_text(f"✅ Approved order #{wid} and sent bill."); await call.answer("Approved!")

@dp.callback_query(F.data.startswith("wd_reject_list_"))
async def cb_wd_reject_list(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    wid = int(call.data.replace("wd_reject_list_", ""))
    reasons = [("Wrong TON Address", "wrong_wallet"), ("Unsupported TON Network", "wrong_network"), ("Suspected Fraud", "fraud"), ("Wrong Amount", "wrong_amount"), ("Other", "other")]
    buttons = [[InlineKeyboardButton(text=r[0], callback_data=f"wd_reject_conf_{wid}_{r[1]}")] for r in reasons]
    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data=f"wd_admin_view_{wid}")])
    await call.message.edit_text(f"❌ <b>SELECT REJECTION REASON FOR #{wid}</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)); await call.answer()

@dp.callback_query(F.data.startswith("wd_reject_conf_"))
async def cb_wd_reject_conf(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    parts = call.data.replace("wd_reject_conf_", "").split("_"); wid = int(parts[0]); reason_code = parts[1]
    reason_text = {"wrong_wallet": "Wrong TON Address", "wrong_network": "Unsupported TON Network", "fraud": "Suspected Fraud", "wrong_amount": "Wrong Amount", "other": "Other"}.get(reason_code, "Unknown")
    row = await db_exec("SELECT user_id, amount_milli FROM withdrawals WHERE id=? AND status='PENDING'", (wid,), fetch='one')
    if not row: await call.answer("Error!", show_alert=True); return
    uid, amt = row
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔥 CONFIRM CANCEL & REFUND", callback_data=f"wd_reject_final_{wid}_{reason_code}")], [InlineKeyboardButton(text="⬅️ Back", callback_data=f"wd_admin_view_{wid}")]])
    await call.message.edit_text(f"⚠️ <b>CONFIRM CANCEL</b>\n\nReject <code>#{wid}</code>.\nRefund: <b>{usd(amt)}</b>.\nReason: <b>{reason_text}</b>", reply_markup=kb); await call.answer()

@dp.callback_query(F.data.startswith("wd_reject_final_"))
async def cb_wd_reject_final(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    parts = call.data.replace("wd_reject_final_", "").split("_"); wid = int(parts[0]); reason_code = parts[1]
    reason_text = {"wrong_wallet": "Wrong TON Address", "wrong_network": "Unsupported TON Network", "fraud": "Suspected Fraud", "wrong_amount": "Wrong Amount", "other": "Other"}.get(reason_code, "Unknown")
    
    def _tx():
        db = get_db()
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT user_id, amount_milli, status FROM withdrawals WHERE id=?", (wid,)).fetchone()
            if not row or row[2] != "PENDING": db.rollback(); return False, "Processed", None
            uid, amt = row[0], row[1]
            db.execute("UPDATE withdrawals SET status='REJECTED', processed_at=?, reject_reason=? WHERE id=?", (now_text(), reason_text, wid))
            db.execute("UPDATE users SET usd_milli=usd_milli+? WHERE user_id=?", (amt, uid))
            db.execute("INSERT INTO transactions (user_id, amount, tx_type, note, created_at) VALUES (?, ?, 'WITHDRAW_REFUND', ?, ?)", (uid, amt, f"Refund #{wid}: {reason_text}", now_text()))
            db.commit()
            return True, amt, uid
        except Exception as e:
            db.rollback(); return False, str(e), None
        finally: db.close()
    
    ok, amt, uid = await asyncio.to_thread(_tx) if hasattr(asyncio, 'to_thread') else await asyncio.get_running_loop().run_in_executor(None, _tx)
    if not ok: await call.answer(amt, show_alert=True); return
    
    await call.message.edit_text(call.message.text + "\n\n❌ <b>CANCELLED AND REFUNDED</b>"); await call.answer("Cancelled")
    try: await bot.send_message(uid, f"❌ <b>WITHDRAWAL REJECTED</b>\n\nOrder <code>#{wid}</code> was cancelled.\nReason: <b>{reason_text}</b>\nRefunded <b>{usd(amt)}</b>.")
    except: pass

@dp.message(Command("addbal"))
async def cmd_congtien(message: Message):
    try: await message.delete()
    except: pass
    if not is_admin(message.from_user.id): return
    parts = message.text.split()
    if len(parts) != 3 or not parts[1].isdigit(): await message.answer("Usage: <code>/addbal ID AMOUNT</code>"); return
    uid = int(parts[1]); amt = int(float(parts[2].replace("$","")) * 1000)
    if amt <= 0: await message.answer("Amount must be > 0."); return
    if not await get_user(uid): await message.answer("User not found."); return
    
    tid = await db_exec("INSERT INTO transactions (user_id, amount, tx_type, note, created_at) VALUES (?, ?, 'PENDING_ADD', 'Waiting for user confirmation', ?)", (uid, amt, now_text()))
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Receive Now", callback_data=f"acc_recv_{tid}"), InlineKeyboardButton(text="❌ Cancel", callback_data=f"acc_cancel_{tid}")]])
    try:
        await bot.send_message(uid, f"🎁 <b>YOU RECEIVED MONEY!</b>\n\nAdmin added <b>{usd(amt)}</b>.", reply_markup=kb); await message.answer(f"✅ Sent request to {uid}.")
    except Exception as e: await message.answer(f"❌ Error: {e}")

@dp.callback_query(F.data.startswith("acc_recv_"))
async def cb_acc_recv(call: CallbackQuery):
    tid = int(call.data.replace("acc_recv_", ""))
    def _tx():
        db = get_db()
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT user_id, amount, tx_type FROM transactions WHERE id=?", (tid,)).fetchone()
            if not row or row[2] != "PENDING_ADD": db.rollback(); return False, None, None
            uid, amt, _ = row
            db.execute("UPDATE transactions SET tx_type='ADMIN_ADD' WHERE id=?", (tid,))
            db.execute("UPDATE users SET usd_milli=usd_milli+? WHERE user_id=?", (amt, uid))
            db.commit()
            return True, amt, uid
        except:
            db.rollback(); return False, None, None
        finally: db.close()
        
    ok, amt, uid = await asyncio.to_thread(_tx) if hasattr(asyncio, 'to_thread') else await asyncio.get_running_loop().run_in_executor(None, _tx)
    if not ok: await call.answer("Error!", show_alert=True); return
    await call.message.edit_text(f"✅ Successfully received <b>{usd(amt)}</b>."); await call.answer("Received")

@dp.callback_query(F.data.startswith("acc_cancel_"))
async def cb_acc_cancel(call: CallbackQuery):
    tid = int(call.data.replace("acc_cancel_", ""))
    await db_exec("UPDATE transactions SET tx_type='ADMIN_ADD_CANCEL' WHERE id=? AND tx_type='PENDING_ADD'", (tid,))
    await call.message.edit_text("❌ Cancelled."); await call.answer("Cancelled")

@dp.message(Command("deductbal"))
async def cmd_trutien(message: Message):
    try: await message.delete()
    except: pass
    if not is_admin(message.from_user.id): return
    parts = message.text.split()
    if len(parts) != 3 or not parts[1].isdigit(): await message.answer("Usage: <code>/deductbal ID AMOUNT</code>"); return
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
    users = await db_exec("SELECT user_id FROM users", fetch='all')
    sent = failed = 0
    if users:
        for (uid,) in users:
            try: await bot.send_message(uid, "📢 <b>ANNOUNCEMENT</b>\n\n" + safe(content, 3500)); sent += 1; await asyncio.sleep(0.05)
            except: failed += 1
    await message.answer(f"📢 Done. OK: {sent} · Fail: {failed}")

# =====================================================
# OTP POLLER
# =====================================================
class MkOtpPoller:
    MAX_CONSECUTIVE_ERRORS = 5
    def __init__(self):
        self.interval = max(MK_POLL_MIN_SEC, 10) 
        self._consecutive_errors = 0

    async def _get_today_otp_count(self, uid):
        row = await db_exec("SELECT COUNT(*) FROM orders WHERE user_id=? AND status='COMPLETED' AND created_at >= ?", (uid, now().strftime("%Y-%m-%d")), fetch='one')
        return row[0] if row else 0

    async def _broadcast_otp(self, row, otp_code, full_sms, reward_milli, platform):
        user_name = f"User {row['user_id']}"; u = await get_user(row["user_id"])
        if u and u["first_name"]: user_name = u["first_name"]
        display_country = ISO_MAP.get(row['country'], row['country']) if row.get("provider") == "NP" else row['country']
        flag = get_country_flag(display_country); today_count = await self._get_today_otp_count(row["user_id"])
        reward_str = f"+{usd(reward_milli)} USD" if reward_milli > 0 else "0 USD"

        user_text = f"📱 <b>{platform}</b> 🌍 {display_country}\n<b>OTP Received</b>\n👤 User: {user_link(row['user_id'], user_name)}\n\n🔒 <b>OTP :</b> <code>{otp_code}</code>\n📞 <code>{row['phone']}</code>\n📊 Today OTP : <b>{today_count}</b>\n<blockquote>💰 {reward_str}</blockquote>"
        kb_user = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💬 OTP Group", url=OTP_GROUP_URL), InlineKeyboardButton(text="🔄 Get New Number", callback_data=f"rng_{row['range_code']}")], [InlineKeyboardButton(text="🏠 Main Menu", callback_data="home")]])
        kb_group = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📢 Main Channel", url=MAIN_CHANNEL_URL), InlineKeyboardButton(text="🤖 Get Numbers", url=f"https://t.me/{BOT_USERNAME}?start=home")]])
        group_text = f"📱 <b>{platform}</b> 🌍 {display_country}\n<b>OTP Received</b>\n👤 User: {user_link(row['user_id'], user_name)}\n\n🔒 <b>OTP :</b> <code>{otp_code}</code>\n📞 <code>{mask_phone(row['phone'])}</code>\n📊 Today OTP : <b>{today_count}</b>"
        if full_sms: group_text += f"\n<blockquote>💬 {safe(full_sms, 300)}</blockquote>"

        if OTP_GROUP_ID:
            try: await bot.send_message(OTP_GROUP_ID, group_text, reply_markup=kb_group)
            except Exception as e: logger.error(f"Error sending OTP to Group: {e}")
        try:
            u_msg = await bot.send_message(row["user_id"], user_text, reply_markup=kb_user); track_msg(row["user_id"], u_msg.message_id)
        except Exception as e: logger.error(f"Error sending OTP to User: {e}")

    async def _process_otp(self, row, otp, sms):
        reward = REWARD_MILLI_PER_OTP
        if row.get("provider") == "NP": reward = 0; platform = row.get("operator", "Other").capitalize()
        elif row.get("provider") == "BASHA": reward = 0; platform = "Basha Service"
        else: platform = detect_otp_platform(sms)
        
        def _tx():
            db = get_db()
            try:
                db.execute("BEGIN IMMEDIATE")
                chk = db.execute("SELECT status FROM orders WHERE id=?", (row["id"],)).fetchone()
                if not chk or chk[0] != "PENDING": db.rollback(); return False
                db.execute("UPDATE orders SET status='COMPLETED', otp_code=?, full_sms=?, platform=?, reward_milli=?, updated_at=? WHERE id=?", (otp, sms, platform, reward, now_text(), row["id"])); db.commit()
                return True
            except Exception: db.rollback(); return False
            finally: db.close()
            
        success = await asyncio.to_thread(_tx) if hasattr(asyncio, 'to_thread') else await asyncio.get_running_loop().run_in_executor(None, _tx)
        if not success: return False
        
        if reward > 0:
            ok, _ = await change_usd(row["user_id"], reward, "OTP_REWARD", f"Reward OTP #{row['id']}")
            if not ok: reward = 0
        await self._broadcast_otp(row, otp, sms, reward, platform)
        return True

    async def _poll_once(self):
        rows = await get_pending_requests(limit=MK_POLL_BATCH)
        if not rows: return 0, 0, False
        mk_rows, np_rows, basha_rows = [r for r in rows if r.get("provider") == "MK"], [r for r in rows if r.get("provider") == "NP"], [r for r in rows if r.get("provider") == "BASHA"]
        checked = new_otp = 0; api_error = False
        
        if mk_rows:
            ids = []; by_req = {}
            for r in mk_rows:
                try: ids.append(int(r["request_id"])); by_req[int(r["request_id"])] = r
                except: await self._update_failed(r["id"])
            if ids:
                data, err = await api_request("POST", "check/status", {"request_ids": ids})
                if err: api_error = True
                else:
                    for item in data.get("data", {}).get("results", []) if isinstance(data, dict) else []:
                        try: rid = int(item.get("request_id"))
                        except: continue
                        row = by_req.get(rid)
                        if not row: continue
                        checked += 1
                        if (item.get("status") or "").lower() == "success":
                            otp, sms = str(item.get("otp_code") or "").strip(), str(item.get("full_sms") or "").strip()
                            if not otp: await self._update_failed(row["id"]); continue
                            if await self._process_otp(row, otp, sms): new_otp += 1
                        elif (item.get("status") or "").lower() in ["cancel", "failed", "expired", "refunded", "not_found"]: await self._update_failed(row["id"])

        for r in np_rows:
            checked += 1; data, err = await np_api_request("GET", "latest_otp", params={"number": r['phone']})
            if err: api_error = True; continue
            if data and data.get("has_otp") and str(data.get("otp_code") or "").strip():
                if await self._process_otp(r, str(data.get("otp_code")).strip(), f"Your OTP is: {data.get('otp_code')}"): new_otp += 1

        for r in basha_rows:
            checked += 1; data, err = await basha_api_request("POST", "legacy/get-last-sms", payload={"number": r['phone']})
            if err: api_error = True; continue
            if data and isinstance(data, dict):
                sms = str(data.get("message") or "").strip()
                if sms:
                    otp_match = re.search(r'\b(\d{4,8})\b', sms)
                    if otp_match and await self._process_otp(r, otp_match.group(1), sms): new_otp += 1
        return checked, new_otp, api_error

    async def _update_failed(self, oid):
        await db_exec("UPDATE orders SET status='FAILED', updated_at=? WHERE id=? AND status='PENDING'", (now_text(), oid))

    async def run_forever(self):
        while True:
            try:
                await expire_old_orders(); checked, new_otp, api_error = await self._poll_once()
                if api_error: self._consecutive_errors += 1; self.interval = min(MK_POLL_MAX_SEC, max(self.interval * 2, self.interval + 5))
                else:
                    self._consecutive_errors = 0
                    if checked == 0: self.interval = min(MK_POLL_MAX_SEC, self.interval + 5)
                    elif new_otp > 0: self.interval = max(MK_POLL_MIN_SEC, self.interval - 2)
                    else: self.interval = max(MK_POLL_MIN_SEC, self.interval - 1)
            except Exception as e: logger.error(f"Poller error: {e}"); self.interval = min(MK_POLL_MAX_SEC, max(self.interval * 2, 15))
            await asyncio.sleep(self.interval)

@dp.callback_query(F.data.startswith("show_otp_"))
async def cb_show_otp(call: CallbackQuery):
    oid = int(call.data.replace("show_otp_", "")); row = await get_order(oid)
    if not row or not row.get("otp_code"): await call.answer("OTP not found!", show_alert=True); return
    await call.answer(f"Your {row.get('platform') or 'Unknown'} OTP is: {row['otp_code']}", show_alert=True)

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

async def set_bot_commands():
    user_commands = [BotCommand(command="start", description="Open main menu"), BotCommand(command="profile", description="View profile"), BotCommand(command="wallet", description="View USD wallet"), BotCommand(command="getnum", description="Get OTP Number"), BotCommand(command="withdraw", description="Withdraw USD menu"), BotCommand(command="history", description="Transaction history"), BotCommand(command="id", description="Get Telegram ID")]
    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())
    admin_commands = user_commands + [BotCommand(command="admin", description="[Admin] Panel"), BotCommand(command="health", description="[Admin] Health"), BotCommand(command="pollnow", description="[Admin] Poll OTP"), BotCommand(command="broadcast", description="[Admin] Broadcast"), BotCommand(command="addbal", description="[Admin] Add bal"), BotCommand(command="deductbal", description="[Admin] Deduct bal"), BotCommand(command="whoami", description="[Admin] MK info"), BotCommand(command="access_list", description="[Admin] MK ranges"), BotCommand(command="radar", description="[Admin] Radar")]
    try: await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=ADMIN_ID))
    except Exception as e: logger.error(f"Error: {e}")

async def main():
    global _mk_poller, BOT_USERNAME
    try: 
        me = await bot.get_me(); BOT_USERNAME = me.username; await set_bot_commands()
    except Exception as e: logger.error(f"Error setting menu: {e}")
    
    try:
        await init_db(); await expire_old_orders()
    except Exception as e:
        logger.error(f"Database init error: {e}")
        
    asyncio.create_task(web_server())
    if MK_POLL_ENABLED:
        _mk_poller = MkOtpPoller(); asyncio.create_task(_mk_poller.run_forever()); logger.info("Poller created.")
    logger.info("FAST IVAS starting...")
    await dp.start_polling(bot, drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
