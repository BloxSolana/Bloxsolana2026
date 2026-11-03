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
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
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
REWARD_MILLI_PER_OTP   = 4    # $0.004
MIN_WITHDRAW_MILLI     = 3000 # $3.000

MK_POLL_ENABLED = True
MK_POLL_MIN_SEC = 8
MK_POLL_MAX_SEC = 60
MK_POLL_BATCH   = 100

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FAST_IVAS")

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp  = Dispatcher()

# DANH SÁCH 50 QUỐC GIA MẶC ĐỊNH (Fallback nếu API lỗi)
FALLBACK_COUNTRIES = {
    "Vietnam": "84XXX", "Liberia": "231XXX", "Guinea": "224XXX",
    "Sierra Leone": "232XXX", "Indonesia": "62XXX", "Cambodia": "855XXX",
    "Myanmar": "95XXX", "Zambia": "260XXX", "Tanzania": "255XXX",
    "Lesotho": "266XXX", "Mozambique": "258XXX", "Yemen": "967XXX",
    "Algeria": "213XXX", "Tunisia": "216XXX", "Nigeria": "234XXX",
    "Nepal": "977XXX", "Afghanistan": "93XXX", "Lebanon": "961XXX",
    "Morocco": "212XXX", "Libya": "218XXX", "Madagascar": "261XXX",
    "Ethiopia": "251XXX", "Senegal": "221XXX", "Zimbabwe": "263XXX",
    "Norway": "47XXX", "Egypt": "20XXX", "Palestine": "970XXX",
    "Uzbekistan": "998XXX", "Sudan": "249XXX", "Cameroon": "237XXX",
    "Benin": "229XXX", "Mali": "223XXX", "Ghana": "233XXX",
    "Kenya": "254XXX", "Uganda": "256XXX", "Rwanda": "250XXX",
    "Chad": "235XXX", "Niger": "227XXX", "Somalia": "252XXX",
    "Angola": "244XXX", "Botswana": "267XXX", "Namibia": "264XXX",
    "Gabon": "241XXX", "Congo": "242XXX", "Togo": "228XXX",
    "Burkina Faso": "226XXX", "Mauritania": "222XXX", "Gambia": "220XXX",
    "Guinea-Bissau": "245XXX", "Maldives": "960XXX"
}

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

def is_valid_ton_address(address):
    if not address: return False
    pattern = r"^(EQ|UQ)[a-zA-Z0-9_-]{46}$"
    return bool(re.match(pattern, address))

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

# =====================================================
# DATABASE KẾT NỐI TURSO
# =====================================================
def get_db():
    if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
        return libsql.connect(
            "local_replica.db", 
            sync_url=TURSO_DATABASE_URL, 
            auth_token=TURSO_AUTH_TOKEN
        )
    else:
        logger.warning("Chưa cấu hình Turso, dùng file tạm local.db")
        return libsql.connect("local.db")

async def init_db():
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT, first_name TEXT,
            usd_milli INTEGER NOT NULL DEFAULT 0,
            wallet_ton TEXT,
            referrer INTEGER, joined_at TEXT
        )""")
    
    db.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            request_id TEXT UNIQUE,
            phone TEXT, country TEXT, operator TEXT, range_code TEXT,
            status TEXT NOT NULL DEFAULT 'PENDING',
            otp_code TEXT, full_sms TEXT,
            reward_milli INTEGER NOT NULL DEFAULT 0,
            msg_id INTEGER,
            created_at TEXT, expires_at TEXT, updated_at TEXT
        )""")

    db.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, amount INTEGER NOT NULL,
            tx_type TEXT, note TEXT, created_at TEXT
        )""")

    db.execute("""
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount_milli INTEGER NOT NULL, 
            wallet_ton TEXT,
            status TEXT NOT NULL DEFAULT 'PENDING',
            reject_reason TEXT,
            created_at TEXT, processed_at TEXT
        )""")
    
    try: db.execute("ALTER TABLE withdrawals ADD COLUMN reject_reason TEXT")
    except: pass
    
    db.commit()
    db.close()

# =====================================================
# HÀM XỬ LÝ DATABASE
# =====================================================
async def register_user(tg_user, referrer=None):
    db = get_db()
    try:
        res = db.execute("SELECT user_id FROM users WHERE user_id=?", (tg_user.id,)).fetchone()
        name = tg_user.first_name or "Người dùng"
        if res:
            db.execute("UPDATE users SET username=?, first_name=? WHERE user_id=?",
                             (tg_user.username, name, tg_user.id))
            db.commit()
            return False
        if referrer == tg_user.id: referrer = None
        db.execute("""
            INSERT INTO users (user_id, username, first_name, usd_milli, referrer, joined_at)
            VALUES (?, ?, ?, 0, ?, ?)
        """, (tg_user.id, tg_user.username, name, referrer, now_text()))
        db.commit()
        return True
    finally:
        db.close()

async def get_user(uid):
    db = get_db()
    try:
        cursor = db.execute("SELECT * FROM users WHERE user_id=?", (uid,))
        row = cursor.fetchone()
        if row:
            return dict_factory(cursor, row)
        return None
    finally:
        db.close()

async def change_usd(uid, amount_milli, tx_type, note):
    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT usd_milli FROM users WHERE user_id=?", (uid,)).fetchone()
        if not row:
            db.rollback(); return False, "Không tìm thấy user."
        new = int(row[0]) + int(amount_milli)
        if new < 0:
            db.rollback(); return False, "Số dư USD không đủ."
        db.execute("UPDATE users SET usd_milli=? WHERE user_id=?", (new, uid))
        db.execute("""
            INSERT INTO transactions (user_id, amount, tx_type, note, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (uid, amount_milli, tx_type, note, now_text()))
        db.commit()
        return True, new
    finally:
        db.close()

async def get_transactions(uid, limit=15):
    db = get_db()
    try:
        return db.execute("""
            SELECT amount, tx_type, note, created_at
            FROM transactions WHERE user_id=? ORDER BY id DESC LIMIT ?
        """, (uid, limit)).fetchall()
    finally:
        db.close()

async def create_withdrawal(uid, amount_milli, wallet_ton):
    db = get_db()
    try:
        cur = db.execute("""
            INSERT INTO withdrawals (user_id, amount_milli, wallet_ton, status, created_at)
            VALUES (?, ?, ?, 'PENDING', ?)
        """, (uid, amount_milli, wallet_ton, now_text()))
        db.commit()
        return cur.lastrowid
    finally:
        db.close()

async def expire_old_orders():
    t = now_text()
    db = get_db()
    try:
        rows = db.execute("""
            SELECT id, user_id, msg_id, phone, country FROM orders 
            WHERE status='PENDING' AND expires_at IS NOT NULL AND expires_at<=?
        """, (t,)).fetchall()
        
        for r in rows:
            oid, uid, msg_id, phone, country = r
            db.execute("UPDATE orders SET status='EXPIRED', updated_at=? WHERE id=?", (t, oid))
            
            if msg_id:
                try: await bot.delete_message(chat_id=uid, message_id=msg_id)
                except: pass
            
            try:
                text = (
                    f"⌛ <b>ĐƠN HÀNG HẾT HẠN</b>\n\n"
                    f"Số: <code>{safe(phone)}</code> ({safe(country)})\n"
                    f"Trạng thái: Đã hết hạn sử dụng.\n\n"
                    f"Vui lòng chọn thao tác bên dưới:"
                )
                await bot.send_message(
                    chat_id=uid,
                    text=text,
                    reply_markup=expired_kb()
                )
            except Exception as e: logger.error(f"Lỗi gửi tin hết hạn: {e}")
        db.commit()
    finally:
        db.close()

# =====================================================
# KEYBOARDS
# =====================================================
def main_kb(uid):
    rows = [
        [InlineKeyboardButton(text="👤 Tài khoản", callback_data="menu_profile"),
         InlineKeyboardButton(text="💵 Ví USD",   callback_data="menu_wallet")],
        [InlineKeyboardButton(text="📱 Nhận số",  callback_data="menu_order_help"),
         InlineKeyboardButton(text="📦 Đơn hàng", callback_data="my_orders")],
        [InlineKeyboardButton(text="📜 Lịch sử",  callback_data="history"),
         InlineKeyboardButton(text="💸 Rút USD",  callback_data="menu_withdraw_help")],
        [InlineKeyboardButton(text="👥 Giới thiệu", callback_data="menu_referral")],
    ]
    if OTP_GROUP_URL:
        rows.append([InlineKeyboardButton(text="📢 Nhóm OTP", url=OTP_GROUP_URL)])
    if is_admin(uid):
        rows.append([InlineKeyboardButton(text="🛡 TRANG QUẢN TRỊ", callback_data="admin_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def order_help_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Quay lại", callback_data="home")]
    ])

def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Thống kê",       callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 Danh sách User", callback_data="admin_users")],
        [InlineKeyboardButton(text="📦 Đơn hàng",       callback_data="admin_orders")],
        [InlineKeyboardButton(text="💸 Duyệt Rút TON",  callback_data="admin_withdraws")],
        [InlineKeyboardButton(text="✅ Lịch sử duyệt",   callback_data="admin_withdraws_history")],
        [InlineKeyboardButton(text="⬅️ Quay lại",       callback_data="home")]
    ])

def expired_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Nhận số khác", callback_data="menu_order_help")],
        [InlineKeyboardButton(text="🌍 Đổi quốc gia khác", callback_data="list_countries")],
        [InlineKeyboardButton(text="🏠 Trang chủ", callback_data="home")]
    ])

# =====================================================
# FAST IVAS API (MK backend)
# =====================================================
HTTP_ERRORS = {
    401: "API key không hợp lệ.", 403: "API bị khoá / chờ duyệt.",
    404: "Hết số cho range này.", 405: "Sai HTTP method.",
    422: "Sai field.",            429: "Vượt rate limit.",
    500: "Lỗi nội bộ.",           503: "API tạm tắt.",
}

async def api_request(method, endpoint, payload=None, params=None):
    headers = {"mknetwork-key": MK_API_KEY, "Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
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
                    logger.warning(err); return None, err
                if isinstance(data, dict) and data.get("success") is False:
                    return None, str(data.get("message") or "API lỗi")
                return data, None
    except asyncio.TimeoutError:
        return None, "FAST IVAS timeout."
    except Exception:
        logger.exception("API fail"); return None, "Không kết nối được FAST IVAS."

async def api_get(ep, params=None): return await api_request("GET", ep, params=params)

def unwrap(d):
    if not isinstance(d, dict): return {}
    for k in ("data", "result", "response"):
        v = d.get(k)
        if isinstance(v, dict): return v
    return d

def field(d, *names, default=""):
    if not isinstance(d, dict): return default
    for src in (d, unwrap(d)):
        for n in names:
            if src.get(n) is not None: return src[n]
    return default

def strip_secrets(obj):
    blocked = {"otp","otp_code","code","full_sms","sms","message",
               "api_key","token","authorization","password"}
    if isinstance(obj, dict):
        return {k: strip_secrets(v) for k, v in obj.items() if k.lower() not in blocked}
    if isinstance(obj, list):
        return [strip_secrets(x) for x in obj[:30]]
    return obj

def fmt_api(d):
    return html.escape(json.dumps(strip_secrets(d), ensure_ascii=False, indent=2, default=str)[:3500])

# =====================================================
# CREATE ORDER
# =====================================================
async def create_number_order(uid, range_code, msg_id=None):
    if not range_code or len(range_code) > 80 or any(c.isspace() for c in range_code):
        return False, "Mã tuyến không hợp lệ."

    data, err = await api_request("POST", "getnum/number", {"range": range_code})
    if err: return False, err

    rid      = field(data, "request_id", "requestId", "id")
    phone    = field(data, "number", "phone", "phone_number")
    country  = field(data, "country", "country_name")
    operator = field(data, "operator", "network", "carrier")

    if not rid: return False, "API thiếu request_id."

    exp = (now() + timedelta(minutes=ORDER_LIFETIME_MINUTES)).isoformat(timespec="seconds")
    db = get_db()
    try:
        db.execute("""
            INSERT INTO orders (user_id, request_id, phone, country, operator,
                range_code, status, created_at, expires_at, updated_at, msg_id)
            VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?, ?, ?, ?)
        """, (uid, str(rid), str(phone or "N/A"), str(country or "?"),
              str(operator or "?"), range_code, now_text(), exp, now_text(), msg_id))
        db.commit()
    except Exception as e:
        logger.error(f"Lỗi insert order: {e}")
        return False, "Lỗi Database."
    finally:
        db.close()

    return True, {
        "request_id": rid, "phone": phone or "N/A",
        "country": country or "?", "operator": operator or "?",
        "expires_at": exp,
    }

# =====================================================
# ORDER DB HELPERS
# =====================================================
async def get_user_orders(uid, limit=10):
    await expire_old_orders()
    db = get_db()
    try:
        return db.execute("""
            SELECT id, request_id, phone, country, operator,
                   status, created_at, expires_at
            FROM orders WHERE user_id=? ORDER BY id DESC LIMIT ?
        """, (uid, limit)).fetchall()
    finally:
        db.close()

async def get_order(oid, uid=None):
    db = get_db()
    try:
        if uid is None:
            cursor = db.execute("SELECT * FROM orders WHERE id=?", (oid,))
        else:
            cursor = db.execute("SELECT * FROM orders WHERE id=? AND user_id=?", (oid, uid))
        row = cursor.fetchone()
        if row:
            return dict_factory(cursor, row)
        return None
    finally:
        db.close()

async def get_all_orders(limit=15):
    await expire_old_orders()
    db = get_db()
    try:
        return db.execute("""
            SELECT id, user_id, request_id, phone, status
            FROM orders ORDER BY id DESC LIMIT ?
        """, (limit,)).fetchall()
    finally:
        db.close()

async def get_pending_requests(limit=100):
    db = get_db()
    try:
        rows = db.execute("""
            SELECT id, user_id, request_id, phone, msg_id
            FROM orders WHERE status='PENDING' ORDER BY id ASC LIMIT ?
        """, (limit,)).fetchall()
        results = []
        for r in rows:
            results.append({
                "id": r[0], "user_id": r[1], "request_id": r[2], 
                "phone": r[3], "msg_id": r[4]
            })
        return results
    finally:
        db.close()

def fmt_order(row):
    extra = ""
    if row["status"] == "COMPLETED":
        try:
            if row["otp_code"]:    extra += f"\n🔑 OTP: <code>{safe(row['otp_code'])}</code>"
            if row["full_sms"]:    extra += f"\n💬 SMS: {safe(row['full_sms'], 200)}"
            if row["reward_milli"]: extra += f"\n💵 Thưởng: <b>{usd(row['reward_milli'])}</b>"
        except (IndexError, KeyError): pass
    return (
        f"📦 <b>ĐƠN #{row['id']}</b>\n"
        f"Request ID: <code>{safe(row['request_id'])}</code>\n"
        f"Số: <code>{safe(row['phone'])}</code>\n"
        f"Quốc gia: {safe(row['country'])}\n"
        f"Nhà mạng: {safe(row['operator'])}\n"
        f"Trạng thái: {status_text(row['status'])}\n"
        f"Hết hạn: {safe(row['expires_at'])}"
        f"{extra}"
    )

# =====================================================
# START / HELP / COMMANDS
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
    
    await message.answer(
        "🚀 <b>FAST IVAS</b>\n\nChào mừng bạn!\nChọn chức năng:",
        reply_markup=main_kb(message.from_user.id)
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    try: await message.delete()
    except: pass
    await message.answer(
        "<b>FAST IVAS — Hướng dẫn</b>\n\n"
        "/start — Menu\n/profile — Hồ sơ\n/wallet — Ví USD\n"
        "/nhanso RANGE — Nhận số OTP\n/donhang [ID] — Xem đơn\n"
        "/rut SOTIEN DIA_CHI_TON — Rút USD (min $3)\n"
        "/history — Lịch sử\n/id — Telegram ID\n\n"
        f"💵 <b>{usd(REWARD_MILLI_PER_OTP)}</b>/OTP · "
        f"💸 Rút min <b>{usd(MIN_WITHDRAW_MILLI)}</b>"
    )

@dp.message(Command("id"))
async def cmd_id(message: Message):
    try: await message.delete()
    except: pass
    await message.answer(f"Telegram ID: <code>{message.from_user.id}</code>")

@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    try: await message.delete()
    except: pass
    await register_user(message.from_user)
    u = await get_user(message.from_user.id)
    await message.answer(
        "👤 <b>HỒ SƠ</b>\n\n"
        f"ID: <code>{u['user_id']}</code>\n"
        f"Tên: {safe(u['first_name'])}\n"
        f"Username: @{safe(u['username'] or '—')}\n"
        f"Ngày tham gia: {safe(u['joined_at'][:10])}\n\n"
        f"💵 Số dư USD: <b>{usd(u['usd_milli'])}</b>"
    )

@dp.message(Command("wallet"))
async def cmd_wallet(message: Message):
    try: await message.delete()
    except: pass
    await register_user(message.from_user)
    u = await get_user(message.from_user.id)
    await message.answer(
        "💵 <b>VÍ USD (từ OTP)</b>\n\n"
        f"Số dư: <b>{usd(u['usd_milli'])}</b>\n"
        f"Thưởng/OTP: <b>{usd(REWARD_MILLI_PER_OTP)}</b>\n"
        f"Rút min: <b>{usd(MIN_WITHDRAW_MILLI)}</b>\n\n"
        "Lệnh rút: <code>/rut SOTIEN DIA_CHI_VI_TON</code>\n"
        "VD: <code>/rut 3.5 UQ...</code>"
    )

# =====================================================
# CALLBACKS
# =====================================================
@dp.callback_query(F.data == "home")
async def cb_home(call: CallbackQuery):
    await call.message.edit_text(
        "🚀 <b>FAST IVAS</b>\n\nChọn chức năng:", 
        reply_markup=main_kb(call.from_user.id)
    )
    await call.answer()

@dp.callback_query(F.data == "menu_order_help")
async def cb_menu_order_help(call: CallbackQuery):
    await call.answer("Đang tải danh sách lệnh tham khảo...")
    
    # Lấy dữ liệu từ API MK
    data, err = await api_get("access_list", params={"limit": 200})
    cmd_list = ""
    country_dict = {}
    
    if not err:
        items = data.get("data", {}).get("items", [])
        for item in items:
            c_name = item.get("country")
            r_code = item.get("range")
            if c_name and r_code and c_name not in country_dict:
                country_dict[c_name] = r_code
    
    # Nếu không lấy được từ API (hoặc API trả rỗng), dùng danh sách Fallback có sẵn
    if not country_dict:
        country_dict = FALLBACK_COUNTRIES

    # Lấy ngẫu nhiên 50 quốc gia
    all_c = list(country_dict.keys())
    random.shuffle(all_c)
    selected_c = all_c[:50]

    # Tạo list lệnh
    for c_name in selected_c:
        r_code = country_dict[c_name]
        cmd_list += f"🌍 {c_name}: <code>/nhanso {r_code}</code>\n"

    text = (
        "📱 <b>NHẬN SỐ OTP</b>\n\n"
        "Bạn có thể gõ lệnh thủ công, hoặc bấm nút <b>Chọn Quốc Gia</b> bên dưới để lấy số tự động.\n\n"
        "<b>DANH SÁCH LỆNH THAM KHẢO (50 nước ngẫu nhiên):</b>\n"
        f"{cmd_list}"
    )

    await call.message.edit_text(text, reply_markup=order_help_kb())
    await call.answer()

@dp.callback_query(F.data == "menu_profile")
async def cb_menu_profile(call: CallbackQuery):
    await register_user(call.from_user)
    u = await get_user(call.from_user.id)
    await call.message.edit_text(
        "👤 <b>HỒ SƠ</b>\n\n"
        f"ID: <code>{u['user_id']}</code>\n"
        f"Tên: {safe(u['first_name'])}\n"
        f"Username: @{safe(u['username'] or '—')}\n"
        f"Ngày tham gia: {safe(u['joined_at'][:10])}\n\n"
        f"💵 Số dư USD: <b>{usd(u['usd_milli'])}</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Quay lại", callback_data="home")]
        ])
    )
    await call.answer()

@dp.callback_query(F.data == "menu_wallet")
async def cb_menu_wallet(call: CallbackQuery):
    await register_user(call.from_user)
    u = await get_user(call.from_user.id)
    await call.message.edit_text(
        "💵 <b>VÍ USD</b>\n\n"
        f"Số dư: <b>{usd(u['usd_milli'])}</b>\n"
        f"Thưởng/OTP: <b>{usd(REWARD_MILLI_PER_OTP)}</b>\n"
        f"Rút min: <b>{usd(MIN_WITHDRAW_MILLI)}</b>\n\n"
        "Lệnh rút: <code>/rut 3.5 UQ...</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Quay lại", callback_data="home")]
        ])
    )
    await call.answer()

@dp.callback_query(F.data == "menu_withdraw_help")
async def cb_menu_withdraw_help(call: CallbackQuery):
    await call.message.edit_text(
        "💸 <b>RÚT USD QUA MẠNG TON</b>\n\n"
        "Cú pháp: <code>/rut SOTIEN DIA_CHI_TON</code>\n\n"
        "VD: <code>/rut 3.5 UQ...</code>\n\n"
        f"Min rút: <b>{usd(MIN_WITHDRAW_MILLI)}</b>\n"
        "⚠️ Lưu ý: Chỉ hỗ trợ mạng TON. Nhập sai địa chỉ sẽ mất tiền!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Quay lại", callback_data="home")]
        ])
    )
    await call.answer()

@dp.callback_query(F.data == "menu_referral")
async def cb_menu_referral(call: CallbackQuery):
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={call.from_user.id}"
    await call.message.edit_text(
        "👥 <b>GIỚI THIỆU</b>\n\n"
        f"<code>{link}</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Quay lại", callback_data="home")]
        ])
    )
    await call.answer()


@dp.callback_query(F.data == "list_countries")
async def cb_list_countries(call: CallbackQuery):
    await call.answer("Đang tải...")
    
    data, err = await api_get("access_list", params={"limit": 200})
    country_dict = {}
    
    if not err:
        items = data.get("data", {}).get("items", [])
        for item in items:
            c_name = item.get("country")
            r_code = item.get("range")
            if c_name and r_code:
                if c_name not in country_dict:
                    country_dict[c_name] = []
                country_dict[c_name].append(r_code)
    
    # Fallback nếu không có dữ liệu
    if not country_dict:
        country_dict = {k: [v] for k, v in FALLBACK_COUNTRIES.items()}

    buttons = []
    c_list = list(country_dict.keys())
    
    # Chia 2 cột và hiển thị mã Range
    for i in range(0, len(c_list), 2):
        row = []
        c1 = c_list[i]
        r1 = country_dict[c1][0]
        row.append(InlineKeyboardButton(text=f"🌍 {c1} ({r1})", callback_data=f"rng_{r1}"))
        
        if i + 1 < len(c_list):
            c2 = c_list[i+1]
            r2 = country_dict[c2][0]
            row.append(InlineKeyboardButton(text=f"🌍 {c2} ({r2})", callback_data=f"rng_{r2}"))
        
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton(text="⬅️ Quay lại", callback_data="menu_order_help")])

    await call.message.edit_text(
        "🌍 <b>CHỌN QUỐC GIA</b>\n\n"
        "Bấm vào quốc gia để nhận số ngay lập tức (Mã trong ngoặc là Range):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@dp.callback_query(F.data.startswith("rng_"))
async def cb_choose_range(call: CallbackQuery):
    range_code = call.data.replace("rng_", "")
    await call.answer("Đang lấy số...")
    
    ok, res = await create_number_order(call.from_user.id, range_code, msg_id=call.message.message_id)
    if not ok:
        await call.message.edit_text(f"❌ {safe(res)}", reply_markup=order_help_kb())
        return

    await call.message.edit_text(
        "✅ <b>ĐÃ NHẬN SỐ</b>\n\n"
        f"Số: <code>{res['phone']}</code>\n"
        f"Quốc gia: {safe(res['country'])}\n"
        f"Hết hạn: {safe(res['expires_at'])}\n\n"
        "⏳ Đang chờ OTP...",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌍 Đổi quốc gia", callback_data="list_countries")]
        ])
    )

@dp.message(Command("nhanso"))
async def cmd_nhanso(message: Message):
    try: await message.delete()
    except: pass
    await register_user(message.from_user)
    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        await message.answer("Cú pháp: <code>/nhanso MA_TUYEN</code>")
        return

    waiting_msg = await message.answer("⏳ Đang gửi yêu cầu…")
    ok, res = await create_number_order(message.from_user.id, parts[1].strip(), msg_id=waiting_msg.message_id)
    
    if not ok:
        await waiting_msg.edit_text(f"❌ {safe(res)}")
        return

    await waiting_msg.edit_text(
        "✅ <b>ĐÃ NHẬN SỐ</b>\n\n"
        f"Số: <code>{res['phone']}</code>\n"
        f"Quốc gia: {safe(res['country'])}\n"
        f"Hết hạn: {safe(res['expires_at'])}\n\n"
        "⏳ Đang chờ OTP...",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌍 Đổi quốc gia", callback_data="list_countries")]
        ])
    )

# =====================================================
# ADMIN PANEL
# =====================================================
@dp.callback_query(F.data == "admin_menu")
async def cb_admin_menu(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Không có quyền.", show_alert=True); return
    await call.message.edit_text("🛡 <b>FAST IVAS ADMIN</b>", reply_markup=admin_kb())
    await call.answer()

@dp.callback_query(F.data.startswith("admin_"))
async def cb_admin(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Không có quyền.", show_alert=True); return

    if call.data == "admin_stats":
        await expire_old_orders()
        db = get_db()
        try:
            users    = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            tot_usd  = db.execute("SELECT COALESCE(SUM(usd_milli),0) FROM users").fetchone()[0]
            orders   = db.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
            pending  = db.execute("SELECT COUNT(*) FROM orders WHERE status='PENDING'").fetchone()[0]
            completed= db.execute("SELECT COUNT(*) FROM orders WHERE status='COMPLETED'").fetchone()[0]
            wd       = db.execute("SELECT COUNT(*) FROM withdrawals WHERE status='PENDING'").fetchone()[0]
            
            text = (
                "📊 <b>THỐNG KÊ</b>\n\n"
                f"👥 Users: <b>{users}</b>\n"
                f"📦 Đơn: <b>{orders}</b> (chờ <b>{pending}</b>, xong <b>{completed}</b>)\n"
                f"💵 USD tổng: <b>{usd(tot_usd)}</b>\n"
                f"💸 Rút chờ: <b>{wd}</b>"
            )
            await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Quay lại", callback_data="admin_menu")]
            ]))
        finally: db.close()

    elif call.data == "admin_users":
        db = get_db()
        try:
            users = db.execute("""
                SELECT joined_at, user_id, first_name FROM users ORDER BY joined_at DESC LIMIT 50
            """).fetchall()
            if not users:
                text = "Chưa có user nào."
            else:
                lines = ["👥 <b>DANH SÁCH USER MỚI NHẤT</b>\n"]
                for joined, uid, name in users:
                    time_str = joined[:16].replace("T", " ") if joined else "N/A"
                    lines.append(f"📅 {time_str} | <code>{uid}</code>\n👤 Tên: {safe(name)}\n")
                text = "\n".join(lines)
            
            await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Quay lại", callback_data="admin_menu")]
            ]))
        finally: db.close()

    elif call.data == "admin_orders":
        rows = await get_all_orders()
        if not rows:
            text = "Chưa có đơn."
        else:
            lines = ["📦 <b>ĐƠN GẦN ĐÂY</b>\n"]
            for r in rows:
                lines.append(
                    f"#{r[0]} | User <code>{r[1]}</code>\n"
                    f"Request: <code>{safe(r[2])}</code>\n"
                    f"Số: <code>{safe(r[3])}</code>\n"
                    f"Status: {safe(r[4])}"
                )
            text = "\n\n".join(lines)
            
        await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Quay lại", callback_data="admin_menu")]
        ]))

    elif call.data == "admin_withdraws":
        db = get_db()
        try:
            rows = db.execute("""
                SELECT w.id, w.user_id, w.amount_milli, w.wallet_ton, u.first_name 
                FROM withdrawals w
                JOIN users u ON w.user_id = u.user_id
                WHERE w.status='PENDING' ORDER BY w.id DESC LIMIT 15
            """).fetchall()
            if not rows:
                await call.message.edit_text("Không có yêu cầu rút TON nào đang chờ.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Quay lại", callback_data="admin_menu")]
                ]))
            else:
                buttons = []
                for i, (rid, uid, amt, wallet, name) in enumerate(rows, 1):
                    buttons.append([InlineKeyboardButton(
                        text=f"{i}. {name} ({usd(amt)})", 
                        callback_data=f"wd_detail_{rid}"
                    )])
                buttons.append([InlineKeyboardButton(text="⬅️ Quay lại", callback_data="admin_menu")])
                
                await call.message.edit_text(
                    "💸 <b>DANH SÁCH YÊU CẦU RÚT TON</b>\n\n"
                    "Bấm vào tên User để xem chi tiết và xử lý:",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
                )
        finally: db.close()

    elif call.data == "admin_withdraws_history":
        db = get_db()
        try:
            rows = db.execute("""
                SELECT w.id, w.user_id, w.amount_milli, w.status, w.processed_at, w.reject_reason, u.first_name 
                FROM withdrawals w
                JOIN users u ON w.user_id = u.user_id
                WHERE w.status IN ('APPROVED', 'REJECTED') 
                ORDER BY w.processed_at DESC LIMIT 20
            """).fetchall()
            if not rows:
                text = "Chưa có lịch sử duyệt nào."
            else:
                lines = ["📜 <b>LỊCH SỬ DUYỆT RÚT TON</b>\n"]
                for rid, uid, amt, status, p_at, reason, name in rows:
                    icon = "✅" if status == "APPROVED" else "❌"
                    time_str = p_at[:16].replace("T", " ") if p_at else "N/A"
                    note = f" - Lý do: {reason}" if reason else ""
                    lines.append(
                        f"{icon} <b>Đơn #{rid}</b> | {time_str}\n"
                        f"👤 User: {name} (<code>{uid}</code>)\n"
                        f"💵 {usd(amt)}{note}\n"
                    )
                text = "\n".join(lines)
                
            await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Quay lại", callback_data="admin_menu")]
            ]))
        finally: db.close()

    await call.answer()

# === XỬ LÝ CHI TIẾT ĐƠN RÚT ===
@dp.callback_query(F.data.startswith("wd_detail_"))
async def cb_wd_detail(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    wid = int(call.data.replace("wd_detail_", ""))
    
    db = get_db()
    try:
        row = db.execute("""
            SELECT w.id, w.user_id, w.amount_milli, w.wallet_ton, w.status, u.first_name 
            FROM withdrawals w
            JOIN users u ON w.user_id = u.user_id
            WHERE w.id=?
        """, (wid,)).fetchone()
        
        if not row or row[4] != "PENDING":
            await call.answer("Đơn này đã được xử lý!", show_alert=True)
            return
            
        rid, uid, amt, wallet, status, name = row
        
        text = (
            f"💸 <b>CHI TIẾT YÊU CẦU RÚT TON</b>\n\n"
            f"Mã đơn: <code>#{rid}</code>\n"
            f"User: <b>{name}</b> (<code>{uid}</code>)\n"
            f"Số tiền: <b>{usd(amt)}</b>\n"
            f"Ví TON: <code>{wallet}</code>"
        )
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Duyệt (Đã chuyển tiền)", callback_data=f"wd_approve_{rid}")],
            [InlineKeyboardButton(text="❌ Hủy duyệt / Từ chối", callback_data=f"wd_reject_list_{rid}")],
            [InlineKeyboardButton(text="⬅️ Quay lại", callback_data="admin_withdraws")]
        ])
        
        await call.message.edit_text(text, reply_markup=kb)
    finally:
        db.close()
    await call.answer()

# === DUYỆT ĐƠN ===
@dp.callback_query(F.data.startswith("wd_approve_"))
async def cb_wd_approve(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    wid = int(call.data.replace("wd_approve_", ""))
    
    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT user_id, amount_milli, status FROM withdrawals WHERE id=?", (wid,)).fetchone()
        if not row or row[2] != "PENDING":
            db.rollback()
            await call.answer("Đã xử lý hoặc không tìm thấy.", show_alert=True); return
        uid, amt = row[0], row[1]
        db.execute("UPDATE withdrawals SET status='APPROVED', processed_at=? WHERE id=?", (now_text(), wid))
        db.commit()
    finally:
        db.close()
        
    await call.message.edit_text(call.message.text + "\n\n✅ <b>ĐÃ DUYỆT THANH TOÁN</b>")
    await call.answer("Đã duyệt")
    try: 
        await bot.send_message(
            uid, 
            f"✅ <b>THÔNG BÁO</b>\n\n"
            f"Yêu cầu rút TON mã <code>#{wid}</code> của bạn ({usd(amt)}) đã được xử lý thanh toán thành công.\n"
            f"Vui lòng kiểm tra ví TON của bạn."
        )
    except Exception: pass

# === MENU LÝ DO TỪ CHỐI ===
@dp.callback_query(F.data.startswith("wd_reject_list_"))
async def cb_wd_reject_list(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    wid = int(call.data.replace("wd_reject_list_", ""))
    
    reasons = [
        ("Sai địa chỉ ví TON", "wrong_wallet"),
        ("Ví không hỗ trợ mạng TON", "wrong_network"),
        ("Nghi ngờ gian lận (Bug/Cheat)", "fraud"),
        ("Sai số tiền / Lỗi hệ thống", "wrong_amount"),
        ("Khác (Admin tự nhập sau)", "other")
    ]
    
    buttons = []
    for r_text, r_code in reasons:
        buttons.append([InlineKeyboardButton(text=r_text, callback_data=f"wd_reject_conf_{wid}_{r_code}")])
        
    buttons.append([InlineKeyboardButton(text="⬅️ Quay lại", callback_data=f"wd_detail_{wid}")])
    
    await call.message.edit_text(
        f"❌ <b>CHỌN LÝ DO TỪ CHỐI ĐƠN #{wid}</b>\n\n"
        f"Vui lòng chọn lý do để thông báo cho User:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await call.answer()

# === XÁC NHẬN TỪ CHỐI ===
@dp.callback_query(F.data.startswith("wd_reject_conf_"))
async def cb_wd_reject_conf(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    parts = call.data.replace("wd_reject_conf_", "").split("_")
    wid = int(parts[0])
    reason_code = parts[1]
    
    reason_map = {
        "wrong_wallet": "Sai địa chỉ ví TON",
        "wrong_network": "Ví không hỗ trợ mạng TON",
        "fraud": "Nghi ngờ gian lận",
        "wrong_amount": "Sai số tiền / Lỗi hệ thống",
        "other": "Lý do khác từ Admin"
    }
    reason_text = reason_map.get(reason_code, "Không xác định")
    
    db = get_db()
    try:
        row = db.execute("SELECT user_id, amount_milli FROM withdrawals WHERE id=? AND status='PENDING'", (wid,)).fetchone()
        if not row:
            await call.answer("Đơn không tồn tại hoặc đã xử lý!", show_alert=True)
            return
        uid, amt = row
    finally:
        db.close()
        
    text = (
        f"⚠️ <b>XÁC NHẬN HỦY DUYỆT</b>\n\n"
        f"Bạn chuẩn bị từ chối đơn rút <code>#{wid}</code>.\n"
        f"Số tiền: <b>{usd(amt)}</b> sẽ được hoàn lại vào ví USD của User.\n"
        f"Lý do: <b>{reason_text}</b>\n\n"
        f"Bạn có chắc chắn muốn thực hiện?"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 XÁC NHẬN HỦY & HOÀN TIỀN", callback_data=f"wd_reject_final_{wid}_{reason_code}")],
        [InlineKeyboardButton(text="⬅️ Quay lại", callback_data=f"wd_detail_{wid}")]
    ])
    
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()

# === THỰC HIỆN TỪ CHỐI ===
@dp.callback_query(F.data.startswith("wd_reject_final_"))
async def cb_wd_reject_final(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    parts = call.data.replace("wd_reject_final_", "").split("_")
    wid = int(parts[0])
    reason_code = parts[1]
    
    reason_map = {
        "wrong_wallet": "Sai địa chỉ ví TON",
        "wrong_network": "Ví không hỗ trợ mạng TON",
        "fraud": "Nghi ngờ gian lận",
        "wrong_amount": "Sai số tiền / Lỗi hệ thống",
        "other": "Lý do khác từ Admin"
    }
    reason_text = reason_map.get(reason_code, "Không xác định")
    
    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT user_id, amount_milli, status FROM withdrawals WHERE id=?", (wid,)).fetchone()
        if not row or row[2] != "PENDING":
            db.rollback()
            await call.answer("Đã xử lý hoặc không tìm thấy.", show_alert=True); return
        uid, amt = row[0], row[1]
        
        # Cập nhật trạng thái từ chối
        db.execute("UPDATE withdrawals SET status='REJECTED', processed_at=?, reject_reason=? WHERE id=?", 
                   (now_text(), reason_text, wid))
        
        # Hoàn tiền
        db.execute("UPDATE users SET usd_milli=usd_milli+? WHERE user_id=?", (amt, uid))
        db.execute("""
            INSERT INTO transactions (user_id, amount, tx_type, note, created_at)
            VALUES (?, ?, 'WITHDRAW_REFUND', ?, ?)
        """, (uid, amt, f"Hoàn tiền rút TON #{wid} bị từ chối: {reason_text}", now_text()))
        db.commit()
    finally:
        db.close()
        
    await call.message.edit_text(call.message.text + "\n\n❌ <b>ĐÃ HỦY VÀ HOÀN TIỀN</b>")
    await call.answer("Đã hủy đơn")
    try: 
        await bot.send_message(
            uid, 
            f"❌ <b>THÔNG BÁO TỪ CHỐI RÚT TIỀN</b>\n\n"
            f"Yêu cầu rút TON mã <code>#{wid}</code> của bạn đã bị hủy.\n"
            f"Lý do: <b>{reason_text}</b>\n\n"
            f"Số tiền <b>{usd(amt)}</b> đã được hoàn lại vào ví USD của bạn."
        )
    except Exception: pass


# =====================================================
# WITHDRAW / HISTORY (Phía User)
# =====================================================
def parse_usd(text):
    m = re.fullmatch(r"(\d+)(?:\.(\d{1,3}))?", str(text).strip().replace(",", "."))
    if not m: return None
    frac = ((m.group(2) or "") + "000")[:3]
    return int(m.group(1)) * 1000 + int(frac)

@dp.message(Command("rut"))
async def cmd_rut(message: Message):
    try: await message.delete()
    except: pass
    await register_user(message.from_user)
    parts = message.text.split()
    
    if len(parts) != 3:
        await message.answer(
            "Cú pháp: <code>/rut SOTIEN DIA_CHI_TON</code>\n"
            "VD: <code>/rut 3.5 UQ...</code>"
        )
        return

    amt = parse_usd(parts[1])
    ton_wallet = parts[2].strip()

    if amt is None or amt <= 0:
        await message.answer("Số tiền không hợp lệ."); return
    if amt < MIN_WITHDRAW_MILLI:
        await message.answer(f"❌ Min rút là {usd(MIN_WITHDRAW_MILLI)}."); return

    if not is_valid_ton_address(ton_wallet):
        await message.answer(
            "❌ <b>ĐỊA CHỈ VÍ TON KHÔNG HỢP LỆ!</b>\n\n"
            "Địa chỉ ví TON chuẩn thường dài 48 ký tự và bắt đầu bằng <code>UQ</code> hoặc <code>EQ</code>.\n"
            "Vui lòng kiểm tra lại để tránh mất tiền."
        )
        return

    u = await get_user(message.from_user.id)
    if int(u["usd_milli"]) < amt:
        await message.answer(f"❌ Số dư không đủ. Hiện có: <b>{usd(u['usd_milli'])}</b>")
        return

    ok, new_usd = await change_usd(message.from_user.id, -amt, "WITHDRAW_HOLD", "Yêu cầu rút TON")
    if not ok:
        await message.answer(safe(new_usd)); return

    wid = await create_withdrawal(message.from_user.id, amt, ton_wallet)
    await message.answer(
        "✅ <b>YÊU CẦU RÚT ĐÃ TẠO</b>\n\n"
        f"Mã: <code>#{wid}</code>\n"
        f"Số tiền: <b>{usd(amt)}</b>\n"
        f"Ví TON: <code>{ton_wallet}</code>\n"
        f"Còn lại: <b>{usd(new_usd)}</b>\n"
        "Vui lòng chờ Admin duyệt."
    )
    
    try:
        admin_text = (
            f"💸 <b>YÊU CẦU RÚT MỚI</b>\n\n"
            f"Mã: <code>#{wid}</code>\n"
            f"User: <code>{message.from_user.id}</code>\n"
            f"Số tiền: <b>{usd(amt)}</b>\n"
            f"Ví TON: <code>{ton_wallet}</code>"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👉 Bấm vào đây để xử lý", callback_data=f"wd_detail_{wid}")]
        ])
        await bot.send_message(ADMIN_ID, admin_text, reply_markup=kb)
    except Exception as e:
        logger.error(f"Lỗi gửi thông báo rút cho admin: {e}")

@dp.callback_query(F.data == "history")
async def cb_history(call: CallbackQuery):
    rows = await get_transactions(call.from_user.id)
    text = "📜 <b>LỊCH SỬ</b>\n\nChưa có giao dịch." if not rows else \
        "\n".join(["📜 <b>LỊCH SỬ</b>\n"] + [tx_line(*r[:3]) for r in rows])
    await call.message.edit_text(
        text, 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Quay lại", callback_data="home")]
        ])
    )
    await call.answer()

def tx_line(amount, tx_type, note):
    sign = "+" if amount >= 0 else ""
    return f"• {sign}{usd(amount)} | {safe(tx_type)}\n  {safe(note)}"

# =====================================================
# ADMIN COMMANDS
# =====================================================
@dp.message(Command("adminorder"))
async def cmd_adminorder(message: Message):
    try: await message.delete()
    except: pass
    if not is_admin(message.from_user.id): return
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Dùng: <code>/adminorder ID</code>"); return
    row = await get_order(int(parts[1]))
    if not row:
        await message.answer("Không tìm thấy đơn."); return
    await message.answer(fmt_order(row))

async def _set_order_status(oid, new):
    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT user_id, status FROM orders WHERE id=?", (oid,)).fetchone()
        if not row: db.rollback(); return None
        uid, old = row
        if old != "PENDING":
            db.rollback(); return False
        db.execute("UPDATE orders SET status=?, updated_at=? WHERE id=? AND status='PENDING'",
                         (new, now_text(), oid))
        db.commit()
        return uid
    finally:
        db.close()

@dp.message(Command("hoanthanh"))
async def cmd_hoanthanh(message: Message):
    try: await message.delete()
    except: pass
    if not is_admin(message.from_user.id): return
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Dùng: <code>/hoanthanh ID</code>"); return
    uid = await _set_order_status(int(parts[1]), "COMPLETED")
    if uid is None: await message.answer("Không tìm thấy đơn."); return
    if uid is False: await message.answer("Đơn không PENDING."); return
    await message.answer(f"✅ Đã set đơn #{parts[1]} = COMPLETED.")

@dp.message(Command("thatbai"))
async def cmd_thatbai(message: Message):
    try: await message.delete()
    except: pass
    if not is_admin(message.from_user.id): return
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Dùng: <code>/thatbai ID</code>"); return
    uid = await _set_order_status(int(parts[1]), "FAILED")
    if uid is None: await message.answer("Không tìm thấy đơn."); return
    if uid is False: await message.answer("Đơn không PENDING."); return
    await message.answer(f"❌ Đã set đơn #{parts[1]} = FAILED.")

@dp.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    try: await message.delete()
    except: pass
    if not is_admin(message.from_user.id): return
    content = message.text.partition(" ")[2].strip()
    if not content:
        await message.answer("Dùng: <code>/broadcast Nội dung</code>"); return
    db = get_db()
    try:
        users = db.execute("SELECT user_id FROM users").fetchall()
    finally: db.close()
    
    sent = failed = 0
    for (uid,) in users:
        try:
            await bot.send_message(uid, "📢 <b>THÔNG BÁO</b>\n\n" + safe(content, 3500))
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
    await message.answer(f"📢 Xong. OK: {sent} · Fail: {failed}")

_mk_poller = None

@dp.message(Command("pollnow"))
async def cmd_pollnow(message: Message):
    try: await message.delete()
    except: pass
    if not is_admin(message.from_user.id): return
    if not _mk_poller:
        await message.answer("Poller chưa chạy."); return
    await message.answer("🔄 Polling…")
    try:
        c, n, err = await _mk_poller._poll_once()
        if err: await message.answer("⚠️ Lỗi API.")
        else:   await message.answer(f"✅ Checked: {c} · OTP mới: {n}")
    except Exception as e:
        await message.answer(f"❌ {safe(str(e))}")

@dp.message(Command("health"))
async def cmd_health(message: Message):
    try: await message.delete()
    except: pass
    if not is_admin(message.from_user.id): return
    db = get_db()
    try:
        pending = db.execute("SELECT COUNT(*) FROM orders WHERE status='PENDING'").fetchone()[0]
    finally: db.close()
    poller = "OFF" if not _mk_poller else f"ON ({_mk_poller.interval}s, err={_mk_poller._consecutive_errors})"
    await message.answer(
        "🟢 <b>FAST IVAS ONLINE</b>\n\n"
        f"DB: <code>Turso Cloud</code>\n"
        f"API key: {'✓' if MK_API_KEY else '✗'}\n"
        f"OTP group ID: <code>{OTP_GROUP_ID}</code>\n"
        f"Đơn chờ: <b>{pending}</b>\n"
        f"Poller: {safe(poller)}\n"
        f"Thưởng/OTP: <b>{usd(REWARD_MILLI_PER_OTP)}</b>\n"
        f"Min rút: <b>{usd(MIN_WITHDRAW_MILLI)}</b>"
    )

# =====================================================
# OTP POLLER
# =====================================================
class MkOtpPoller:
    MAX_CONSECUTIVE_ERRORS = 5

    def __init__(self):
        self.interval = max(MK_POLL_MIN_SEC, 8)
        self._consecutive_errors = 0

    async def _broadcast_otp(self, row, otp_code, full_sms, reward_milli):
        user_name = f"User {row['user_id']}"
        u = await get_user(row["user_id"])
        if u and u["first_name"]: user_name = u["first_name"]
            
        group_text = (
            f"🔔 <b>OTP MỚI</b>\n\n"
            f"👤 User: {user_link(row['user_id'], user_name)}\n"
            f"📱 Số: <code>{mask_phone(row['phone'])}</code>\n"
            f"🔑 OTP: <code>{safe(otp_code)}</code>\n"
        )
        if full_sms: group_text += f"\n💬 {safe(full_sms, 300)}"

        user_text = (
            f"🔔 <b>OTP MỚI</b>\n\n"
            f"📦 Đơn: <code>#{row['id']}</code>\n"
            f"📱 Số: <code>{row['phone']}</code>\n"
            f"🔑 OTP: <code>{safe(otp_code)}</code>\n"
            f"💵 Thưởng: <b>{usd(reward_milli)}</b>"
        )
        if full_sms: user_text += f"\n\n💬 {safe(full_sms, 300)}"

        if OTP_GROUP_ID:
            try: await bot.send_message(OTP_GROUP_ID, group_text)
            except Exception: pass
        if ADMIN_ID and ADMIN_ID != OTP_GROUP_ID:
            try: await bot.send_message(ADMIN_ID, group_text)
            except Exception: pass
        try:
            if row["user_id"] not in (ADMIN_ID, OTP_GROUP_ID):
                await bot.send_message(row["user_id"], user_text)
        except Exception: pass

        if row["msg_id"]:
            asyncio.create_task(safe_delete_msg(row["user_id"], row["msg_id"], delay=300))

    async def _update_completed(self, oid, otp, sms, reward):
        db = get_db()
        try:
            db.execute("""
                UPDATE orders SET status='COMPLETED', otp_code=?, full_sms=?,
                    reward_milli=?, updated_at=? WHERE id=? AND status='PENDING'
            """, (otp, sms, reward, now_text(), oid))
            db.commit()
        finally: db.close()

    async def _update_failed(self, oid):
        db = get_db()
        try:
            db.execute("UPDATE orders SET status='FAILED', updated_at=? WHERE id=? AND status='PENDING'",
                             (now_text(), oid))
            db.commit()
        finally: db.close()

    async def _poll_once(self):
        rows = await get_pending_requests(limit=MK_POLL_BATCH)
        if not rows: return 0, 0, False

        ids = []
        for r in rows:
            try: ids.append(int(r["request_id"]))
            except (ValueError, TypeError): await self._update_failed(r["id"])
        if not ids: return 0, 0, False

        data, err = await api_request("POST", "check/status", {"request_ids": ids})
        if err: return 0, 0, True

        inner   = data.get("data") if isinstance(data, dict) else None
        results = inner.get("results") if isinstance(inner, dict) else None
        if not isinstance(results, list): return 0, 0, True

        by_req = {}
        for r in rows:
            try: by_req[int(r["request_id"])] = r
            except (ValueError, TypeError): pass

        checked = new_otp = 0
        for item in results:
            try: rid = int(item.get("request_id"))
            except (ValueError, TypeError): continue
            
            row = by_req.get(rid)
            if not row: continue

            checked += 1
            status = (item.get("status") or "").lower()

            if status == "success":
                otp  = str(item.get("otp_code") or "").strip()
                sms  = str(item.get("full_sms") or "").strip()
                if not otp:
                    await self._update_failed(row["id"])
                    continue

                reward = REWARD_MILLI_PER_OTP
                ok, _ = await change_usd(row["user_id"], reward, "OTP_REWARD", f"Thưởng OTP #{row['id']}")
                if not ok: reward = 0

                await self._update_completed(row["id"], otp, sms, reward)
                await self._broadcast_otp(row, otp, sms, reward)
                new_otp += 1

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
                self.interval = min(MK_POLL_MAX_SEC, max(self.interval * 2, 30))
            await asyncio.sleep(self.interval)

# =====================================================
# WEB SERVER (Render 24/7)
# =====================================================
async def web_server():
    async def handle(request):
        return web.Response(text="Bot is running!")
    
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Web server started on port {port}")

# =====================================================
# MAIN
# =====================================================
@dp.message(F.text)
async def unknown(message: Message):
    try: await message.delete()
    except: pass
    await message.answer("Gõ /start để mở menu FAST IVAS.")

async def main():
    global _mk_poller
    await init_db()
    await expire_old_orders()
    
    asyncio.create_task(web_server())

    if MK_POLL_ENABLED:
        _mk_poller = MkOtpPoller()
        asyncio.create_task(_mk_poller.run_forever())
        logger.info("Poller task created.")

    logger.info("FAST IVAS starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())