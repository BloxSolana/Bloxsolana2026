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
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand, BotCommandScopeChat, BotCommandScopeDefault
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest

# =====================================================
# CONFIG
# =====================================================
BOT_TOKEN      = "8622066775:AAG1_WA634q5SEctcbq-xdqlWJ3an-M1Lpw"
ADMIN_ID       = 6726769296
OTP_GROUP_ID   = -1004341368656
OTP_GROUP_URL  = "https://t.me/LIVEOTPIVAS"
MK_API_KEY     = "badacaa33d287233567a49db" 
MK_API_BASE    = "https://mknetworkbd.com/api/v3/public"

TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL", "")
TURSO_AUTH_TOKEN   = os.getenv("TURSO_AUTH_TOKEN", "")

ORDER_LIFETIME_MINUTES = 15
REWARD_MILLI_PER_OTP   = 2    # $0.002 (Đã giảm theo yêu cầu)
MIN_WITHDRAW_MILLI     = 1000 # $1.000 (Đã giảm theo yêu cầu)

MK_POLL_ENABLED = True
MK_POLL_MIN_SEC = 15 
MK_POLL_MAX_SEC = 45
MK_POLL_BATCH   = 100

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FAST_IVAS")

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp  = Dispatcher()

FALLBACK_COUNTRIES = {
    "Vietnam": "84XXX", "Liberia": "231XXX", "Guinea": "2246XXX",
    "Sierra Leone": "2327XXX", "Indonesia": "62XXX", "Cambodia": "855XXX",
    "Myanmar": "9596XXX", "Zambia": "2609XXX", "Tanzania": "255XXX",
    "Lesotho": "2666XXX", "Mozambique": "2588XXX", "Yemen": "9677XXX",
    "Algeria": "2135XXX", "Tunisia": "2162XXX", "Nigeria": "234XXX",
    "Nepal": "977XXX", "Afghanistan": "9370XXX", "Lebanon": "961XXX",
    "Morocco": "2126XXX", "Libya": "2189XXX", "Madagascar": "2613XXX",
    "Ethiopia": "2519XXX", "Senegal": "2217XXX", "Zimbabwe": "2637XXX",
    "Norway": "47XXX", "Egypt": "2012XXX", "Palestine": "9725XXX",
    "Uzbekistan": "998XXX", "Sudan": "2491XXX", "Cameroon": "237XXX",
    "Benin": "2290XXX", "Mali": "223XXX", "Ghana": "233XXX",
    "Kenya": "254XXX", "Uganda": "256XXX", "Rwanda": "250XXX",
    "Chad": "235XXX", "Niger": "227XXX", "Somalia": "252XXX",
    "Angola": "244XXX", "Botswana": "267XXX", "Namibia": "264XXX",
    "Gabon": "241XXX", "Congo": "242XXX", "Togo": "228XXX",
    "Burkina Faso": "226XXX", "Mauritania": "222XXX", "Gambia": "220XXX",
    "Guinea-Bissau": "245XXX", "Maldives": "960XXX"
}

ADMIN_PENDING_APPROVE = {} 
MSG_TO_DELETE = {}
_mk_poller = None

# =====================================================
# HELPERS
# =====================================================
def now():      return datetime.now(timezone.utc)
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
        "PENDING":   "⏳ Đang chờ",
        "EXPIRED":   "⌛ Hết hạn",
        "COMPLETED": "✅ Hoàn tất",
        "FAILED":    "❌ Thất bại",
        "APPROVED":  "✅ Đã duyệt",
        "REJECTED":  "❌ Từ chối",
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

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def detect_otp_platform(full_sms):
    if not full_sms: return "Khác"
    sms_lower = full_sms.lower()
    platforms = {
        "Facebook": ["facebook", "fb-", "fb:"],
        "Google": ["google", "g-"],
        "Telegram": ["telegram"],
        "WhatsApp": ["whatsapp"],
        "TikTok": ["tiktok"],
        "Zalo": ["zalo"],
        "Instagram": ["instagram", "ig-"],
        "Twitter/X": ["twitter", "x.com"],
        "Shopee": ["shopee"],
        "Grab": ["grab"],
        "Apple": ["apple", "icloud"],
        "Microsoft": ["microsoft", "outlook"]
    }
    for name, keywords in platforms.items():
        if any(kw in sms_lower for kw in keywords):
            return name
    return "Khác"

# =====================================================
# DATABASE
# =====================================================
def get_db():
    if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
        try:
            return libsql.connect("local_replica.db", sync_url=TURSO_DATABASE_URL, auth_token=TURSO_AUTH_TOKEN)
        except Exception as e:
            logger.error(f"Lỗi kết nối Turso: {e}. Đang dùng file local.")
            return libsql.connect("local.db")
    return libsql.connect("local.db")

async def init_db():
    db = get_db()
    db.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, usd_milli INTEGER NOT NULL DEFAULT 0, wallet_ton TEXT, referrer INTEGER, joined_at TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, request_id INTEGER UNIQUE, phone TEXT, country TEXT, operator TEXT, range_code TEXT, status TEXT NOT NULL DEFAULT 'PENDING', otp_code TEXT, full_sms TEXT, reward_milli INTEGER NOT NULL DEFAULT 0, msg_id INTEGER, created_at TEXT, expires_at TEXT, updated_at TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, amount INTEGER NOT NULL, tx_type TEXT, note TEXT, created_at TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS withdrawals (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, amount_milli INTEGER NOT NULL, wallet_ton TEXT, status TEXT NOT NULL DEFAULT 'PENDING', reject_reason TEXT, tx_hash TEXT, proof_photo TEXT, created_at TEXT, processed_at TEXT)")
    try: db.execute("ALTER TABLE withdrawals ADD COLUMN reject_reason TEXT")
    except: pass
    try: db.execute("ALTER TABLE withdrawals ADD COLUMN tx_hash TEXT")
    except: pass
    try: db.execute("ALTER TABLE withdrawals ADD COLUMN proof_photo TEXT")
    except: pass
    db.commit(); db.close()

# =====================================================
# HÀM DB
# =====================================================
async def register_user(tg_user, referrer=None):
    db = get_db()
    try:
        res = db.execute("SELECT user_id FROM users WHERE user_id=?", (tg_user.id,)).fetchone()
        name = tg_user.first_name or "Người dùng"
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
        if not row: db.rollback(); return False, "Không tìm thấy user."
        new = int(row[0]) + int(amount_milli)
        if new < 0: db.rollback(); return False, "Số dư USD không đủ."
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
                try: await bot.delete_message(chat_id=uid, message_id=msg_id)
                except: pass
            try:
                text = f"⌛ <b>ĐƠN HÀNG HẾT HẠN</b>\n\nSố: <code>{safe(phone)}</code> ({safe(country)})\nTrạng thái: Đã hết hạn sử dụng.\n\nVui lòng chọn thao tác bên dưới:"
                msg = await bot.send_message(chat_id=uid, text=text, reply_markup=expired_kb())
                track_msg(uid, msg.message_id)
            except Exception as e: logger.error(f"Lỗi gửi tin hết hạn: {e}")
        db.commit()
    finally: db.close()

# =====================================================
# KEYBOARDS
# =====================================================
def main_kb(uid):
    rows = [
        [InlineKeyboardButton(text="👤 Tài khoản", callback_data="menu_profile"),
         InlineKeyboardButton(text="💵 Ví USD",   callback_data="menu_wallet")],
        [InlineKeyboardButton(text="📱 Nhận số",  callback_data="menu_order_help"),
         InlineKeyboardButton(text="📜 Lịch sử",  callback_data="user_orders_history")],
        [InlineKeyboardButton(text="🏆 BXH Hôm Nay", callback_data="leaderboard")],
        [InlineKeyboardButton(text="💸 Rút USD",  callback_data="wd_menu"),
         InlineKeyboardButton(text="👥 Giới thiệu", callback_data="menu_referral")],
    ]
    if OTP_GROUP_URL:
        rows.append([InlineKeyboardButton(text="📢 Nhóm OTP", url=OTP_GROUP_URL)])
    if is_admin(uid):
        rows.append([InlineKeyboardButton(text="🛡 ADMIN PANEL", callback_data="admin_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def order_help_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Quay lại", callback_data="home")]])

def order_status_kb(order_id=None):
    rows = []
    if order_id:
        rows.append([
            InlineKeyboardButton(text="🔄 Làm mới", callback_data=f"refresh_order_{order_id}"),
            InlineKeyboardButton(text="📜 Check OTP", callback_data="user_orders_history")
        ])
    else:
        rows.append([
            InlineKeyboardButton(text="📜 Check OTP", callback_data="user_orders_history")
        ])
    rows.append([InlineKeyboardButton(text="❌ Hủy số này", callback_data=f"cancel_num_{order_id}" if order_id else "cancel_num_0")])
    rows.append([InlineKeyboardButton(text="🌍 Đổi quốc gia", callback_data="list_countries")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Thống kê",       callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 Danh sách User", callback_data="admin_users")],
        [InlineKeyboardButton(text="📦 Đơn hàng",       callback_data="admin_orders")],
        [InlineKeyboardButton(text="💸 Duyệt Rút TON",  callback_data="admin_withdraws")],
        [InlineKeyboardButton(text="✅ Lịch sử duyệt",   callback_data="admin_withdraws_history")],
        [InlineKeyboardButton(text="🛠 Lệnh Admin",      callback_data="admin_cmds")],
        [InlineKeyboardButton(text="⬅️ Quay lại",       callback_data="home")]
    ])

def admin_cmds_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Ép quét OTP (/pollnow)", callback_data="run_cmd_pollnow")],
        [InlineKeyboardButton(text="🟢 Check sức khỏe (/health)", callback_data="run_cmd_health")],
        [InlineKeyboardButton(text="📊 Xem tài khoản MK (/whoami)", callback_data="run_cmd_whoami")],
        [InlineKeyboardButton(text="🗺 Xem tuyến MK (/access_list)", callback_data="run_cmd_access_list")],
        [InlineKeyboardButton(text="📡 Xem radar MK (/radar)", callback_data="run_cmd_radar")],
        [InlineKeyboardButton(text="⬅️ Quay lại", callback_data="admin_menu")]
    ])

def expired_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Nhận số khác", callback_data="menu_order_help")],
        [InlineKeyboardButton(text="📜 Check Lịch Sử OTP", callback_data="user_orders_history")],
        [InlineKeyboardButton(text="🏠 Trang chủ", callback_data="home")]
    ])

# =====================================================
# MK API CORE
# =====================================================
HTTP_ERRORS = {
    401: "API key không hợp lệ.", 403: "API bị khoá / chờ duyệt.",
    404: "Hết số cho range này.", 405: "Sai HTTP method.",
    422: "Sai field.",            429: "Vượt rate limit.",
    500: "Lỗi nội bộ.",           503: "API tạm tắt.",
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
                    err = f"FAST IVAS {r.status}: {HTTP_ERRORS.get(r.status, '')}"
                    logger.warning(f"{err} - Raw: {raw[:200]}")
                    return None, err
                if isinstance(data, dict) and data.get("success") is False:
                    return None, str(data.get("message") or "API lỗi")
                return data, None
    except asyncio.TimeoutError:
        return None, "FAST IVAS timeout."
    except Exception:
        logger.exception("API fail"); return None, "Không kết nối được FAST IVAS."

async def api_get(ep, params=None): 
    return await api_request("GET", ep, params=params)

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
        return False, "Mã tuyến không hợp lệ."

    clean_range = range_code.replace("XXX", "").replace("xxx", "")
    
    data, err = await api_request("POST", "getnum/number", {"range": clean_range})
    if err: return False, err

    def find_valid_id(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                k_lower = str(k).lower()
                if ("id" in k_lower or "request" in k_lower) and str(v).isdigit():
                    return int(v)
            for v in obj.values():
                res = find_valid_id(v)
                if res is not None: return res
        elif isinstance(obj, list):
            for item in obj:
                res = find_valid_id(item)
                if res is not None: return res
        return None

    rid_int = find_valid_id(data)

    if rid_int is None:
        logger.error(f"=== KHÔNG TÌM THẤY REQUEST_ID ===\nDữ liệu API trả về: {json.dumps(data, ensure_ascii=False)}")
        return False, "Không tìm thấy ID trong phản hồi API (Xem log)."

    phone    = field(data, "number", "phone", "phone_number")
    country  = field(data, "country", "country_name")
    operator = field(data, "operator", "network", "carrier")

    exp = (now() + timedelta(minutes=ORDER_LIFETIME_MINUTES)).isoformat(timespec="seconds")
    db = get_db()
    try:
        db.execute("""
            INSERT INTO orders (user_id, request_id, phone, country, operator,
                range_code, status, created_at, expires_at, updated_at, msg_id)
            VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?, ?, ?, ?)
        """, (uid, rid_int, str(phone or "N/A"), str(country or "?"),
              str(operator or "?"), range_code, now_text(), exp, now_text(), msg_id))
        db.commit()
    except Exception as e:
        logger.error(f"Lỗi insert order: {e}"); return False, "Lỗi Database."
    finally: db.close()

    return True, {
        "request_id": rid_int, "phone": phone or "N/A",
        "country": country or "?", "operator": operator or "?",
        "expires_at": exp,
    }

# =====================================================
# HELPER ĐƠN HÀNG
# =====================================================
async def get_user_orders(uid, limit=10):
    await expire_old_orders()
    db = get_db()
    try:
        return db.execute("SELECT id, request_id, phone, country, operator, status, created_at, expires_at FROM orders WHERE user_id=? ORDER BY id DESC LIMIT ?", (uid, limit)).fetchall()
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
        rows = db.execute("SELECT id, user_id, request_id, phone, msg_id FROM orders WHERE status='PENDING' ORDER BY id ASC LIMIT ?", (limit,)).fetchall()
        return [{"id": r[0], "user_id": r[1], "request_id": int(r[2]), "phone": r[3], "msg_id": r[4]} for r in rows]
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
        try: await bot.send_message(ref, "👥 Có người mới tham gia FAST IVAS qua link của bạn.")
        except Exception: pass
    
    msg = await message.answer("🚀 <b>FAST IVAS</b>\n\nChào mừng bạn!\nChọn chức năng:", reply_markup=main_kb(message.from_user.id))
    track_msg(message.from_user.id, msg.message_id)

@dp.message(Command("help"))
async def cmd_help(message: Message):
    try: await message.delete()
    except: pass
    msg = await message.answer("<b>FAST IVAS — Hướng dẫn</b>\n\n/start — Menu\n/profile — Hồ sơ\n/wallet — Ví USD\n/nhanso RANGE — Nhận số OTP\n/donhang [ID] — Xem đơn\n/rut — Menu rút tiền\n/history — Lịch sử\n/id — Telegram ID\n\n" f"💵 <b>{usd(REWARD_MILLI_PER_OTP)}</b>/OTP · 💸 Rút min <b>{usd(MIN_WITHDRAW_MILLI)}</b>")
    track_msg(message.from_user.id, msg.message_id)

@dp.message(Command("id"))
async def cmd_id(message: Message):
    try: await message.delete()
    except: pass
    msg = await message.answer(f"Telegram ID: <code>{message.from_user.id}</code>")
    track_msg(message.from_user.id, msg.message_id)

@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    try: await message.delete()
    except: pass
    await register_user(message.from_user)
    u = await get_user(message.from_user.id)
    msg = await message.answer("👤 <b>HỒ SƠ</b>\n\n" f"ID: <code>{u['user_id']}</code>\nTên: {safe(u['first_name'])}\nUsername: @{safe(u['username'] or '—')}\nNgày tham gia: {safe(u['joined_at'][:10])}\n\n" f"💵 Số dư USD: <b>{usd(u['usd_milli'])}</b>")
    track_msg(message.from_user.id, msg.message_id)

@dp.message(Command("wallet"))
async def cmd_wallet(message: Message):
    try: await message.delete()
    except: pass
    await register_user(message.from_user)
    u = await get_user(message.from_user.id)
    msg = await message.answer("💵 <b>VÍ USD (từ OTP)</b>\n\n" f"Số dư: <b>{usd(u['usd_milli'])}</b>\nThưởng/OTP: <b>{usd(REWARD_MILLI_PER_OTP)}</b>\nRút min: <b>{usd(MIN_WITHDRAW_MILLI)}</b>\n\n" "Lệnh rút: <code>/rut</code>")
    track_msg(message.from_user.id, msg.message_id)

# =====================================================
# MENU CALLBACKS
# =====================================================
@dp.callback_query(F.data == "home")
async def cb_home(call: CallbackQuery):
    await call.message.edit_text("🚀 <b>FAST IVAS</b>\n\nChọn chức năng:", reply_markup=main_kb(call.from_user.id))
    await call.answer()

@dp.callback_query(F.data == "leaderboard")
async def cb_leaderboard(call: CallbackQuery):
    today_str = now().strftime("%Y-%m-%d")
    db = get_db()
    try:
        # Truy vấn lấy OTP, Số dư và Lượt giới thiệu
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
        
        text = "🏆 <b>BẢNG XẾP HẠNG OTP HÔM NAY</b>\n\n"
        if not rows:
            text += "Chưa có ai nhận được OTP hôm nay."
        else:
            for i, r in enumerate(rows, 1):
                uid = r[0]
                otp_count = r[1]
                name = safe(r[2] or f"User {uid}")
                balance = usd(r[3])
                ref_count = r[4]
                
                text += f"{i}. <b>{name}</b> (<code>{uid}</code>)\n"
                text += f"   ├ 🔑 OTP: <b>{otp_count}</b>\n"
                text += f"   ├ 💵 Số dư: <b>{balance}</b>\n"
                text += f"   └ 👥 Lượt mời: <b>{ref_count}</b>\n\n"
        
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Quay lại", callback_data="home")]])
        await call.message.edit_text(text, reply_markup=kb)
    finally:
        db.close()
    await call.answer()

@dp.callback_query(F.data == "menu_order_help")
async def cb_menu_order_help(call: CallbackQuery):
    await call.answer("Đang tải...")
    data, err = await api_get("access_list", params={"limit": 200})
    country_dict = {}
    if not err and isinstance(data, dict):
        items = data.get("data", {}).get("items", [])
        for item in items:
            c_name = item.get("country"); r_code = item.get("range")
            if c_name and r_code and c_name not in country_dict: country_dict[c_name] = r_code
    if not country_dict: country_dict = FALLBACK_COUNTRIES

    all_c = list(country_dict.keys()); random.shuffle(all_c); selected_c = all_c[:50]
    cmd_list = "".join([f"🌍 {c}: <code>/nhanso {country_dict[c]}</code>\n" for c in selected_c])

    text = "📱 <b>NHẬN SỐ OTP</b>\n\nGõ lệnh hoặc bấm nút bên dưới.\n\n<b>DANH SÁCH LỆNH THAM KHẢO (50 nước):</b>\n" + cmd_list
    await call.message.edit_text(text, reply_markup=order_help_kb())
    await call.answer()

@dp.callback_query(F.data == "menu_profile")
async def cb_menu_profile(call: CallbackQuery):
    await register_user(call.from_user)
    u = await get_user(call.from_user.id)
    await call.message.edit_text("👤 <b>HỒ SƠ</b>\n\n" f"ID: <code>{u['user_id']}</code>\nTên: {safe(u['first_name'])}\nUsername: @{safe(u['username'] or '—')}\nNgày tham gia: {safe(u['joined_at'][:10])}\n\n" f"💵 Số dư USD: <b>{usd(u['usd_milli'])}</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Quay lại", callback_data="home")]]))
    await call.answer()

@dp.callback_query(F.data == "menu_wallet")
async def cb_menu_wallet(call: CallbackQuery):
    await register_user(call.from_user)
    u = await get_user(call.from_user.id)
    await call.message.edit_text("💵 <b>VÍ USD</b>\n\n" f"Số dư: <b>{usd(u['usd_milli'])}</b>\nThưởng/OTP: <b>{usd(REWARD_MILLI_PER_OTP)}</b>\nRút min: <b>{usd(MIN_WITHDRAW_MILLI)}</b>\n\n" "Lệnh rút: <code>/rut</code>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Quay lại", callback_data="home")]]))
    await call.answer()

@dp.callback_query(F.data == "menu_referral")
async def cb_menu_referral(call: CallbackQuery):
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={call.from_user.id}"
    await call.message.edit_text("👥 <b>GIỚI THIỆU</b>\n\n" f"<code>{link}</code>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Quay lại", callback_data="home")]]))
    await call.answer()

# =====================================================
# RÚT TIỀN
# =====================================================
@dp.message(Command("rut"))
async def cmd_rut_menu(message: Message):
    try: await message.delete()
    except: pass
    u = await get_user(message.from_user.id)
    wallet = u["wallet_ton"] or "Chưa thiết lập"
    text = f"💸 <b>RÚT USD QUA MẠNG TON</b>\n\nSố dư hiện tại: <b>{usd(u['usd_milli'])}</b>\nVí TON: <code>{wallet}</code>\n\nVui lòng chọn thao tác:"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚙️ Thiết lập địa chỉ ví TON", callback_data="wd_setup_addr")], [InlineKeyboardButton(text="💵 Rút tiền", callback_data="wd_choose_amount")], [InlineKeyboardButton(text="⬅️ Quay lại", callback_data="home")]])
    msg = await message.answer(text, reply_markup=kb)
    track_msg(message.from_user.id, msg.message_id)

@dp.callback_query(F.data == "wd_menu")
async def cb_wd_menu(call: CallbackQuery):
    u = await get_user(call.from_user.id)
    wallet = u["wallet_ton"] or "Chưa thiết lập"
    text = f"💸 <b>RÚT USD QUA MẠNG TON</b>\n\nSố dư hiện tại: <b>{usd(u['usd_milli'])}</b>\nVí TON: <code>{wallet}</code>\n\nVui lòng chọn thao tác:"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚙️ Thiết lập địa chỉ ví TON", callback_data="wd_setup_addr")], [InlineKeyboardButton(text="💵 Rút tiền", callback_data="wd_choose_amount")], [InlineKeyboardButton(text="⬅️ Quay lại", callback_data="home")]])
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()

@dp.callback_query(F.data == "wd_setup_addr")
async def cb_wd_setup_addr(call: CallbackQuery):
    text = "⚙️ <b>THIẾT LẬP VÍ TON</b>\n\nVui lòng gửi địa chỉ ví TON của bạn vào khung chat bên dưới.\nVí dụ: <code>UQBfFHeVzZyixLYup3rvCkRaSVJTOc8UtCeqksenDoMxSvOS</code>\n\n<i>(Địa chỉ ví TON thường bắt đầu bằng UQ hoặc EQ và dài 48 ký tự).</i>"
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Quay lại", callback_data="wd_menu")]]))
    await call.answer()

@dp.message(F.text.regexp(r"^(EQ|UQ)[a-zA-Z0-9_-]{46}$"))
async def handle_wallet_input(message: Message):
    try: await message.delete()
    except: pass
    wallet = message.text.strip()
    await set_wallet_ton(message.from_user.id, wallet)
    text = f"✅ <b>ĐỊA CHỈ VÍ ĐÃ ĐƯỢC LƯU</b>\n\nĐịa chỉ ví của bạn:\n<code>{wallet}</code>\n\nBạn có thể bấm <b>Quay lại</b> để vào Menu rút tiền."
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Quay lại Menu Rút Tiền", callback_data="wd_menu")]])
    msg = await message.answer(text, reply_markup=kb)
    track_msg(message.from_user.id, msg.message_id)

@dp.callback_query(F.data == "wd_choose_amount")
async def cb_wd_choose_amount(call: CallbackQuery):
    u = await get_user(call.from_user.id)
    if not u["wallet_ton"]:
        await call.answer("Vui lòng thiết lập ví TON trước!", show_alert=True); return
        
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
        buttons.append([InlineKeyboardButton(text=f"💰 Rút tất cả (~{usd(all_in_amt)})", callback_data=f"wd_amt_all")])
        
    buttons.append([InlineKeyboardButton(text="⬅️ Quay lại", callback_data="wd_menu")])
    
    text = f"💵 <b>CHỌN SỐ TIỀN MUỐN RÚT</b>\n\nSố dư: <b>{usd(balance)}</b>\n\n<i>(* Lưu ý: Rút tất cả sẽ trừ phí mạng TON ~$0.1)</i>"
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
            await call.answer("Số dư không đủ để rút (sau khi trừ phí mạng)!", show_alert=True); return
        text_amt = f"tất cả {usd(amt_milli)} (đã trừ phí mạng)"
        amt_usd = 0
    else:
        amt_usd = int(call.data.replace("wd_amt_", ""))
        amt_milli = amt_usd * 1000
        if balance < amt_milli:
            await call.answer(f"Bạn không đủ ${amt_usd} để rút!", show_alert=True); return
        text_amt = f"${amt_usd}.000"
        
    text = f"⚠️ <b>XÁC NHẬN RÚT TIỀN</b>\n\nBạn có chắc chắn muốn rút <b>{text_amt}</b> về ví:\n<code>{u['wallet_ton']}</code> không?\n\n<i>(Tiền sẽ bị trừ ngay và chờ Admin duyệt)</i>"
    
    if call.data == "wd_amt_all":
        callback_conf = "wd_conf_all"
    else:
        callback_conf = f"wd_conf_{amt_usd}"
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Xác nhận rút", callback_data=callback_conf)], 
        [InlineKeyboardButton(text="❌ Hủy", callback_data="wd_choose_amount")]
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
            await call.answer("Số dư không đủ!", show_alert=True); return
        amt_str = usd(amt_milli)
    else:
        amt_usd = int(call.data.replace("wd_conf_", ""))
        amt_milli = amt_usd * 1000
        if balance < amt_milli:
            await call.answer(f"Bạn không đủ tiền!", show_alert=True); return
        amt_str = usd(amt_milli)

    ok, new_usd = await change_usd(call.from_user.id, -amt_milli, "WITHDRAW_HOLD", "Yêu cầu rút TON")
    if not ok:
        await call.answer(safe(new_usd), show_alert=True); return
        
    wid = await create_withdrawal(call.from_user.id, amt_milli, u["wallet_ton"])
    await call.message.edit_text(f"✅ <b>ĐÃ TẠO LỆNH RÚT</b>\n\nMã: <code>#{wid}</code>\nSố tiền: <b>{amt_str}</b>\nVí TON: <code>{u['wallet_ton']}</code>\nCòn lại: <b>{usd(new_usd)}</b>\n\nVui lòng chờ Admin duyệt.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Quay lại", callback_data="home")]]))
    
    try:
        db = get_db()
        pending_count = db.execute("SELECT COUNT(*) FROM withdrawals WHERE status='PENDING'").fetchone()[0]
        db.close()
        admin_text = f"🔔 <b>THÔNG BÁO RÚT TIỀN</b>\n\nHiện đang có <b>{pending_count}</b> yêu cầu rút tiền đang chờ duyệt.\nVui lòng bấm nút bên dưới để xử lý."
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👉 Bấm vào đây để xử lý", callback_data="admin_withdraws")]])
        admin_msg = await bot.send_message(ADMIN_ID, admin_text, reply_markup=kb)
        track_msg(ADMIN_ID, admin_msg.message_id)
    except Exception as e: logger.error(f"Lỗi gửi thông báo rút cho admin: {e}")
    await call.answer("Đã tạo lệnh rút!")

# =====================================================
# NHẬN SỐ & CHECK OTP
# =====================================================
@dp.callback_query(F.data == "list_countries")
async def cb_list_countries(call: CallbackQuery):
    await call.answer("Đang tải...")
    data, err = await api_get("access_list", params={"limit": 200})
    country_dict = {}
    if not err and isinstance(data, dict):
        items = data.get("data", {}).get("items", [])
        for item in items:
            c_name = item.get("country"); r_code = item.get("range")
            if c_name and r_code:
                if c_name not in country_dict: country_dict[c_name] = []
                country_dict[c_name].append(r_code)
    if not country_dict: country_dict = {k: [v] for k, v in FALLBACK_COUNTRIES.items()}

    buttons = []
    c_list = list(country_dict.keys())
    for i in range(0, len(c_list), 2):
        row = [InlineKeyboardButton(text=f"🌍 {c_list[i]} ({country_dict[c_list[i]][0]})", callback_data=f"rng_{country_dict[c_list[i]][0]}")]
        if i + 1 < len(c_list):
            c2 = c_list[i+1]
            row.append(InlineKeyboardButton(text=f"🌍 {c2} ({country_dict[c2][0]})", callback_data=f"rng_{country_dict[c2][0]}"))
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="⬅️ Quay lại", callback_data="menu_order_help")])

    await call.message.edit_text("🌍 <b>CHỌN QUỐC GIA</b>\n\nBấm vào quốc gia để nhận số ngay lập tức (Mã trong ngoặc là Range):", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("rng_"))
async def cb_choose_range(call: CallbackQuery):
    range_code = call.data.replace("rng_", "")
    await call.answer("Đang lấy số...")
    ok, res = await create_number_order(call.from_user.id, range_code, msg_id=call.message.message_id)
    if not ok:
        await call.message.edit_text(f"❌ {safe(res)}", reply_markup=order_help_kb()); return
    
    db = get_db()
    row = db.execute("SELECT id FROM orders WHERE request_id=?", (res['request_id'],)).fetchone()
    db.close()
    order_id = row[0] if row else 0

    await call.message.edit_text(f"✅ <b>ĐÃ NHẬN SỐ</b>\n\nSố: <code>{res['phone']}</code>\nQuốc gia: {safe(res['country'])}\nHết hạn: {safe(res['expires_at'])}\n\n⏳ Đang chờ OTP...", reply_markup=order_status_kb(order_id))

@dp.callback_query(F.data.startswith("new_num_"))
async def cb_new_num(call: CallbackQuery):
    range_code = call.data.replace("new_num_", "")
    await call.answer("Đang lấy số mới...")
    ok, res = await create_number_order(call.from_user.id, range_code)
    if not ok:
        await call.message.answer(f"❌ {safe(res)}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Quay lại", callback_data="home")]]))
        return
    
    db = get_db()
    row = db.execute("SELECT id FROM orders WHERE request_id=?", (res['request_id'],)).fetchone()
    db.close()
    order_id = row[0] if row else 0

    await call.message.edit_text(f"✅ <b>ĐÃ NHẬN SỐ</b>\n\nSố: <code>{res['phone']}</code>\nQuốc gia: {safe(res['country'])}\nHết hạn: {safe(res['expires_at'])}\n\n⏳ Đang chờ OTP...", reply_markup=order_status_kb(order_id))

@dp.callback_query(F.data.startswith("refresh_order_"))
async def cb_refresh_order(call: CallbackQuery):
    oid = int(call.data.replace("refresh_order_", ""))
    row = await get_order(oid, call.from_user.id)
    if not row:
        await call.answer("Không tìm thấy đơn hoặc bạn không có quyền!", show_alert=True); return
    
    await call.answer("Đang kiểm tra...")
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
                            reward = REWARD_MILLI_PER_OTP
                            ok, _ = await change_usd(row["user_id"], reward, "OTP_REWARD", f"Thưởng OTP #{row['id']}")
                            if not ok: reward = 0
                            await _mk_poller._update_completed(oid, otp, sms, reward)
                            await _mk_poller._broadcast_otp(row, otp, sms, reward)
                        
                        await call.message.edit_text(f"✅ <b>ĐÃ CÓ OTP</b>\n\nSố: <code>{row['phone']}</code>\nOTP: <code>{safe(otp)}</code>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📜 Check Lịch Sử", callback_data="user_orders_history")]]))
                        return
    except Exception as e:
        logger.error(f"Lỗi refresh đơn #{oid}: {e}")

    row = await get_order(oid, call.from_user.id)
    if row["status"] == "COMPLETED":
        text = f"✅ <b>ĐÃ CÓ OTP</b>\n\nSố: <code>{row['phone']}</code>\nQuốc gia: {safe(row['country'])}\nOTP: <code>{safe(row['otp_code'])}</code>"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📜 Check Lịch Sử", callback_data="user_orders_history")]])
    elif row["status"] == "EXPIRED":
        text = f"⌛ <b>ĐÃ HẾT HẠN</b>\n\nSố: <code>{row['phone']}</code>\nQuốc gia: {safe(row['country'])}\nHết hạn lúc: {safe(row['expires_at'])}"
        kb = order_status_kb()
    else:
        text = f"⏳ <b>ĐANG CHỜ OTP</b>\n\nSố: <code>{row['phone']}</code>\nQuốc gia: {safe(row['country'])}\nHết hạn: {safe(row['expires_at'])}\n\n<i>(Vui lòng bấm Làm mới để kiểm tra lại)</i>"
        kb = order_status_kb(oid)
        
    await call.message.edit_text(text, reply_markup=kb)

@dp.callback_query(F.data == "user_orders_history")
async def cb_user_orders_history(call: CallbackQuery):
    rows = await get_user_orders(call.from_user.id, limit=15)
    if not rows:
        await call.answer("Bạn chưa lấy số nào!", show_alert=True); return
    
    buttons = []
    for r in rows:
        oid, req, phone, country, op, status, c_at, e_at = r
        icon = "✅" if status == "COMPLETED" else ("⌛" if status == "EXPIRED" else "⏳")
        buttons.append([InlineKeyboardButton(text=f"{icon} {mask_phone(phone)} ({country})", callback_data=f"view_history_{oid}")])
    
    buttons.append([InlineKeyboardButton(text="⬅️ Quay lại", callback_data="home")])
    await call.message.edit_text("📜 <b>LỊCH SỬ NHẬN SỐ GẦN ĐÂY</b>\n\nBấm vào số để xem chi tiết:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("view_history_"))
async def cb_view_history(call: CallbackQuery):
    oid = int(call.data.replace("view_history_", ""))
    row = await get_order(oid, call.from_user.id)
    if not row:
        await call.answer("Không tìm thấy!", show_alert=True); return
    
    text = f"📦 <b>CHI TIẾT ĐƠN #{oid}</b>\n\n"
    text += f"Số: <code>{safe(row['phone'])}</code>\n"
    text += f"Quốc gia: {safe(row['country'])}\n"
    text += f"Hết hạn: {safe(row['expires_at'])}\n"
    
    if row["status"] == "COMPLETED" and row.get("otp_code"):
        text += f"\n🔑 <b>MÃ OTP:</b> <code>{safe(row['otp_code'])}</code>"
        if row.get("full_sms"): text += f"\n💬 {safe(row['full_sms'])}"
    elif row["status"] == "EXPIRED":
        text += "\n\nTrạng thái: <b>Đã hết hạn</b>"
    else:
        text += "\n\nTrạng thái: <b>Đang chờ OTP</b>"

    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Quay lại", callback_data="user_orders_history")]]))
    await call.answer()

@dp.callback_query(F.data.startswith("cancel_num_"))
async def cb_cancel_num(call: CallbackQuery):
    await call.answer("Đang hủy số...", show_alert=False)
    try: await call.message.delete()
    except: pass
    msg = await call.message.answer("✅ Bạn đã hủy nhận số này thành công.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 Nhận số mới", callback_data="menu_order_help")]]))
    track_msg(call.from_user.id, msg.message_id)

@dp.message(Command("nhanso"))
async def cmd_nhanso(message: Message):
    try: await message.delete()
    except: pass
    await register_user(message.from_user)
    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        await message.answer("Cú pháp: <code>/nhanso MA_TUYEN</code>"); return
    waiting_msg = await message.answer("⏳ Đang gửi yêu cầu…")
    ok, res = await create_number_order(message.from_user.id, parts[1].strip(), msg_id=waiting_msg.message_id)
    if not ok:
        await waiting_msg.edit_text(f"❌ {safe(res)}"); return

    db = get_db()
    row = db.execute("SELECT id FROM orders WHERE request_id=?", (res['request_id'],)).fetchone()
    db.close()
    order_id = row[0] if row else 0

    await waiting_msg.edit_text(f"✅ <b>ĐÃ NHẬN SỐ</b>\n\nSố: <code>{res['phone']}</code>\nQuốc gia: {safe(res['country'])}\nHết hạn: {safe(res['expires_at'])}\n\n⏳ Đang chờ OTP...", reply_markup=order_status_kb(order_id))

# =====================================================
# ADMIN PANEL
# =====================================================
@dp.callback_query(F.data == "admin_menu")
async def cb_admin_menu(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Không có quyền.", show_alert=True); return
    await call.message.edit_text("🛡 <b>ADMIN PANEL</b>", reply_markup=admin_kb())
    await call.answer()

@dp.callback_query(F.data == "admin_cmds")
async def cb_admin_cmds(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    await call.message.edit_text("🛠 <b>DANH SÁCH LỆNH ADMIN</b>\n\nBấm nút bên dưới để chạy lệnh ngay (Không cần gõ tay):", reply_markup=admin_cmds_kb())
    await call.answer()

@dp.callback_query(F.data.startswith("run_cmd_"))
async def cb_run_cmd(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    cmd = call.data.replace("run_cmd_", "")
    try: await call.message.delete()
    except: pass

    if cmd == "pollnow":
        if not _mk_poller: await call.message.answer("Poller chưa chạy."); return
        msg = await call.message.answer("🔄 Polling…")
        try:
            c, n, err = await _mk_poller._poll_once()
            if err: await msg.edit_text(f"⚠️ Lỗi API: {err}")
            else: await msg.edit_text(f"✅ Checked: {c} · OTP mới: {n}")
        except Exception as e: await msg.edit_text(f"❌ {safe(str(e))}")
        
    elif cmd == "health":
        db = get_db()
        try: pending = db.execute("SELECT COUNT(*) FROM orders WHERE status='PENDING'").fetchone()[0]
        finally: db.close()
        poller = "OFF" if not _mk_poller else f"ON ({_mk_poller.interval}s, err={_mk_poller._consecutive_errors})"
        text = "🟢 <b>FAST IVAS ONLINE</b>\n\n" f"DB: <code>Turso Cloud</code>\nAPI key: {'✓' if MK_API_KEY else '✗'}\n" f"OTP group: <code>{OTP_GROUP_ID}</code>\nĐơn chờ: <b>{pending}</b>\nPoller: {safe(poller)}\n" f"Thưởng/OTP: <b>{usd(REWARD_MILLI_PER_OTP)}</b>\nMin rút: <b>{usd(MIN_WITHDRAW_MILLI)}</b>"
        await call.message.answer(text)

    elif cmd == "whoami":
        data, err = await api_get("whoami")
        if err: await call.message.answer(f"❌ {safe(err)}"); return
        await call.message.answer(f"📊 <b>TÀI KHOẢN MK</b>\n\n<pre>{fmt_api(data)}</pre>")
        
    elif cmd == "access_list":
        data, err = await api_get("access_list")
        if err: await call.message.answer(f"❌ {safe(err)}"); return
        await call.message.answer(f"🗺 <b>DANH SÁCH TUYẾN</b>\n\n<pre>{fmt_api(data)}</pre>")
        
    elif cmd == "radar":
        data, err = await api_get("radar", params={"limit": 25, "charts": "true"})
        if err: await call.message.answer(f"❌ {safe(err)}"); return
        await call.message.answer(f"📡 <b>RADAR</b>\n\n<pre>{fmt_api(data)}</pre>")
        
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
        text = f"📊 <b>THỐNG KÊ</b>\n\n👥 Users: <b>{users}</b>\n📦 Đơn: <b>{orders}</b> (chờ <b>{pending}</b>, xong <b>{completed}</b>)\n💵 USD tổng: <b>{usd(tot_usd)}</b>\n💸 Rút chờ: <b>{wd}</b>"
        await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Quay lại", callback_data="admin_menu")]]))
    finally: db.close()
    await call.answer()

@dp.callback_query(F.data == "admin_users")
async def cb_admin_users(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    db = get_db()
    try:
        users = db.execute("SELECT joined_at, user_id, first_name FROM users ORDER BY joined_at DESC LIMIT 50").fetchall()
        if not users:
            await call.message.edit_text("Chưa có user nào.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Quay lại", callback_data="admin_menu")]]))
        else:
            buttons = []
            for joined, uid, name in users:
                buttons.append([InlineKeyboardButton(text=f"👤 {name} ({uid})", callback_data=f"adm_u_{uid}")])
            buttons.append([InlineKeyboardButton(text="🗑 Xoá lịch sử chat", callback_data="admin_clear_chat")])
            buttons.append([InlineKeyboardButton(text="⬅️ Quay lại", callback_data="admin_menu")])
            await call.message.edit_text("👥 <b>DANH SÁCH USER</b>\n\nBấm vào User để xem chi tiết:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    finally: db.close()
    await call.answer()

@dp.callback_query(F.data == "admin_clear_chat")
async def cb_admin_clear_chat(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    try:
        await call.message.delete()
        await call.message.answer("🗑 Đã xoá lịch sử tin nhắn trên màn hình.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Quay lại Admin Panel", callback_data="admin_menu")]]))
    except Exception: pass
    await call.answer("Đã xoá chat!")

@dp.callback_query(F.data == "admin_orders")
async def cb_admin_orders(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    rows = await get_all_orders()
    if not rows:
        text = "Chưa có đơn."
    else:
        lines = ["📦 <b>ĐƠN GẦN ĐÂY</b>\n"]
        for r in rows: lines.append(f"#{r[0]} | User <code>{r[1]}</code>\nRequest: <code>{safe(r[2])}</code>\nSố: <code>{safe(r[3])}</code>\nStatus: {safe(r[4])}")
        text = "\n\n".join(lines)
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Quay lại", callback_data="admin_menu")]]))
    await call.answer()

@dp.callback_query(F.data == "admin_withdraws")
async def cb_admin_withdraws(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    db = get_db()
    try:
        rows = db.execute("SELECT w.id, w.user_id, w.amount_milli, w.wallet_ton, u.first_name FROM withdrawals w JOIN users u ON w.user_id = u.user_id WHERE w.status='PENDING' ORDER BY w.id DESC LIMIT 15").fetchall()
        if not rows:
            await call.message.edit_text("Không có yêu cầu rút TON nào đang chờ.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Quay lại", callback_data="admin_menu")]]))
        else:
            buttons = []
            for i, (rid, uid, amt, wallet, name) in enumerate(rows, 1):
                buttons.append([InlineKeyboardButton(text=f"{i}. {name} - {usd(amt)}", callback_data=f"wd_admin_view_{rid}")])
            buttons.append([InlineKeyboardButton(text="⬅️ Quay lại", callback_data="admin_menu")])
            await call.message.edit_text("💸 <b>YÊU CẦU RÚT TON</b>\n\nBấm vào User để xử lý:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    finally: db.close()
    await call.answer()

@dp.callback_query(F.data == "admin_withdraws_history")
async def cb_admin_withdraws_history(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    db = get_db()
    try:
        rows = db.execute("SELECT w.id, w.user_id, w.amount_milli, w.status, w.processed_at, w.reject_reason, u.first_name FROM withdrawals w JOIN users u ON w.user_id = u.user_id WHERE w.status IN ('APPROVED', 'REJECTED') ORDER BY w.processed_at DESC LIMIT 20").fetchall()
        if not rows:
            text = "Chưa có lịch sử duyệt nào."
        else:
            lines = ["📜 <b>LỊCH SỬ DUYỆT</b>\n"]
            for rid, uid, amt, status, p_at, reason, name in rows:
                icon = "✅" if status == "APPROVED" else "❌"
                note = f" - Lý do: {reason}" if reason else ""
                lines.append(f"{icon} <b>Đơn #{rid}</b> | {p_at[:16] if p_at else ''}\n👤 {name} (<code>{uid}</code>)\n💵 {usd(amt)}{note}\n")
            text = "\n".join(lines)
        await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Xoá lịch sử duyệt", callback_data="admin_clear_history")],
            [InlineKeyboardButton(text="⬅️ Quay lại", callback_data="admin_menu")]
        ]))
    finally: db.close()
    await call.answer()

@dp.callback_query(F.data == "admin_clear_history")
async def cb_admin_clear_history(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    try:
        await call.message.delete()
        await call.message.answer("🗑 Đã xoá lịch sử duyệt trên màn hình.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Quay lại", callback_data="admin_menu")]]))
    except Exception: pass
    await call.answer("Đã xoá lịch sử!")

@dp.callback_query(F.data.startswith("adm_u_"))
async def cb_adm_user_detail(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    uid = int(call.data.replace("adm_u_", ""))
    u = await get_user(uid)
    if not u:
        await call.answer("Không tìm thấy user.", show_alert=True); return
    text = f"👤 <b>CHI TIẾT USER</b>\n\nID: <code>{uid}</code>\nTên: {safe(u['first_name'])}\nUsername: @{safe(u['username'] or '—')}\nSố dư: <b>{usd(u['usd_milli'])}</b>\n\n👇 Để cộng/trừ tiền, bấm nút:"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Cộng Tiền", callback_data=f"adm_cong_help_{uid}")],
        [InlineKeyboardButton(text="➖ Trừ Tiền", callback_data=f"adm_tru_help_{uid}")],
        [InlineKeyboardButton(text="⬅️ Quay lại", callback_data="admin_users")]
    ])
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()

@dp.callback_query(F.data.startswith("adm_cong_help_"))
async def cb_adm_cong_help(call: CallbackQuery):
    uid = call.data.replace("adm_cong_help_", "")
    text = f"➕ <b>HƯỚNG DẪN CỘNG TIỀN</b>\n\nGõ lệnh sau ra ngoài chat:\n\n<code>/congtien {uid} 10$</code>"
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Quay lại", callback_data=f"adm_u_{uid}")]]))
    await call.answer()

@dp.callback_query(F.data.startswith("adm_tru_help_"))
async def cb_adm_tru_help(call: CallbackQuery):
    uid = call.data.replace("adm_tru_help_", "")
    text = f"➖ <b>HƯỚNG DẪN TRỪ TIỀN</b>\n\nGõ lệnh sau ra ngoài chat:\n\n<code>/trutien {uid} 10$</code>"
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Quay lại", callback_data=f"adm_u_{uid}")]]))
    await call.answer()

@dp.callback_query(F.data.startswith("wd_admin_view_"))
async def cb_wd_admin_view(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    wid = int(call.data.replace("wd_admin_view_", ""))
    db = get_db()
    try:
        row = db.execute("SELECT w.id, w.user_id, w.amount_milli, w.wallet_ton, w.status, u.first_name FROM withdrawals w JOIN users u ON w.user_id = u.user_id WHERE w.id=?", (wid,)).fetchone()
        if not row or row[4] != "PENDING":
            await call.answer("Đơn này đã được xử lý!", show_alert=True); return
        rid, uid, amt, wallet, status, name = row
        text = f"💸 <b>YÊU CẦU RÚT TON</b>\n\n👤 User: <b>{name}</b> (<code>{uid}</code>)\n💵 Số tiền: <b>{usd(amt)}</b>\n🔗 Ví TON: <code>{wallet}</code>\n\n👇 Chọn thao tác xử lý:"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Duyệt (Gửi Bill)", callback_data=f"wd_approve_step1_{rid}")],
            [InlineKeyboardButton(text="⏳ Để sau", callback_data="admin_withdraws")],
            [InlineKeyboardButton(text="❌ Từ chối duyệt", callback_data=f"wd_reject_list_{rid}")]
        ])
        await call.message.edit_text(text, reply_markup=kb)
    finally: db.close()
    await call.answer()

@dp.callback_query(F.data.startswith("wd_approve_step1_"))
async def cb_wd_approve_step1(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    wid = int(call.data.replace("wd_approve_step1_", ""))
    ADMIN_PENDING_APPROVE[ADMIN_ID] = {"wid": wid, "step": "waiting_link"}
    text = f"🔗 <b>THÊM LINK GIAO DỊCH</b>\n\nVui lòng gửi <b>Link giao dịch TON (TX Hash)</b> vào chat này."
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Hủy", callback_data=f"wd_admin_view_{wid}")]])
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

    text = f"🔗 <b>XÁC NHẬN LINK GIAO DỊCH</b>\n\nLink đã nhận:\n<code>{safe(tx_hash)}</code>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Xác nhận", callback_data="wd_confirm_link")],
        [InlineKeyboardButton(text="❌ Hủy", callback_data=f"wd_admin_view_{wid}")]
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

    text = f"🖼 <b>THÊM ẢNH BẰNG CHỨNG</b>\n\nVui lòng gửi <b>Ảnh chụp bill chuyển tiền</b> vào chat này."
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Hủy", callback_data=f"wd_admin_view_{wid}")]])
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

    text = f"🖼 <b>XÁC NHẬN ẢNH BẰNG CHỨNG</b>\n\nBạn đã gửi 1 ảnh. Xác nhận duyệt đơn <code>#{wid}</code> và gửi bill cho User?"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Xác nhận duyệt", callback_data="wd_confirm_photo")],
        [InlineKeyboardButton(text="❌ Hủy", callback_data=f"wd_admin_view_{wid}")]
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

    text = f"🎉 <b>RÚT TIỀN THÀNH CÔNG</b> 🎉\n\nChúc mừng bạn! Yêu cầu rút <b>{usd(amt)}</b> đã được duyệt.\n\nVí nhận: <code>{wallet}</code>\n"
    if tx_hash: text += f"Mã giao dịch (TX): <code>{tx_hash}</code>\n<a href='{tx_hash}'>👉 Xem trên Tonscan</a>\n\n"
    text += "Cảm ơn bạn đã đồng hành cùng FAST IVAS. ❤️"
    
    try:
        await bot.send_photo(uid, photo_id, caption=text)
    except Exception as e: logger.error(f"Lỗi gửi bill cho user: {e}")
    
    await call.message.edit_text(f"✅ Đã duyệt thành công đơn #{wid} và gửi bill cho User.")
    await call.answer("Duyệt thành công!")

@dp.callback_query(F.data.startswith("wd_reject_list_"))
async def cb_wd_reject_list(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    wid = int(call.data.replace("wd_reject_list_", ""))
    reasons = [("Sai địa chỉ ví TON", "wrong_wallet"), ("Ví không hỗ trợ mạng TON", "wrong_network"), ("Nghi ngờ gian lận", "fraud"), ("Sai số tiền", "wrong_amount"), ("Khác", "other")]
    buttons = [[InlineKeyboardButton(text=r[0], callback_data=f"wd_reject_conf_{wid}_{r[1]}")] for r in reasons]
    buttons.append([InlineKeyboardButton(text="⬅️ Quay lại", callback_data=f"wd_admin_view_{wid}")])
    await call.message.edit_text(f"❌ <b>CHỌN LÝ DO TỪ CHỐI ĐƠN #{wid}</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await call.answer()

@dp.callback_query(F.data.startswith("wd_reject_conf_"))
async def cb_wd_reject_conf(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    parts = call.data.replace("wd_reject_conf_", "").split("_")
    wid = int(parts[0]); reason_code = parts[1]
    reason_map = {"wrong_wallet": "Sai địa chỉ ví TON", "wrong_network": "Ví không hỗ trợ mạng TON", "fraud": "Nghi ngờ gian lận", "wrong_amount": "Sai số tiền", "other": "Khác"}
    reason_text = reason_map.get(reason_code, "Không xác định")
    db = get_db()
    try:
        row = db.execute("SELECT user_id, amount_milli FROM withdrawals WHERE id=? AND status='PENDING'", (wid,)).fetchone()
        if not row: await call.answer("Lỗi!", show_alert=True); return
        uid, amt = row
    finally: db.close()
    text = f"⚠️ <b>XÁC NHẬN HỦY</b>\n\nTừ chối đơn rút <code>#{wid}</code>.\nHoàn lại: <b>{usd(amt)}</b>.\nLý do: <b>{reason_text}</b>"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔥 XÁC NHẬN HỦY & HOÀN TIỀN", callback_data=f"wd_reject_final_{wid}_{reason_code}")], [InlineKeyboardButton(text="⬅️ Quay lại", callback_data=f"wd_admin_view_{wid}")]])
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()

@dp.callback_query(F.data.startswith("wd_reject_final_"))
async def cb_wd_reject_final(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    parts = call.data.replace("wd_reject_final_", "").split("_")
    wid = int(parts[0]); reason_code = parts[1]
    reason_text = {"wrong_wallet": "Sai địa chỉ ví TON", "wrong_network": "Ví không hỗ trợ mạng TON", "fraud": "Nghi ngờ gian lận", "wrong_amount": "Sai số tiền", "other": "Khác"}.get(reason_code, "Không xác định")
    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT user_id, amount_milli, status FROM withdrawals WHERE id=?", (wid,)).fetchone()
        if not row or row[2] != "PENDING": db.rollback(); await call.answer("Đã xử lý.", show_alert=True); return
        uid, amt = row[0], row[1]
        db.execute("UPDATE withdrawals SET status='REJECTED', processed_at=?, reject_reason=? WHERE id=?", (now_text(), reason_text, wid))
        db.execute("UPDATE users SET usd_milli=usd_milli+? WHERE user_id=?", (amt, uid))
        db.execute("INSERT INTO transactions (user_id, amount, tx_type, note, created_at) VALUES (?, ?, 'WITHDRAW_REFUND', ?, ?)", (uid, amt, f"Hoàn tiền rút #{wid}: {reason_text}", now_text()))
        db.commit()
    finally: db.close()
    await call.message.edit_text(call.message.text + "\n\n❌ <b>ĐÃ HỦY VÀ HOÀN TIỀN</b>")
    await call.answer("Đã hủy")
    try: await bot.send_message(uid, f"❌ <b>TỪ CHỐI RÚT TIỀN</b>\n\nĐơn <code>#{wid}</code> bị hủy.\nLý do: <b>{reason_text}</b>\nĐã hoàn <b>{usd(amt)}</b> vào ví.")
    except Exception: pass

@dp.message(Command("congtien"))
async def cmd_congtien(message: Message):
    try: await message.delete()
    except: pass
    if not is_admin(message.from_user.id): return
    parts = message.text.split()
    if len(parts) != 3 or not parts[1].isdigit():
        await message.answer("Dùng: <code>/congtien ID SOTIEN</code>"); return
    uid = int(parts[1]); amt = int(float(parts[2].replace("$","")) * 1000)
    u = await get_user(uid)
    if not u: await message.answer("Không tìm thấy user."); return
    db = get_db()
    try:
        cur = db.execute("INSERT INTO transactions (user_id, amount, tx_type, note, created_at) VALUES (?, ?, 'PENDING_ADD', 'Chờ user xác nhận', ?)", (uid, amt, now_text()))
        tid = cur.lastrowid; db.commit()
    finally: db.close()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Nhận Ngay", callback_data=f"acc_recv_{tid}"), InlineKeyboardButton(text="❌ Hủy", callback_data=f"acc_cancel_{tid}")]])
    try:
        await bot.send_message(uid, f"🎁 <b>BẠN NHẬN ĐƯỢC TIỀN!</b>\n\nAdmin cộng <b>{usd(amt)}</b>.\nBấm <b>Nhận Ngay</b> để vào ví.", reply_markup=kb)
        await message.answer(f"✅ Đã gửi yêu cầu cộng {usd(amt)} cho {uid}.")
    except Exception as e: await message.answer(f"❌ Lỗi: {e}")

@dp.callback_query(F.data.startswith("acc_recv_"))
async def cb_acc_recv(call: CallbackQuery):
    tid = int(call.data.replace("acc_recv_", ""))
    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT user_id, amount, tx_type FROM transactions WHERE id=?", (tid,)).fetchone()
        if not row or row[2] != "PENDING_ADD": db.rollback(); await call.answer("Lỗi!", show_alert=True); return
        uid, amt, _ = row
        db.execute("UPDATE transactions SET tx_type='ADMIN_ADD' WHERE id=?", (tid,))
        db.execute("UPDATE users SET usd_milli=usd_milli+? WHERE user_id=?", (amt, uid))
        db.commit()
    finally: db.close()
    await call.message.edit_text(f"✅ Nhận thành công <b>{usd(amt)}</b> vào ví.")
    await call.answer("Đã nhận")

@dp.callback_query(F.data.startswith("acc_cancel_"))
async def cb_acc_cancel(call: CallbackQuery):
    tid = int(call.data.replace("acc_cancel_", ""))
    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT user_id, amount, tx_type FROM transactions WHERE id=?", (tid,)).fetchone()
        if not row or row[2] != "PENDING_ADD": db.rollback(); await call.answer("Lỗi!", show_alert=True); return
        db.execute("UPDATE transactions SET tx_type='ADMIN_ADD_CANCEL' WHERE id=?", (tid,))
        db.commit()
    finally: db.close()
    await call.message.edit_text("❌ Bạn đã hủy nhận tiền.")
    await call.answer("Đã hủy")

@dp.message(Command("trutien"))
async def cmd_trutien(message: Message):
    try: await message.delete()
    except: pass
    if not is_admin(message.from_user.id): return
    parts = message.text.split()
    if len(parts) != 3 or not parts[1].isdigit():
        await message.answer("Dùng: <code>/trutien ID SOTIEN</code>"); return
    uid = int(parts[1]); amt = int(float(parts[2].replace("$","")) * 1000)
    ok, new_usd = await change_usd(uid, -amt, "ADMIN_REMOVE", "Admin thu hồi")
    if not ok: await message.answer(f"❌ {safe(new_usd)}"); return
    await message.answer(f"✅ Đã thu hồi {usd(amt)} từ {uid}.")

@dp.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    try: await message.delete()
    except: pass
    if not is_admin(message.from_user.id): return
    content = message.text.partition(" ")[2].strip()
    if not content: await message.answer("Dùng: <code>/broadcast Nội dung</code>"); return
    db = get_db()
    try: users = db.execute("SELECT user_id FROM users").fetchall()
    finally: db.close()
    sent = failed = 0
    for (uid,) in users:
        try:
            await bot.send_message(uid, "📢 <b>THÔNG BÁO</b>\n\n" + safe(content, 3500))
            sent += 1; await asyncio.sleep(0.05)
        except Exception: failed += 1
    await message.answer(f"📢 Xong. OK: {sent} · Fail: {failed}")

# =====================================================
# OTP POLLER
# =====================================================
class MkOtpPoller:
    MAX_CONSECUTIVE_ERRORS = 5
    def __init__(self):
        self.interval = max(MK_POLL_MIN_SEC, 15)
        self._consecutive_errors = 0

    async def _broadcast_otp(self, row, otp_code, full_sms, reward_milli):
        user_name = f"User {row['user_id']}"
        u = await get_user(row["user_id"])
        if u and u["first_name"]: user_name = u["first_name"]
        
        platform = detect_otp_platform(full_sms)
        btn_text = f"🔑 Xem mã OTP {platform}" if platform != "Khác" else "🔑 Xem mã OTP"
        
        kb_group = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=btn_text, callback_data=f"show_otp_{row['id']}")]
        ])
        
        # Nút cho user
        kb_user = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Sao chép OTP", copy_text=otp_code)],
            [InlineKeyboardButton(text="🔄 Lấy số mới", callback_data=f"new_num_{row['range_code']}")],
            [InlineKeyboardButton(text="⬅️ Quay lại", callback_data="home")]
        ])

        group_text = f"🔔 <b>OTP MỚI</b>\n\n👤 User: {user_link(row['user_id'], user_name)}\n📱 Số: <code>{mask_phone(row['phone'])}</code>\n📌 Nền tảng: <b>{platform}</b>\n"
        if full_sms: group_text += f"\n💬 {safe(full_sms, 300)}"
        
        user_text = f"🔔 <b>OTP MỚI</b>\n\n📦 Đơn: <code>#{row['id']}</code>\n📱 Số: <code>{row['phone']}</code>\n📌 Nền tảng: <b>{platform}</b>\n💵 Thưởng: <b>{usd(reward_milli)}</b>"
        if full_sms: user_text += f"\n\n💬 {safe(full_sms, 300)}"

        if OTP_GROUP_ID:
            try:
                g_msg = await bot.send_message(OTP_GROUP_ID, group_text, reply_markup=kb_group)
                track_msg(OTP_GROUP_ID, g_msg.message_id)
            except Exception: pass
            
        # Đã bỏ gửi cho ADMIN
        try:
            if row["user_id"] not in (ADMIN_ID, OTP_GROUP_ID):
                u_msg = await bot.send_message(row["user_id"], user_text, reply_markup=kb_user)
                track_msg(row["user_id"], u_msg.message_id)
        except Exception: pass
        if row["msg_id"]: asyncio.create_task(safe_delete_msg(row["user_id"], row["msg_id"], delay=300))

    async def _update_completed(self, oid, otp, sms, reward):
        db = get_db()
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT status FROM orders WHERE id=?", (oid,)).fetchone()
            if not row or row[0] != "PENDING":
                db.rollback()
                return
            
            db.execute("UPDATE orders SET status='COMPLETED', otp_code=?, full_sms=?, reward_milli=?, updated_at=? WHERE id=?", (otp, sms, reward, now_text(), oid))
            db.commit()
        finally: db.close()

    async def _update_failed(self, oid):
        db = get_db()
        try:
            db.execute("UPDATE orders SET status='FAILED', updated_at=? WHERE id=? AND status='PENDING'", (now_text(), oid))
            db.commit()
        finally: db.close()

    async def _poll_once(self):
        rows = await get_pending_requests(limit=MK_POLL_BATCH)
        if not rows: 
            return 0, 0, False
        
        ids = []
        by_req = {}
        for r in rows:
            try:
                rid_int = int(r["request_id"])
                ids.append(rid_int)
                by_req[rid_int] = r
            except (ValueError, TypeError):
                logger.warning(f"Lỗi parse ID đơn #{r['id']}: {r['request_id']}")
                await self._update_failed(r["id"])
        
        if not ids: return 0, 0, False
        
        logger.info(f"Đang quét {len(ids)} ID: {ids}")
        
        data, err = await api_request("POST", "check/status", {"request_ids": ids})
        
        if err: 
            logger.error(f"Lỗi API khi quét: {err}")
            return 0, 0, True
            
        inner = data.get("data") if isinstance(data, dict) else None
        results = inner.get("results") if isinstance(inner, dict) else None
        
        if not isinstance(results, list): 
            logger.warning(f"API trả về sai định dạng: {data}")
            return 0, 0, True
            
        checked = new_otp = 0
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
                    
                reward = REWARD_MILLI_PER_OTP
                
                db = get_db()
                try:
                    db.execute("BEGIN IMMEDIATE")
                    chk = db.execute("SELECT status FROM orders WHERE id=?", (row["id"],)).fetchone()
                    if not chk or chk[0] != "PENDING":
                        db.rollback()
                        continue 
                    db.execute("UPDATE orders SET status='COMPLETED', otp_code=?, full_sms=?, reward_milli=?, updated_at=? WHERE id=?", (otp, sms, reward, now_text(), row["id"]))
                    db.commit()
                finally: db.close()
                
                ok, _ = await change_usd(row["user_id"], reward, "OTP_REWARD", f"Thưởng OTP #{row['id']}")
                if not ok: reward = 0
                await self._broadcast_otp(row, otp, sms, reward)
                new_otp += 1
            elif status in ["cancel", "failed", "expired", "refunded", "not_found"]:
                await self._update_failed(row["id"])
                
        return checked, new_otp, False

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
        await call.answer("Không tìm thấy mã OTP cho đơn này!", show_alert=True); return
    platform = detect_otp_platform(row.get("full_sms", ""))
    await call.answer(f"Mã OTP {platform} của bạn là: {row['otp_code']}", show_alert=True)

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
    msg = await message.answer("Gõ /start để mở menu FAST IVAS.")
    track_msg(message.from_user.id, msg.message_id)

async def set_bot_commands():
    user_commands = [
        BotCommand(command="start", description="Mở menu chính"),
        BotCommand(command="profile", description="Xem hồ sơ"),
        BotCommand(command="wallet", description="Xem ví USD"),
        BotCommand(command="nhanso", description="Nhận số OTP (VD: /nhanso 84XXX)"),
        BotCommand(command="donhang", description="Xem đơn hàng"),
        BotCommand(command="rut", description="Menu rút USD"),
        BotCommand(command="history", description="Lịch sử giao dịch"),
        BotCommand(command="id", description="Lấy Telegram ID"),
    ]
    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

    admin_commands = user_commands + [
        BotCommand(command="admin", description="[Admin] Mở trang quản trị"),
        BotCommand(command="health", description="[Admin] Kiểm tra sức khỏe bot"),
        BotCommand(command="pollnow", description="[Admin] Ép quét OTP ngay"),
        BotCommand(command="broadcast", description="[Admin] Gửi thông báo toàn bộ"),
        BotCommand(command="congtien", description="[Admin] Cộng tiền cho user"),
        BotCommand(command="trutien", description="[Admin] Trừ tiền của user"),
        BotCommand(command="whoami", description="[Admin] Xem thông tin MK"),
        BotCommand(command="access_list", description="[Admin] Xem tuyến MK"),
        BotCommand(command="radar", description="[Admin] Xem radar MK"),
    ]
    try: await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=ADMIN_ID))
    except Exception as e: logger.error(f"Lỗi thiết lập Menu Admin: {e}")

async def main():
    global _mk_poller
    try: await set_bot_commands()
    except Exception as e: logger.error(f"Lỗi thiết lập Menu: {e}")

    await init_db(); await expire_old_orders()
    asyncio.create_task(web_server())

    if MK_POLL_ENABLED:
        _mk_poller = MkOtpPoller()
        asyncio.create_task(_mk_poller.run_forever())
        logger.info("Poller task created.")

    logger.info("FAST IVAS starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())