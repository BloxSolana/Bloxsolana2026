import os
import re
import json
import html
import asyncio
import logging
from datetime import datetime, timedelta, timezone

import aiohttp
import aiosqlite

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

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

PRICE_PER_ORDER        = 0
ORDER_LIFETIME_MINUTES = 15

REWARD_MILLI_PER_OTP   = 4    # $0.004
MIN_WITHDRAW_MILLI     = 3000 # $3.000

MK_POLL_ENABLED = True
MK_POLL_MIN_SEC = 8
MK_POLL_MAX_SEC = 60
MK_POLL_BATCH   = 100

if not BOT_TOKEN:
    raise RuntimeError("Thiếu BOT_TOKEN")
if not MK_API_KEY:
    raise RuntimeError("Thiếu MK_API_KEY")
if not ADMIN_ID:
    raise RuntimeError("Thiếu ADMIN_ID")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FAST_IVAS")

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp  = Dispatcher()


# =====================================================
# HELPERS
# =====================================================

def now():      return datetime.now(timezone.utc)
def now_text(): return now().isoformat(timespec="seconds")

def money(v):   return f"{int(v):,}".replace(",", ".")

def usd(milli):
    milli = int(milli); s = "-" if milli < 0 else ""; milli = abs(milli)
    return f"{s}${milli // 1000}.{milli % 1000:03d}"

def safe(v, limit=500): return html.escape(str(v or "")[:limit])
def is_admin(uid):      return int(uid) == ADMIN_ID

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
        [InlineKeyboardButton(text="📱 Đặt số",   callback_data="order_help"),
         InlineKeyboardButton(text="📦 Đơn hàng", callback_data="my_orders")],
        [InlineKeyboardButton(text="➕ Nạp VND",  callback_data="deposit_help"),
         InlineKeyboardButton(text="💸 Rút USD",  callback_data="withdraw_help")],
        [InlineKeyboardButton(text="📜 Lịch sử",  callback_data="history"),
         InlineKeyboardButton(text="👥 Giới thiệu", callback_data="referral")],
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
        [InlineKeyboardButton(text="📦 Đơn hàng",       callback_data="admin_orders")],
        [InlineKeyboardButton(text="💳 Nạp chờ",         callback_data="admin_deposits")],
        [InlineKeyboardButton(text="💸 Rút chờ",         callback_data="admin_withdraws")],
        [InlineKeyboardButton(text="🌐 FAST IVAS",      callback_data="fv_whoami")],
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
                balance INTEGER NOT NULL DEFAULT 0,
                usd_milli INTEGER NOT NULL DEFAULT 0,
                referrer INTEGER, joined_at TEXT
            )""")
        try:
            await db.execute("ALTER TABLE users ADD COLUMN usd_milli INTEGER NOT NULL DEFAULT 0")
        except aiosqlite.OperationalError:
            pass

        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                request_id TEXT UNIQUE,
                phone TEXT, country TEXT, operator TEXT, range_code TEXT,
                status TEXT NOT NULL DEFAULT 'PENDING',
                price INTEGER NOT NULL DEFAULT 0,
                otp_code TEXT, full_sms TEXT,
                reward_milli INTEGER NOT NULL DEFAULT 0,
                created_at TEXT, expires_at TEXT, updated_at TEXT
            )""")
        for col, typ in [
            ("otp_code", "TEXT"), ("full_sms", "TEXT"),
            ("reward_milli", "INTEGER NOT NULL DEFAULT 0"),
        ]:
            try:
                await db.execute(f"ALTER TABLE orders ADD COLUMN {col} {typ}")
            except aiosqlite.OperationalError:
                pass

        await db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL, amount INTEGER NOT NULL,
                unit TEXT NOT NULL DEFAULT 'VND',
                tx_type TEXT, note TEXT, created_at TEXT
            )""")
        try:
            await db.execute("ALTER TABLE transactions ADD COLUMN unit TEXT NOT NULL DEFAULT 'VND'")
        except aiosqlite.OperationalError:
            pass

        await db.execute("""
            CREATE TABLE IF NOT EXISTS deposits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL, amount INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TEXT, processed_at TEXT
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
        if referrer == tg_user.id:
            referrer = None
        await db.execute("""
            INSERT INTO users (user_id, username, first_name, balance, usd_milli, referrer, joined_at)
            VALUES (?, ?, ?, 0, 0, ?, ?)
        """, (tg_user.id, tg_user.username, tg_user.first_name, referrer, now_text()))
        await db.commit()
        return True


async def get_user(uid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE user_id=?", (uid,))
        return await cur.fetchone()


async def change_balance(uid, amount, tx_type, note):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("BEGIN IMMEDIATE")
        cur = await db.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
        if not row:
            await db.rollback(); return False, "Không tìm thấy user."
        new = int(row[0]) + int(amount)
        if new < 0:
            await db.rollback(); return False, "Số dư VND không đủ."
        await db.execute("UPDATE users SET balance=? WHERE user_id=?", (new, uid))
        await db.execute("""
            INSERT INTO transactions (user_id, amount, unit, tx_type, note, created_at)
            VALUES (?, ?, 'VND', ?, ?, ?)
        """, (uid, amount, tx_type, note, now_text()))
        await db.commit()
        return True, new


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
            INSERT INTO transactions (user_id, amount, unit, tx_type, note, created_at)
            VALUES (?, ?, 'USD_MILLI', ?, ?, ?)
        """, (uid, amount_milli, tx_type, note, now_text()))
        await db.commit()
        return True, new


async def get_transactions(uid, limit=15):
    async with aiosqlite.connect(DB_PATH) as db:
        return await (await db.execute("""
            SELECT amount, unit, tx_type, note, created_at
            FROM transactions WHERE user_id=? ORDER BY id DESC LIMIT ?
        """, (uid, limit))).fetchall()


async def create_deposit(uid, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            INSERT INTO deposits (user_id, amount, status, created_at)
            VALUES (?, ?, 'PENDING', ?)
        """, (uid, amount, now_text()))
        await db.commit()
        return cur.lastrowid


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
        await db.execute("""
            UPDATE orders SET status='EXPIRED', updated_at=?
            WHERE status='PENDING' AND expires_at IS NOT NULL AND expires_at<=?
        """, (t, t))
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

async def create_number_order(uid, range_code):
    if not range_code or len(range_code) > 80 or any(c.isspace() for c in range_code):
        return False, "Mã tuyến không hợp lệ."

    if PRICE_PER_ORDER > 0:
        ok, _ = await change_balance(uid, -PRICE_PER_ORDER, "ORDER_RESERVE", "Phí đặt số")
        if not ok: return False, f"Số dư VND không đủ (phí {money(PRICE_PER_ORDER)}đ)."

    data, err = await api_request("POST", "getnum/number", {"range": range_code})
    if err:
        if PRICE_PER_ORDER > 0:
            await change_balance(uid, PRICE_PER_ORDER, "ORDER_REFUND", "Hoàn phí")
        return False, err

    rid      = field(data, "request_id", "requestId", "id")
    phone    = field(data, "number", "phone", "phone_number")
    country  = field(data, "country", "country_name")
    operator = field(data, "operator", "network", "carrier")

    if not rid:
        if PRICE_PER_ORDER > 0:
            await change_balance(uid, PRICE_PER_ORDER, "ORDER_REFUND", "Hoàn phí")
        return False, "API thiếu request_id."

    exp = (now() + timedelta(minutes=ORDER_LIFETIME_MINUTES)).isoformat(timespec="seconds")
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO orders (user_id, request_id, phone, country, operator,
                    range_code, status, price, created_at, expires_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?, ?, ?, ?)
            """, (uid, str(rid), str(phone or "N/A"), str(country or "?"),
                  str(operator or "?"), range_code, PRICE_PER_ORDER,
                  now_text(), exp, now_text()))
            await db.commit()
    except aiosqlite.IntegrityError:
        if PRICE_PER_ORDER > 0:
            await change_balance(uid, PRICE_PER_ORDER, "ORDER_REFUND", "Hoàn phí")
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
                   status, created_at, expires_at, price
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
            SELECT id, user_id, request_id, phone
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
        f"Hết hạn: {safe(row['expires_at'])}\n"
        f"Phí VND: {money(row['price'])}đ"
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
        "/datso RANGE — Đặt số nhận OTP\n/donhang [ID] — Xem đơn\n"
        "/nap SOTIEN — Nạp VND\n/rut SOTIEN — Rút USD (min $3)\n"
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
        f"💰 VND: <b>{money(u['balance'])}đ</b>\n"
        f"💵 USD: <b>{usd(u['usd_milli'])}</b>"
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
        f"💰 VND: <b>{money(u['balance'])}đ</b>\n"
        f"💵 USD: <b>{usd(u['usd_milli'])}</b>",
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
        "📱 <b>ĐẶT SỐ</b>\n\n"
        "Gửi: <code>/datso MA_TUYEN</code>\n"
        "VD: <code>/datso 23276345XXX</code>\n\n"
        f"Phí: {money(PRICE_PER_ORDER)}đ\n"
        f"Thời hạn: {ORDER_LIFETIME_MINUTES} phút\n"
        f"Thưởng/OTP: <b>{usd(REWARD_MILLI_PER_OTP)}</b>",
        reply_markup=main_kb()
    )
    await call.answer()


@dp.message(Command("datso"))
async def cmd_datso(message: Message):
    await register_user(message.from_user)
    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        await message.answer("Cú pháp: <code>/datso MA_TUYEN</code>")
        return

    await message.answer("⏳ Đang gửi yêu cầu…")
    ok, res = await create_number_order(message.from_user.id, parts[1].strip())
    if not ok:
        await message.answer(f"❌ {safe(res)}")
        return

    await message.answer(
        "✅ <b>ĐÃ TẠO ĐƠN</b>\n\n"
        f"Request ID: <code>{safe(res['request_id'])}</code>\n"
        f"Số: <code>{safe(res['phone'])}</code>\n"
        f"Quốc gia: {safe(res['country'])}\n"
        f"Nhà mạng: {safe(res['operator'])}\n"
        f"Hết hạn: {safe(res['expires_at'])}\n\n"
        "⏳ Đang chờ OTP — bot sẽ gửi khi có.\n"
        f"💵 Bạn sẽ nhận <b>{usd(REWARD_MILLI_PER_OTP)}</b>/OTP."
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
# DEPOSIT (VND)
# =====================================================

@dp.callback_query(F.data == "deposit_help")
async def cb_deposit_help(call: CallbackQuery):
    await call.message.edit_text(
        "➕ <b>NẠP VND</b>\n\n"
        "Gửi: <code>/nap 50000</code>\n\n"
        "Admin sẽ duyệt thủ công.",
        reply_markup=main_kb()
    )
    await call.answer()


@dp.message(Command("nap"))
async def cmd_nap(message: Message):
    await register_user(message.from_user)
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Dùng: <code>/nap 50000</code>"); return
    amount = int(parts[1])
    if not 10000 <= amount <= 10000000:
        await message.answer("Số tiền từ 10.000đ đến 10.000.000đ."); return

    rid = await create_deposit(message.from_user.id, amount)
    await message.answer(
        "✅ <b>ĐÃ TẠO YÊU CẦU NẠP</b>\n\n"
        f"Mã: <code>#{rid}</code>\n"
        f"Số tiền: <b>{money(amount)}đ</b>\n"
        "Chờ Admin duyệt."
    )
    try:
        await bot.send_message(
            ADMIN_ID,
            "💳 <b>NẠP VND</b>\n\n"
            f"Mã: #{rid}\nUser: <code>{message.from_user.id}</code>\n"
            f"Số tiền: <b>{money(amount)}đ</b>\n"
            f"Duyệt: <code>/napduyet {rid}</code>"
        )
    except Exception: pass


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

def tx_line(amount, unit, tx_type, note):
    if unit == "USD_MILLI":
        sign = "+" if amount >= 0 else ""
        return f"• {sign}{usd(amount)} | {safe(tx_type)}\n  {safe(note)}"
    sign = "+" if amount >= 0 else ""
    return f"• {sign}{money(amount)}đ | {safe(tx_type)}\n  {safe(note)}"


@dp.callback_query(F.data == "history")
async def cb_history(call: CallbackQuery):
    rows = await get_transactions(call.from_user.id)
    text = "📜 <b>LỊCH SỬ</b>\n\nChưa có giao dịch." if not rows else \
        "\n".join(["📜 <b>LỊCH SỬ</b>\n"] + [tx_line(*r[:4]) for r in rows])
    await call.message.edit_text(text, reply_markup=main_kb())
    await call.answer()


@dp.message(Command("history"))
async def cmd_history(message: Message):
    rows = await get_transactions(message.from_user.id)
    if not rows:
        await message.answer("Chưa có giao dịch."); return
    await message.answer("\n".join(["📜 <b>LỊCH SỬ</b>\n"] + [tx_line(*r[:4]) for r in rows]))


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
            bal      = (await (await db.execute("SELECT COALESCE(SUM(balance),0) FROM users")).fetchone())[0]
            tot_usd  = (await (await db.execute("SELECT COALESCE(SUM(usd_milli),0) FROM users")).fetchone())[0]
            orders   = (await (await db.execute("SELECT COUNT(*) FROM orders")).fetchone())[0]
            pending  = (await (await db.execute("SELECT COUNT(*) FROM orders WHERE status='PENDING'")).fetchone())[0]
            completed= (await (await db.execute("SELECT COUNT(*) FROM orders WHERE status='COMPLETED'")).fetchone())[0]
            dep      = (await (await db.execute("SELECT COUNT(*) FROM deposits WHERE status='PENDING'")).fetchone())[0]
            wd       = (await (await db.execute("SELECT COUNT(*) FROM withdrawals WHERE status='PENDING'")).fetchone())[0]
        await call.message.answer(
            "📊 <b>THỐNG KÊ</b>\n\n"
            f"👥 Users: <b>{users}</b>\n"
            f"📦 Đơn: <b>{orders}</b> (chờ <b>{pending}</b>, xong <b>{completed}</b>)\n"
            f"💰 VND tổng: <b>{money(bal)}đ</b>\n"
            f"💵 USD tổng: <b>{usd(tot_usd)}</b>\n"
            f"💳 Nạp chờ: <b>{dep}</b>\n"
            f"💸 Rút chờ: <b>{wd}</b>"
        )

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

    elif call.data == "admin_deposits":
        async with aiosqlite.connect(DB_PATH) as db:
            rows = await (await db.execute("""
                SELECT id, user_id, amount FROM deposits
                WHERE status='PENDING' ORDER BY id DESC LIMIT 15
            """)).fetchall()
        if not rows:
            await call.message.answer("Không có nạp chờ.")
        else:
            lines = ["💳 <b>NẠP CHỜ</b>\n"]
            for rid, uid, amt in rows:
                lines.append(
                    f"#{rid} | User <code>{uid}</code>\n"
                    f"Số tiền: <b>{money(amt)}đ</b>\n"
                    f"Duyệt: <code>/napduyet {rid}</code>"
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
# ADMIN ORDER / BALANCE / DEPOSIT / WITHDRAW
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


@dp.message(Command("cong"))
async def cmd_cong(message: Message):
    if not is_admin(message.from_user.id): return
    p = message.text.split()
    if len(p) != 3 or not p[1].isdigit() or not p[2].isdigit():
        await message.answer("Dùng: <code>/cong USER_ID SOTIEN</code>"); return
    ok, r = await change_balance(int(p[1]), int(p[2]), "ADMIN_ADD", "Admin cộng")
    if not ok: await message.answer(safe(r)); return
    await message.answer(f"✅ Cộng {money(p[2])}đ. Dư mới: {money(r)}đ")


@dp.message(Command("tru"))
async def cmd_tru(message: Message):
    if not is_admin(message.from_user.id): return
    p = message.text.split()
    if len(p) != 3 or not p[1].isdigit() or not p[2].isdigit():
        await message.answer("Dùng: <code>/tru USER_ID SOTIEN</code>"); return
    ok, r = await change_balance(int(p[1]), -int(p[2]), "ADMIN_REMOVE", "Admin trừ")
    if not ok: await message.answer(safe(r)); return
    await message.answer(f"✅ Trừ {money(p[2])}đ. Dư mới: {money(r)}đ")


@dp.message(Command("napduyet"))
async def cmd_napduyet(message: Message):
    if not is_admin(message.from_user.id): return
    p = message.text.split()
    if len(p) != 2 or not p[1].isdigit():
        await message.answer("Dùng: <code>/napduyet ID</code>"); return
    rid = int(p[1])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("BEGIN IMMEDIATE")
        cur = await db.execute("SELECT user_id, amount, status FROM deposits WHERE id=?", (rid,))
        row = await cur.fetchone()
        if not row:
            await db.rollback(); await message.answer("Không tìm thấy."); return
        uid, amt, status = row
        if status != "PENDING":
            await db.rollback(); await message.answer("Đã xử lý."); return
        await db.execute("UPDATE deposits SET status='APPROVED', processed_at=? WHERE id=?",
                         (now_text(), rid))
        await db.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amt, uid))
        await db.execute("""
            INSERT INTO transactions (user_id, amount, unit, tx_type, note, created_at)
            VALUES (?, ?, 'VND', 'DEPOSIT', ?, ?)
        """, (uid, amt, f"Nạp #{rid}", now_text()))
        await db.commit()
    await message.answer(f"✅ Đã duyệt nạp #{rid}: {money(amt)}đ cho user {uid}")
    try: await bot.send_message(uid, f"✅ Nạp #{rid} được duyệt. +{money(amt)}đ")
    except Exception: pass


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
            INSERT INTO transactions (user_id, amount, unit, tx_type, note, created_at)
            VALUES (?, ?, 'USD_MILLI', 'WITHDRAW_REFUND', ?, ?)
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
# MK OTP POLLER — gửi OTP vào GROUP
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
            if u["username"]:
                user_name += f" (@{u['username']})"

        text = (
            f"🔔 <b>OTP MỚI</b>\n\n"
            f"👤 User: {user_link(row['user_id'], user_name)}\n"
            f"🆔 ID: <code>{row['user_id']}</code>\n"
            f"📦 Đơn: <code>#{row['id']}</code>\n"
            f"📱 Số: <code>{safe(row['phone'])}</code>\n"
            f"🔑 OTP: <code>{safe(otp_code)}</code>\n"
            f"💵 Thưởng: <b>{usd(reward_milli)}</b>"
        )
        if full_sms:
            text += f"\n\n💬 {safe(full_sms, 300)}"

        sent_anywhere = False

        if OTP_GROUP_ID:
            try:
                await bot.send_message(OTP_GROUP_ID, text)
                sent_anywhere = True
                logger.info("OTP đã gửi vào group %s", OTP_GROUP_ID)
            except Exception:
                logger.exception("Gửi OTP vào group %s thất bại", OTP_GROUP_ID)

        if ADMIN_ID and ADMIN_ID != OTP_GROUP_ID:
            try:
                await bot.send_message(ADMIN_ID, text)
                sent_anywhere = True
            except Exception:
                logger.exception("Gửi OTP cho admin thất bại")

        try:
            user_id = row["user_id"]
            if user_id not in (ADMIN_ID, OTP_GROUP_ID):
                await bot.send_message(
                    user_id,
                    text + f"\n\nDùng <code>/donhang {row['id']}</code> để xem."
                )
                sent_anywhere = True
        except Exception:
            logger.warning("Gửi OTP cho user %s thất bại", row["user_id"])

        if not sent_anywhere:
            logger.error("Không gửi được OTP ở đâu cả cho order #%s", row["id"])

    async def _update_completed(self, oid, otp, sms, reward):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                UPDATE orders
                SET status='COMPLETED', otp_code=?, full_sms=?,
                    reward_milli=?, updated_at=?
                WHERE id=? AND status='PENDING'
            """, (otp, sms, reward, now_text(), oid))
            await db.commit()

    async def _update_expired(self, oid):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE orders SET status='EXPIRED', updated_at=? WHERE id=? AND status='PENDING'",
                             (now_text(), oid))
            await db.commit()

    async def _update_failed(self, oid):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE orders SET status='FAILED', updated_at=? WHERE id=? AND status='PENDING'",
                             (now_text(), oid))
            await db.commit()

    async def _poll_once(self):
        rows = await get_pending_requests(limit=MK_POLL_BATCH)
        if not rows:
            return 0, 0, False

        ids = []
        for r in rows:
            try: ids.append(int(r["request_id"]))
            except (ValueError, TypeError): await self._update_failed(r["id"])
        if not ids:
            return 0, 0, False

        data, err = await api_request("POST", "check/status", {"request_ids": ids})
        if err:
            logger.warning("/check/status lỗi: %s", err)
            return 0, 0, True

        inner   = data.get("data") if isinstance(data, dict) else None
        results = inner.get("results") if isinstance(inner, dict) else None
        if not isinstance(results, list):
            logger.warning("Response lạ: %s", str(data)[:200])
            return 0, 0, True

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
                    logger.warning("request_id %s success nhưng otp rỗng", rid)
                    await self._update_failed(row["id"])
                    continue

                reward = REWARD_MILLI_PER_OTP
                ok, _ = await change_usd(row["user_id"], reward,
                                          "OTP_REWARD", f"Thưởng OTP #{row['id']}")
                if not ok:
                    logger.error("Cộng thưởng user %s thất bại", row["user_id"])
                    reward = 0

                await self._update_completed(row["id"], otp, sms, reward)
                await self._broadcast_otp(row, otp, sms, reward)
                new_otp += 1

            elif status == "expired":
                await self._update_expired(row["id"])
            elif status == "not_found":
                logger.warning("request_id %s not_found", rid)
                await self._update_failed(row["id"])

        return checked, new_otp, False

    async def run_forever(self):
        logger.info("Poller started: min=%ss max=%ss batch=%d group=%s",
                    MK_POLL_MIN_SEC, MK_POLL_MAX_SEC, MK_POLL_BATCH, OTP_GROUP_ID)
        while True:
            try:
                checked, new_otp, api_error = await self._poll_once()
                if api_error:
                    self._consecutive_errors += 1
                    self.interval = min(MK_POLL_MAX_SEC,
                                        max(self.interval * 2, self.interval + 5))
                    if self._consecutive_errors == self.MAX_CONSECUTIVE_ERRORS:
                        try:
                            await bot.send_message(ADMIN_ID,
                                f"⚠️ Poller lỗi {self._consecutive_errors} lần. Interval: {self.interval}s")
                        except Exception: pass
                else:
                    self._consecutive_errors = 0
                    if checked == 0:
                        self.interval = min(MK_POLL_MAX_SEC, self.interval + 5)
                    elif new_otp > 0:
                        self.interval = max(MK_POLL_MIN_SEC, self.interval - 2)
                    else:
                        self.interval = max(MK_POLL_MIN_SEC, self.interval - 1)
            except Exception:
                logger.exception("Poller crash")
                self._consecutive_errors += 1
                self.interval = min(MK_POLL_MAX_SEC, max(self.interval * 2, 30))
            await asyncio.sleep(self.interval)


# =====================================================
# FALLBACK
# =====================================================

@dp.message(F.text)
async def unknown(message: Message):
    await message.answer("Gõ /start để mở menu FAST IVAS.")


# =====================================================
# MAIN
# =====================================================

async def main():
    global _mk_poller
    await init_db()
    await expire_old_orders()

    if MK_POLL_ENABLED:
        _mk_poller = MkOtpPoller()
        asyncio.create_task(_mk_poller.run_forever())
        logger.info("Poller task created.")

    logger.info("FAST IVAS starting... group=%s admin=%s", OTP_GROUP_ID, ADMIN_ID)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())