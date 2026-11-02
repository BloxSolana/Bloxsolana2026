import os
import re
import json
import html
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from aiohttp import web

import aiohttp
import aiosqlite

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest

# =====================================================
# CONFIG (ĐÃ ĐIỀN SẴN THÔNG TIN CỦA BẠN)
# =====================================================

BOT_TOKEN      = "8622066775:AAG1_WA634q5SEctcbq-xdqlWJ3an-M1Lpw"
ADMIN_ID       = 6726769296
OTP_GROUP_ID   = -1004341368656
OTP_GROUP_URL  = "https://t.me/LIVEOTPIVAS"
MK_API_KEY     = "badacaa33d287233567a49db"
MK_API_BASE    = "https://mknetworkbd.com/api/v3/public"
DB_PATH        = "fast_ivas.db"

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
    """Che số khi gửi vào Group OTP"""
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


# =====================================================
# KEYBOARDS
# =====================================================

def main_kb():
    rows = [
        [InlineKeyboardButton(text="👤 Tài khoản", callback_data="profile"),
         InlineKeyboardButton(text="💵 Ví USD",   callback_data="wallet")],
        [InlineKeyboardButton(text="📱 Nhận số",  callback_data="order_help"),
         InlineKeyboardButton(text="📦 Đơn hàng", callback_data="my_orders")],
        [InlineKeyboardButton(text="🌍 Danh sách số", callback_data="list_countries")],
        [InlineKeyboardButton(text="📜 Lịch sử",  callback_data="history"),
         InlineKeyboardButton(text="💸 Rút USD",  callback_data="withdraw_help")],
        [InlineKeyboardButton(text="👥 Giới thiệu", callback_data="referral")],
    ]
    if OTP_GROUP_URL:
        rows.append([InlineKeyboardButton(text="📢 Nhóm OTP", url=OTP_GROUP_URL)])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def fv_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Tài khoản",   callback_data="fv_whoami")],
        [InlineKeyboardButton(text="🗺 Tuyến",       callback_data="fv_routes")],
        [InlineKeyboardButton(text="📡 Radar",       callback_data="fv_radar")],
        [InlineKeyboardButton(text="⬅️ Trang chủ",   callback_data="home")],
    ])

def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Thống kê",       callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 Danh sách User", callback_data="admin_users")],
        [InlineKeyboardButton(text="📦 Đơn hàng",       callback_data="admin_orders")],
        [InlineKeyboardButton(text="💸 Rút chờ",         callback_data="admin_withdraws")],
        [InlineKeyboardButton(text="🌐 FAST IVAS",      callback_data="fv_whoami")],
    ])

def expired_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Nhận số khác", callback_data="order_help")],
        [InlineKeyboardButton(text="🌍 Đổi quốc gia khác", callback_data="list_countries")],
        [InlineKeyboardButton(text="🏠 Trang chủ", callback_data="home")]
    ])


# =====================================================
# DATABASE
# =====================================================

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT, first_name TEXT,
                usd_milli INTEGER NOT NULL DEFAULT 0,
                referrer INTEGER, joined_at TEXT
            )""")
        
        await db.execute("""
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
        
        try:
            await db.execute("ALTER TABLE orders ADD COLUMN msg_id INTEGER")
        except aiosqlite.OperationalError:
            pass

        await db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL, amount INTEGER NOT NULL,
                tx_type TEXT, note TEXT, created_at TEXT
            )""")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount_milli INTEGER NOT NULL, info TEXT,
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TEXT, processed_at TEXT
            )""")
        await db.commit()


async def register_user(tg_user, referrer=None):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE user_id=?", (tg_user.id,))
        if await cur.fetchone():
            await db.execute("UPDATE users SET username=?, first_name=? WHERE user_id=?",
                             (tg_user.username, tg_user.first_name, tg_user.id))
            await db.commit()
            return False
        if referrer == tg_user.id: referrer = None
        await db.execute("""
            INSERT INTO users (user_id, username, first_name, usd_milli, referrer, joined_at)
            VALUES (?, ?, ?, 0, ?, ?)
        """, (tg_user.id, tg_user.username, tg_user.first_name, referrer, now_text()))
        await db.commit()
        return True


async def get_user(uid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE user_id=?", (uid,))
        return await cur.fetchone()


async def change_usd(uid, amount_milli, tx_type, note):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("BEGIN IMMEDIATE")
        cur = await db.execute("SELECT usd_milli FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
        if not row:
            await db.rollback(); return False, "Không tìm thấy user."
        new = int(row[0]) + int(amount_milli)
        if new < 0:
            await db.rollback(); return False, "Số dư USD không đủ."
        await db.execute("UPDATE users SET usd_milli=? WHERE user_id=?", (new, uid))
        await db.execute("""
            INSERT INTO transactions (user_id, amount, tx_type, note, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (uid, amount_milli, tx_type, note, now_text()))
        await db.commit()
        return True, new


async def get_transactions(uid, limit=15):
    async with aiosqlite.connect(DB_PATH) as db:
        return await (await db.execute("""
            SELECT amount, tx_type, note, created_at
            FROM transactions WHERE user_id=? ORDER BY id DESC LIMIT ?
        """, (uid, limit))).fetchall()


async def create_withdrawal(uid, amount_milli, info):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            INSERT INTO withdrawals (user_id, amount_milli, info, status, created_at)
            VALUES (?, ?, ?, 'PENDING', ?)
        """, (uid, amount_milli, info, now_text()))
        await db.commit()
        return cur.lastrowid


async def expire_old_orders():
    t = now_text()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute("""
            SELECT id, user_id, msg_id, phone, country FROM orders 
            WHERE status='PENDING' AND expires_at IS NOT NULL AND expires_at<=?
        """, (t,))).fetchall()
        
        for r in rows:
            await db.execute("UPDATE orders SET status='EXPIRED', updated_at=? WHERE id=?", (t, r["id"]))
            if r["msg_id"]:
                try:
                    text = (
                        f"⌛ <b>ĐƠN HÀNG HẾT HẠN</b>\n\n"
                        f"Số: <code>{safe(r['phone'])}</code> ({safe(r['country'])})\n"
                        f"Trạng thái: Đã hết hạn sử dụng.\n\n"
                        f"Vui lòng chọn thao tác bên dưới:"
                    )
                    await bot.edit_message_text(
                        chat_id=r["user_id"],
                        message_id=r["msg_id"],
                        text=text,
                        reply_markup=expired_kb()
                    )
                except TelegramBadRequest: pass 
                except Exception as e: logger.error(f"Lỗi sửa tin nhắn hết hạn: {e}")
        await db.commit()


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
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO orders (user_id, request_id, phone, country, operator,
                    range_code, status, created_at, expires_at, updated_at, msg_id)
                VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?, ?, ?, ?)
            """, (uid, str(rid), str(phone or "N/A"), str(country or "?"),
                  str(operator or "?"), range_code, now_text(), exp, now_text(), msg_id))
            await db.commit()
    except aiosqlite.IntegrityError:
        return False, "request_id trùng."

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
    async with aiosqlite.connect(DB_PATH) as db:
        return await (await db.execute("""
            SELECT id, request_id, phone, country, operator,
                   status, created_at, expires_at
            FROM orders WHERE user_id=? ORDER BY id DESC LIMIT ?
        """, (uid, limit))).fetchall()

async def get_order(oid, uid=None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if uid is None:
            cur = await db.execute("SELECT * FROM orders WHERE id=?", (oid,))
        else:
            cur = await db.execute("SELECT * FROM orders WHERE id=? AND user_id=?", (oid, uid))
        return await cur.fetchone()

async def get_all_orders(limit=15):
    await expire_old_orders()
    async with aiosqlite.connect(DB_PATH) as db:
        return await (await db.execute("""
            SELECT id, user_id, request_id, phone, status
            FROM orders ORDER BY id DESC LIMIT ?
        """, (limit,))).fetchall()

async def get_pending_requests(limit=100):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        return await (await db.execute("""
            SELECT id, user_id, request_id, phone, msg_id
            FROM orders WHERE status='PENDING' ORDER BY id ASC LIMIT ?
        """, (limit,))).fetchall()

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
# START / HELP / PROFILE / WALLET
# =====================================================

@dp.message(CommandStart())
async def cmd_start(message: Message):
    args = message.text.split(maxsplit=1)
    ref = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    is_new = await register_user(message.from_user, ref)
    if is_new and ref:
        try: await bot.send_message(ref, "👥 Có người mới tham gia FAST IVAS qua link của bạn.")
        except Exception: pass
    await message.answer(
        "🚀 <b>FAST IVAS</b>\n\nChào mừng bạn!\nChọn chức năng:",
        reply_markup=main_kb()
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "<b>FAST IVAS — Hướng dẫn</b>\n\n"
        "/start — Menu\n/profile — Hồ sơ\n/wallet — Ví USD\n"
        "/nhanso RANGE — Nhận số OTP\n/donhang [ID] — Xem đơn\n"
        "/rut SOTIEN — Rút USD (min $3)\n"
        "/history — Lịch sử\n/id — Telegram ID\n\n"
        f"💵 <b>{usd(REWARD_MILLI_PER_OTP)}</b>/OTP · "
        f"💸 Rút min <b>{usd(MIN_WITHDRAW_MILLI)}</b>"
    )

@dp.message(Command("id"))
async def cmd_id(message: Message):
    await message.answer(f"Telegram ID: <code>{message.from_user.id}</code>")

@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    await register_user(message.from_user)
    u = await get_user(message.from_user.id)
    await message.answer(
        "👤 <b>HỒ SƠ</b>\n\n"
        f"ID: <code>{u['user_id']}</code>\n"
        f"Tên: {safe(u['first_name'])}\n"
        f"Username: @{safe(u['username'] or '—')}\n\n"
        f"💵 Số dư USD: <b>{usd(u['usd_milli'])}</b>"
    )

@dp.message(Command("wallet"))
async def cmd_wallet(message: Message):
    await register_user(message.from_user)
    u = await get_user(message.from_user.id)
    await message.answer(
        "💵 <b>VÍ USD (từ OTP)</b>\n\n"
        f"Số dư: <b>{usd(u['usd_milli'])}</b>\n"
        f"Thưởng/OTP: <b>{usd(REWARD_MILLI_PER_OTP)}</b>\n"
        f"Rút min: <b>{usd(MIN_WITHDRAW_MILLI)}</b>\n\n"
        "Rút: <code>/rut 3.5</code>"
    )


# =====================================================
# CALLBACKS
# =====================================================

@dp.callback_query(F.data == "home")
async def cb_home(call: CallbackQuery):
    await call.message.edit_text("🚀 <b>FAST IVAS</b>\n\nChọn chức năng:", reply_markup=main_kb())
    await call.answer()

@dp.callback_query(F.data == "profile")
async def cb_profile(call: CallbackQuery):
    await register_user(call.from_user)
    u = await get_user(call.from_user.id)
    await call.message.edit_text(
        "👤 <b>HỒ SƠ</b>\n\n"
        f"ID: <code>{u['user_id']}</code>\n"
        f"Tên: {safe(u['first_name'])}\n\n"
        f"💵 Số dư USD: <b>{usd(u['usd_milli'])}</b>",
        reply_markup=main_kb()
    )
    await call.answer()

@dp.callback_query(F.data == "wallet")
async def cb_wallet(call: CallbackQuery):
    await register_user(call.from_user)
    u = await get_user(call.from_user.id)
    await call.message.edit_text(
        "💵 <b>VÍ USD</b>\n\n"
        f"Số dư: <b>{usd(u['usd_milli'])}</b>\n"
        f"Thưởng/OTP: <b>{usd(REWARD_MILLI_PER_OTP)}</b>\n"
        f"Rút min: <b>{usd(MIN_WITHDRAW_MILLI)}</b>\n\n"
        "Rút: <code>/rut 3.5</code>",
        reply_markup=main_kb()
    )
    await call.answer()

@dp.callback_query(F.data == "order_help")
async def cb_order_help(call: CallbackQuery):
    await call.message.edit_text(
        "📱 <b>NHẬN SỐ</b>\n\n"
        "Gửi: <code>/nhanso MA_TUYEN</code>\n"
        "VD: <code>/nhanso 23276345XXX</code>\n\n"
        f"Thời hạn: {ORDER_LIFETIME_MINUTES} phút\n"
        f"Thưởng/OTP: <b>{usd(REWARD_MILLI_PER_OTP)}</b>",
        reply_markup=main_kb()
    )
    await call.answer()

@dp.message(Command("nhanso"))
async def cmd_nhanso(message: Message):
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
        f"Nhà mạng: {safe(res['operator'])}\n"
        f"Hết hạn: {safe(res['expires_at'])}\n\n"
        "⏳ Đang chờ OTP — bot sẽ gửi khi có.\n"
        f"💵 Bạn sẽ nhận <b>{usd(REWARD_MILLI_PER_OTP)}</b>/OTP.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌍 Đổi quốc gia", callback_data="list_countries")]
        ])
    )

@dp.message(Command("donhang"))
async def cmd_donhang(message: Message):
    await register_user(message.from_user)
    parts = message.text.split(maxsplit=1)
    if len(parts) == 2 and parts[1].isdigit():
        row = await get_order(int(parts[1]), message.from_user.id)
        if not row:
            await message.answer("Không tìm thấy đơn.")
            return
        await message.answer(fmt_order(row))
        return

    rows = await get_user_orders(message.from_user.id)
    if not rows:
        await message.answer("Bạn chưa có đơn hàng.")
        return
    lines = ["📦 <b>ĐƠN HÀNG</b>\n"]
    for r in rows:
        lines.append(
            f"#{r[0]} | {status_text(r[5])}\n"
            f"Số: <code>{safe(r[2])}</code>\n"
            f"Request ID: <code>{safe(r[1])}</code>\n"
            f"Chi tiết: <code>/donhang {r[0]}</code>"
        )
    await message.answer("\n\n".join(lines))

@dp.callback_query(F.data == "my_orders")
async def cb_my_orders(call: CallbackQuery):
    rows = await get_user_orders(call.from_user.id)
    if not rows:
        await call.message.edit_text("Bạn chưa có đơn hàng.", reply_markup=main_kb())
        await call.answer(); return
    lines = ["📦 <b>ĐƠN HÀNG</b>\n"]
    for r in rows:
        lines.append(
            f"#{r[0]} | {status_text(r[5])}\n"
            f"Số: <code>{safe(r[2])}</code>\n"
            f"Request ID: <code>{safe(r[1])}</code>"
        )
    await call.message.edit_text("\n\n".join(lines), reply_markup=main_kb())
    await call.answer()


# =====================================================
# DANH SÁCH SỐ
# =====================================================

@dp.callback_query(F.data == "list_countries")
async def cb_list_countries(call: CallbackQuery):
    await call.answer("Đang tải danh sách quốc gia...")
    
    data, err = await api_get("access_list", params={"limit": 150})
    if err:
        await call.message.edit_text(f"❌ Lỗi: {safe(err)}", reply_markup=main_kb())
        return

    items = data.get("data", {}).get("items", [])
    if not items:
        await call.message.edit_text("Tài khoản của bạn chưa có quốc gia nào khả dụng.", reply_markup=main_kb())
        return

    countries = {}
    for item in items:
        c_name = item.get("country")
        if c_name and c_name not in countries:
            countries[c_name] = True

    buttons = []
    c_list = list(countries.keys())
    for i in range(0, len(c_list), 2):
        row = [InlineKeyboardButton(text=f"🌍 {c_list[i]}", callback_data=f"c_{i}")]
        if i + 1 < len(c_list):
            row.append(InlineKeyboardButton(text=f"🌍 {c_list[i+1]}", callback_data=f"c_{i+1}"))
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton(text="⬅️ Quay lại", callback_data="home")])

    await call.message.edit_text(
        "🌍 <b>DANH SÁCH QUỐC GIA</b>\n\n"
        "Chọn quốc gia để xem các đầu số (Range) hiện có:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@dp.callback_query(F.data.startswith("c_"))
async def cb_view_ranges(call: CallbackQuery):
    await call.answer("Đang lấy đầu số...")
    
    data, err = await api_get("access_list", params={"limit": 150})
    if err:
        await call.message.edit_text(f"❌ Lỗi: {safe(err)}", reply_markup=main_kb())
        return
        
    items = data.get("data", {}).get("items", [])
    countries = {}
    for item in items:
        c_name = item.get("country")
        if c_name and c_name not in countries:
            countries[c_name] = []
        if c_name:
            countries[c_name].append(item)

    c_list = list(countries.keys())
    idx = int(call.data.replace("c_", ""))
    if idx >= len(c_list): return

    selected_country = c_list[idx]
    ranges = countries[selected_country]

    buttons = []
    for r in ranges:
        r_code = r.get("range")
        r_health = r.get("health", "good")
        icon = "🟢" if r_health == "excellent" else "🟡" if r_health == "good" else "⚪"
        buttons.append([InlineKeyboardButton(text=f"{icon} {r_code}", callback_data=f"rng_{r_code}")])
    
    buttons.append([InlineKeyboardButton(text="⬅️ Quay lại", callback_data="list_countries")])

    await call.message.edit_text(
        f"🌍 <b>{selected_country}</b>\n\n"
        "Chọn đầu số (Range) để nhận số:\n"
        "🟢 Tốt | 🟡 Thường | ⚪ Ít dùng",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@dp.callback_query(F.data.startswith("rng_"))
async def cb_choose_range(call: CallbackQuery):
    range_code = call.data.replace("rng_", "")
    await call.answer("Đang lấy số...")
    
    ok, res = await create_number_order(call.from_user.id, range_code, msg_id=call.message.message_id)
    if not ok:
        await call.message.edit_text(f"❌ {safe(res)}", reply_markup=main_kb())
        return

    await call.message.edit_text(
        "✅ <b>ĐÃ NHẬN SỐ</b>\n\n"
        f"Số: <code>{res['phone']}</code>\n"
        f"Quốc gia: {safe(res['country'])}\n"
        f"Nhà mạng: {safe(res['operator'])}\n"
        f"Hết hạn: {safe(res['expires_at'])}\n\n"
        "⏳ Đang chờ OTP...",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌍 Đổi quốc gia", callback_data="list_countries")]
        ])
    )


# =====================================================
# WITHDRAW (USD)
# =====================================================

@dp.callback_query(F.data == "withdraw_help")
async def cb_withdraw_help(call: CallbackQuery):
    await call.message.edit_text(
        "💸 <b>RÚT USD</b>\n\n"
        "Gửi: <code>/rut SOTIEN</code>\n"
        f"Min rút: <b>{usd(MIN_WITHDRAW_MILLI)}</b>\n\n"
        "VD: <code>/rut 3.5</code>",
        reply_markup=main_kb()
    )
    await call.answer()

def parse_usd(text):
    m = re.fullmatch(r"(\d+)(?:\.(\d{1,3}))?", str(text).strip().replace(",", "."))
    if not m: return None
    frac = ((m.group(2) or "") + "000")[:3]
    return int(m.group(1)) * 1000 + int(frac)

@dp.message(Command("rut"))
async def cmd_rut(message: Message):
    await register_user(message.from_user)
    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        await message.answer(f"Dùng: <code>/rut 3.5</code>\nMin: {usd(MIN_WITHDRAW_MILLI)}")
        return

    amt = parse_usd(parts[1])
    if amt is None or amt <= 0:
        await message.answer("Số tiền không hợp lệ."); return
    if amt < MIN_WITHDRAW_MILLI:
        await message.answer(f"❌ Min rút là {usd(MIN_WITHDRAW_MILLI)}."); return

    u = await get_user(message.from_user.id)
    if int(u["usd_milli"]) < amt:
        await message.answer(f"❌ Số dư không đủ. Hiện có: <b>{usd(u['usd_milli'])}</b>")
        return

    ok, new_usd = await change_usd(message.from_user.id, -amt, "WITHDRAW_HOLD", "Yêu cầu rút")
    if not ok:
        await message.answer(safe(new_usd)); return

    wid = await create_withdrawal(message.from_user.id, amt, "Chờ admin duyệt")
    await message.answer(
        "✅ <b>YÊU CẦU RÚT ĐÃ TẠO</b>\n\n"
        f"Mã: <code>#{wid}</code>\n"
        f"Số tiền: <b>{usd(amt)}</b>\n"
        f"Còn lại: <b>{usd(new_usd)}</b>\n"
        "Chờ admin duyệt."
    )
    try:
        await bot.send_message(
            ADMIN_ID,
            "💸 <b>YÊU CẦU RÚT</b>\n\n"
            f"Mã: #{wid}\nUser: <code>{message.from_user.id}</code>\n"
            f"Số tiền: <b>{usd(amt)}</b>\n"
            f"Duyệt: <code>/rutduyet {wid}</code>\n"
            f"Từ chối: <code>/ruttuchoi {wid}</code>"
        )
    except Exception: pass


# =====================================================
# HISTORY / REFERRAL
# =====================================================

def tx_line(amount, tx_type, note):
    sign = "+" if amount >= 0 else ""
    return f"• {sign}{usd(amount)} | {safe(tx_type)}\n  {safe(note)}"

@dp.callback_query(F.data == "history")
async def cb_history(call: CallbackQuery):
    rows = await get_transactions(call.from_user.id)
    text = "📜 <b>LỊCH SỬ</b>\n\nChưa có giao dịch." if not rows else \
        "\n".join(["📜 <b>LỊCH SỬ</b>\n"] + [tx_line(*r[:3]) for r in rows])
    await call.message.edit_text(text, reply_markup=main_kb())
    await call.answer()

@dp.message(Command("history"))
async def cmd_history(message: Message):
    rows = await get_transactions(message.from_user.id)
    if not rows:
        await message.answer("Chưa có giao dịch."); return
    await message.answer("\n".join(["📜 <b>LỊCH SỬ</b>\n"] + [tx_line(*r[:3]) for r in rows]))

@dp.callback_query(F.data == "referral")
async def cb_referral(call: CallbackQuery):
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={call.from_user.id}"
    await call.message.edit_text(
        "👥 <b>GIỚI THIỆU</b>\n\n"
        f"<code>{link}</code>",
        reply_markup=main_kb()
    )
    await call.answer()


# =====================================================
# FAST IVAS MENU
# =====================================================

@dp.callback_query(F.data == "fv_menu")
async def cb_fv_menu(call: CallbackQuery):
    await call.message.edit_text(
        "🌐 <b>FAST IVAS</b>\n\nChọn dữ liệu:",
        reply_markup=fv_kb()
    )
    await call.answer()

@dp.callback_query(F.data.in_({"fv_whoami", "fv_routes", "fv_radar"}))
async def cb_fv(call: CallbackQuery):
    await call.answer("Đang tải…")
    if call.data == "fv_whoami":
        data, err = await api_get("whoami"); title = "📊 TÀI KHOẢN"
    elif call.data == "fv_routes":
        data, err = await api_get("access_list", params={"limit": 20, "offset": 0, "health": "excellent"})
        title = "🗺 TUYẾN"
    else:
        data, err = await api_get("radar", params={"limit": 25, "charts": "true"})
        title = "📡 RADAR"

    if err:
        await call.message.answer(f"❌ {safe(err)}"); return
    await call.message.answer(
        f"<b>{title}</b>\n\n<pre>{fmt_api(data)}</pre>",
        reply_markup=fv_kb()
    )


# =====================================================
# ADMIN PANEL
# =====================================================

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id): return
    await message.answer("🛡 <b>FAST IVAS ADMIN</b>", reply_markup=admin_kb())

@dp.callback_query(F.data.startswith("admin_"))
async def cb_admin(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Không có quyền.", show_alert=True); return

    if call.data == "admin_stats":
        await expire_old_orders()
        async with aiosqlite.connect(DB_PATH) as db:
            users    = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
            tot_usd  = (await (await db.execute("SELECT COALESCE(SUM(usd_milli),0) FROM users")).fetchone())[0]
            orders   = (await (await db.execute("SELECT COUNT(*) FROM orders")).fetchone())[0]
            pending  = (await (await db.execute("SELECT COUNT(*) FROM orders WHERE status='PENDING'")).fetchone())[0]
            completed= (await (await db.execute("SELECT COUNT(*) FROM orders WHERE status='COMPLETED'")).fetchone())[0]
            wd       = (await (await db.execute("SELECT COUNT(*) FROM withdrawals WHERE status='PENDING'")).fetchone())[0]
        await call.message.answer(
            "📊 <b>THỐNG KÊ</b>\n\n"
            f"👥 Users: <b>{users}</b>\n"
            f"📦 Đơn: <b>{orders}</b> (chờ <b>{pending}</b>, xong <b>{completed}</b>)\n"
            f"💵 USD tổng: <b>{usd(tot_usd)}</b>\n"
            f"💸 Rút chờ: <b>{wd}</b>"
        )

    elif call.data == "admin_users":
        async with aiosqlite.connect(DB_PATH) as db:
            users = await (await db.execute("""
                SELECT joined_at, user_id, first_name FROM users ORDER BY joined_at DESC LIMIT 50
            """)).fetchall()
        if not users:
            await call.message.answer("Chưa có user nào.")
        else:
            lines = ["👥 <b>DANH SÁCH USER MỚI NHẤT</b>\n"]
            for joined, uid, name in users:
                time_str = joined[:10] if joined else "N/A"
                lines.append(
                    f"📅 {time_str} | <code>{uid}</code>\n"
                    f"👤 Tên: {safe(name)}\n"
                )
            await call.message.answer("\n".join(lines))

    elif call.data == "admin_orders":
        rows = await get_all_orders()
        if not rows:
            await call.message.answer("Chưa có đơn.")
        else:
            lines = ["📦 <b>ĐƠN GẦN ĐÂY</b>\n"]
            for r in rows:
                lines.append(
                    f"#{r[0]} | User <code>{r[1]}</code>\n"
                    f"Request: <code>{safe(r[2])}</code>\n"
                    f"Số: <code>{safe(r[3])}</code>\n"
                    f"Status: {safe(r[4])}"
                )
            await call.message.answer("\n\n".join(lines))

    elif call.data == "admin_withdraws":
        async with aiosqlite.connect(DB_PATH) as db:
            rows = await (await db.execute("""
                SELECT id, user_id, amount_milli FROM withdrawals
                WHERE status='PENDING' ORDER BY id DESC LIMIT 15
            """)).fetchall()
        if not rows:
            await call.message.answer("Không có rút chờ.")
        else:
            lines = ["💸 <b>RÚT CHỜ</b>\n"]
            for rid, uid, amt in rows:
                lines.append(
                    f"#{rid} | User <code>{uid}</code>\n"
                    f"Số tiền: <b>{usd(amt)}</b>\n"
                    f"Duyệt: <code>/rutduyet {rid}</code>\n"
                    f"Từ chối: <code>/ruttuchoi {rid}</code>"
                )
            await call.message.answer("\n\n".join(lines))

    await call.answer()


# =====================================================
# ADMIN ORDER / WITHDRAW
# =====================================================

@dp.message(Command("adminorder"))
async def cmd_adminorder(message: Message):
    if not is_admin(message.from_user.id): return
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Dùng: <code>/adminorder ID</code>"); return
    row = await get_order(int(parts[1]))
    if not row:
        await message.answer("Không tìm thấy đơn."); return
    await message.answer(fmt_order(row))

async def _set_order_status(oid, new):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("BEGIN IMMEDIATE")
        cur = await db.execute("SELECT user_id, status FROM orders WHERE id=?", (oid,))
        row = await cur.fetchone()
        if not row: await db.rollback(); return None
        uid, old = row
        if old != "PENDING":
            await db.rollback(); return False
        await db.execute("UPDATE orders SET status=?, updated_at=? WHERE id=? AND status='PENDING'",
                         (new, now_text(), oid))
        await db.commit()
        return uid

@dp.message(Command("hoanthanh"))
async def cmd_hoanthanh(message: Message):
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
    if not is_admin(message.from_user.id): return
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Dùng: <code>/thatbai ID</code>"); return
    uid = await _set_order_status(int(parts[1]), "FAILED")
    if uid is None: await message.answer("Không tìm thấy đơn."); return
    if uid is False: await message.answer("Đơn không PENDING."); return
    await message.answer(f"❌ Đã set đơn #{parts[1]} = FAILED.")

@dp.message(Command("rutduyet"))
async def cmd_rutduyet(message: Message):
    if not is_admin(message.from_user.id): return
    p = message.text.split()
    if len(p) != 2 or not p[1].isdigit():
        await message.answer("Dùng: <code>/rutduyet ID</code>"); return
    wid = int(p[1])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("BEGIN IMMEDIATE")
        cur = await db.execute("SELECT user_id, amount_milli, status FROM withdrawals WHERE id=?", (wid,))
        row = await cur.fetchone()
        if not row:
            await db.rollback(); await message.answer("Không tìm thấy."); return
        uid, amt, status = row
        if status != "PENDING":
            await db.rollback(); await message.answer("Đã xử lý."); return
        await db.execute("UPDATE withdrawals SET status='APPROVED', processed_at=? WHERE id=?",
                         (now_text(), wid))
        await db.commit()
    await message.answer(f"✅ Đã duyệt rút #{wid}: {usd(amt)} cho user {uid}")
    try: await bot.send_message(uid, f"✅ Rút #{wid} được duyệt: {usd(amt)}")
    except Exception: pass

@dp.message(Command("ruttuchoi"))
async def cmd_ruttuchoi(message: Message):
    if not is_admin(message.from_user.id): return
    p = message.text.split()
    if len(p) != 2 or not p[1].isdigit():
        await message.answer("Dùng: <code>/ruttuchoi ID</code>"); return
    wid = int(p[1])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("BEGIN IMMEDIATE")
        cur = await db.execute("SELECT user_id, amount_milli, status FROM withdrawals WHERE id=?", (wid,))
        row = await cur.fetchone()
        if not row:
            await db.rollback(); await message.answer("Không tìm thấy."); return
        uid, amt, status = row
        if status != "PENDING":
            await db.rollback(); await message.answer("Đã xử lý."); return
        await db.execute("UPDATE withdrawals SET status='REJECTED', processed_at=? WHERE id=?",
                         (now_text(), wid))
        await db.execute("UPDATE users SET usd_milli=usd_milli+? WHERE user_id=?", (amt, uid))
        await db.execute("""
            INSERT INTO transactions (user_id, amount, tx_type, note, created_at)
            VALUES (?, ?, 'WITHDRAW_REFUND', ?, ?)
        """, (uid, amt, f"Hoàn tiền rút #{wid}", now_text()))
        await db.commit()
    await message.answer(f"❌ Đã từ chối rút #{wid}. Hoàn {usd(amt)} cho user {uid}")
    try: await bot.send_message(uid, f"❌ Rút #{wid} bị từ chối. Đã hoàn {usd(amt)}.")
    except Exception: pass

@dp.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    if not is_admin(message.from_user.id): return
    content = message.text.partition(" ")[2].strip()
    if not content:
        await message.answer("Dùng: <code>/broadcast Nội dung</code>"); return
    async with aiosqlite.connect(DB_PATH) as db:
        users = await (await db.execute("SELECT user_id FROM users")).fetchall()
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
    if not is_admin(message.from_user.id): return
    async with aiosqlite.connect(DB_PATH) as db:
        pending = (await (await db.execute("SELECT COUNT(*) FROM orders WHERE status='PENDING'")).fetchone())[0]
    poller = "OFF" if not _mk_poller else f"ON ({_mk_poller.interval}s, err={_mk_poller._consecutive_errors})"
    await message.answer(
        "🟢 <b>FAST IVAS ONLINE</b>\n\n"
        f"DB: <code>{safe(DB_PATH)}</code>\n"
        f"API key: {'✓' if MK_API_KEY else '✗'}\n"
        f"OTP group ID: <code>{OTP_GROUP_ID}</code>\n"
        f"Đơn chờ: <b>{pending}</b>\n"
        f"Poller: {safe(poller)}\n"
        f"Thưởng/OTP: <b>{usd(REWARD_MILLI_PER_OTP)}</b>\n"
        f"Min rút: <b>{usd(MIN_WITHDRAW_MILLI)}</b>"
    )


# =====================================================
# MK OTP POLLER
# =====================================================

class MkOtpPoller:
    MAX_CONSECUTIVE_ERRORS = 5

    def __init__(self):
        self.interval = max(MK_POLL_MIN_SEC, 8)
        self._consecutive_errors = 0

    async def _broadcast_otp(self, row, otp_code, full_sms, reward_milli):
        user_name = f"User {row['user_id']}"
        u = await get_user(row["user_id"])
        if u and u["first_name"]:
            user_name = u["first_name"]
            if u["username"]: user_name += f" (@{u['username']})"

        # 1. Tạo tin nhắn cho Group (Che số)
        group_text = (
            f"🔔 <b>OTP MỚI</b>\n\n"
            f"👤 User: {user_link(row['user_id'], user_name)}\n"
            f"🆔 ID: <code>{row['user_id']}</code>\n"
            f"📦 Đơn: <code>#{row['id']}</code>\n"
            f"📱 Số: <code>{mask_phone(row['phone'])}</code>\n" 
            f"🔑 OTP: <code>{safe(otp_code)}</code>\n"
            f"💵 Thưởng: <b>{usd(reward_milli)}</b>"
        )
        if full_sms: group_text += f"\n\n💬 {safe(full_sms, 300)}"

        # 2. Tạo tin nhắn cho User (Hiện full số)
        user_text = (
            f"🔔 <b>OTP MỚI</b>\n\n"
            f"📦 Đơn: <code>#{row['id']}</code>\n"
            f"📱 Số: <code>{row['phone']}</code>\n" 
            f"🔑 OTP: <code>{safe(otp_code)}</code>\n"
            f"💵 Thưởng: <b>{usd(reward_milli)}</b>"
        )
        if full_sms: user_text += f"\n\n💬 {safe(full_sms, 300)}"

        # Gửi vào Group OTP
        if OTP_GROUP_ID:
            try: await bot.send_message(OTP_GROUP_ID, group_text)
            except Exception: pass

        # Gửi cho Admin
        if ADMIN_ID and ADMIN_ID != OTP_GROUP_ID:
            try: await bot.send_message(ADMIN_ID, group_text)
            except Exception: pass

        # Gửi cho User
        try:
            user_id = row["user_id"]
            if user_id not in (ADMIN_ID, OTP_GROUP_ID):
                await bot.send_message(user_id, user_text)
        except Exception: pass

    async def _update_completed(self, oid, otp, sms, reward):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                UPDATE orders SET status='COMPLETED', otp_code=?, full_sms=?,
                    reward_milli=?, updated_at=? WHERE id=? AND status='PENDING'
            """, (otp, sms, reward, now_text(), oid))
            await db.commit()

    async def _update_failed(self, oid):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE orders SET status='FAILED', updated_at=? WHERE id=? AND status='PENDING'",
                             (now_text(), oid))
            await db.commit()

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
            # Ép kiểu int cho request_id để so sánh chính xác với API trả về
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
            elif status == "expired":
                pass

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
# DUMMY WEB SERVER (Để Render không tắt bot)
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