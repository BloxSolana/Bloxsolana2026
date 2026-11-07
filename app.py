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
from pathlib import Path
from urllib.parse import parse_qsl, quote
from datetime import datetime, timedelta, timezone
from aiohttp import web
from types import SimpleNamespace

import aiohttp
import libsql_experimental as libsql
from aiogram import Bot, Dispatcher, F, BaseMiddleware
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    BotCommand, BotCommandScopeChat, BotCommandScopeDefault,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, MenuButtonWebApp, WebAppInfo
)
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest

# =====================================================
# CONFIG
# =====================================================
BOT_TOKEN      = os.getenv("BOT_TOKEN", "").strip()
WEBAPP_URL     = os.getenv("WEBAPP_URL", "").strip()
ADMIN_ID       = int(os.getenv("ADMIN_ID", "0") or 0)
OTP_GROUP_ID   = int(os.getenv("OTP_GROUP_ID", "-1004341368656"))
OTP_GROUP_URL  = "https://t.me/LIVEOTPIVAS"
MAIN_CHANNEL_URL = "https://t.me/FastNode_1"

MK_API_KEY     = os.getenv("MK_API_KEY", "").strip()
MK_API_BASE    = "https://mknetworkbd.com/api/v3/public"
NP_API_KEY     = os.getenv("NP_API_KEY", "").strip()
NP_API_BASE    = "https://numberpanel.tech/api"
BASHA_API_KEY  = os.getenv("BASHA_API_KEY", "").strip()
BASHA_API_BASE = "https://basha.cc/api"

TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL", "")
TURSO_AUTH_TOKEN   = os.getenv("TURSO_AUTH_TOKEN", "")

ORDER_LIFETIME_MINUTES = 15
REWARD_MILLI_PER_OTP   = 2
MIN_WITHDRAW_MILLI     = 1000
MAX_HISTORY_RECORDS    = 100
HISTORY_PER_PAGE       = 8
MK_POLL_ENABLED        = True
MK_POLL_MIN_SEC        = 10
MK_POLL_MAX_SEC        = 30
MK_POLL_BATCH          = 100

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FAST_IVAS")

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp  = Dispatcher()
BOT_USERNAME = ""
VN_TZ = timezone(timedelta(hours=7))

def safe(text):
    return html.escape(str(text))

# =====================================================
# DATABASE
# =====================================================
_db = None
_db_lock = asyncio.Lock()

async def get_db():
    global _db
    if _db is None:
        try:
            _db = libsql.connect(
                database=TURSO_DATABASE_URL,
                auth_token=TURSO_AUTH_TOKEN
            )
            await init_db()
        except Exception as e:
            logger.error(f"DB connect error: {e}")
            raise
    return _db

async def init_db():
    queries = [
        """CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            balance_milli INTEGER DEFAULT 0,
            total_spent_milli INTEGER DEFAULT 0,
            total_earned_milli INTEGER DEFAULT 0,
            created_at TEXT,
            is_banned INTEGER DEFAULT 0
        )""",
        """CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            user_id INTEGER,
            phone_number TEXT,
            country_code TEXT,
            country_name TEXT,
            service TEXT,
            service_name TEXT,
            source TEXT,
            external_id TEXT,
            status TEXT,
            otp_code TEXT,
            price_milli INTEGER,
            created_at TEXT,
            expires_at TEXT,
            completed_at TEXT,
            notified INTEGER DEFAULT 0
        )""",
        """CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            amount_milli INTEGER,
            description TEXT,
            created_at TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount_milli INTEGER,
            ton_address TEXT,
            status TEXT,
            requested_at TEXT,
            processed_at TEXT,
            processed_by INTEGER
        )""",
        """CREATE TABLE IF NOT EXISTS admin_numbers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_number TEXT UNIQUE,
            source TEXT,
            added_by INTEGER,
            added_at TEXT,
            is_used INTEGER DEFAULT 0
        )""",
        """CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id)""",
        """CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)""",
        """CREATE INDEX IF NOT EXISTS idx_orders_external ON orders(external_id)""",
        """CREATE INDEX IF NOT EXISTS idx_history_user ON history(user_id)"""
    ]
    for q in queries:
        try:
            await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, lambda: _db.execute(q)),
                timeout=10.0
            )
        except Exception as e:
            logger.error(f"DB init error: {e}")

async def db_query(query, params=(), fetchone=False):
    async with _db_lock:
        db = await get_db()
        try:
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, lambda: db.execute(query, params)),
                timeout=10.0
            )
            if fetchone:
                return result.fetchone()
            return result.fetchall()
        except Exception as e:
            logger.error(f"DB query error: {e}")
            raise

async def db_execute(query, params=()):
    async with _db_lock:
        db = await get_db()
        try:
            await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, lambda: db.execute(query, params)),
                timeout=10.0
            )
            db.commit()
        except Exception as e:
            logger.error(f"DB execute error: {e}")
            raise

# =====================================================
# COUNTRY DATA
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

def get_country_info(code):
    code = str(code).replace("+", "")
    for prefix in sorted(COUNTRY_CODES.keys(), key=len, reverse=True):
        if code.startswith(prefix):
            return COUNTRY_CODES[prefix]
    return ("Unknown", "🏳️")

def get_flag_emoji(code):
    return get_country_info(code)[1]

def get_country_name(code):
    return get_country_info(code)[0]

# =====================================================
# API WRAPPERS
# =====================================================
async def mk_api_request(endpoint, params=None):
    headers = {"Authorization": f"Bearer {MK_API_KEY}"}
    url = f"{MK_API_BASE}/{endpoint}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers, params=params, timeout=30) as resp:
                return await resp.json()
        except Exception as e:
            logger.error(f"MK API error: {e}")
            return None

async def np_api_request(action, params=None):
    if not params:
        params = {}
    params["key"] = NP_API_KEY
    params["action"] = action
    url = NP_API_BASE
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, data=params, timeout=30) as resp:
                text = await resp.text()
                try:
                    return json.loads(text)
                except:
                    return {"status": "error", "response": text}
        except Exception as e:
            logger.error(f"NP API error: {e}")
            return None

async def basha_api_request(action, params=None):
    if not params:
        params = {}
    params["api_key"] = BASHA_API_KEY
    params["action"] = action
    url = f"{BASHA_API_BASE}/{action}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params, timeout=30) as resp:
                return await resp.json()
        except Exception as e:
            logger.error(f"Basha API error: {e}")
            return None

# =====================================================
# MIDDLEWARE
# =====================================================
class ErrorMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        try:
            return await handler(event, data)
        except Exception as e:
            logger.error(f"Handler error: {e}")
            try:
                if isinstance(event, Message):
                    await event.answer(f"⚠️ <b>Lỗi:</b> <code>{safe(str(e))}</code>")
                elif isinstance(event, CallbackQuery):
                    await event.answer(f"⚠️ Lỗi: {safe(str(e))[:50]}", show_alert=True)
            except: pass

dp.message.middleware(ErrorMiddleware())
dp.callback_query.middleware(ErrorMiddleware())

# =====================================================
# BOT COMMANDS
# =====================================================
@dp.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    now = datetime.now(VN_TZ).isoformat()
    
    existing = await db_query("SELECT user_id FROM users WHERE user_id = ?", (user.id,), fetchone=True)
    if not existing:
        await db_execute(
            "INSERT INTO users (user_id, username, full_name, created_at) VALUES (?, ?, ?, ?)",
            (user.id, user.username, user.full_name, now)
        )
    
    await message.answer(
        "👋 <b>Chào mừng đến Fast Ivas!</b>\n\n"
        "🚀 Hệ thống nhận mã OTP tự động đa nguồn (MK, NP, BS)\n"
        "💰 Giá rẻ - Ổn định - Tự động 24/7",
        reply_markup=ReplyKeyboardRemove()
    )
    
    webapp_url = f"{WEBAPP_URL}?user_id={user.id}" if WEBAPP_URL else None
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Mở Mini App", web_app=WebAppInfo(url=webapp_url))],
        [InlineKeyboardButton(text="📢 Kênh chính", url=MAIN_CHANNEL_URL)],
        [InlineKeyboardButton(text="💬 Group OTP", url=OTP_GROUP_URL)]
    ])
    
    await message.answer(
        "👇 Nhấn nút bên dưới để mở Mini App:",
        reply_markup=kb
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📖 <b>Hướng dẫn sử dụng:</b>\n\n"
        "1️⃣ Nhấn /start để mở Mini App\n"
        "2️⃣ Chọn quốc gia và dịch vụ cần mã\n"
        "3️⃣ Thanh toán và nhận số\n"
        "4️⃣ Chờ OTP tự động về (tối đa 15 phút)\n\n"
        "📌 Lưu ý: Số dùng 1 lần, hết hạn sau 15 phút nếu không nhận OTP",
        reply_markup=ReplyKeyboardRemove()
    )

# =====================================================
# ADMIN COMMANDS
# =====================================================
def is_admin(user_id):
    return user_id == ADMIN_ID

@dp.message(Command("addbal"))
async def cmd_addbal(message: Message):
    if not is_admin(message.from_user.id):
        return await message.answer("❌ Không có quyền!")
    
    parts = message.text.split()
    if len(parts) < 3:
        return await message.answer("Usage: /addbal <user_id> <amount>")
    
    try:
        target_id = int(parts[1])
        amount = int(parts[2])
    except:
        return await message.answer("❌ Tham số không hợp lệ!")
    
    await db_execute(
        "UPDATE users SET balance_milli = balance_milli + ? WHERE user_id = ?",
        (amount, target_id)
    )
    await db_execute(
        "INSERT INTO history (user_id, type, amount_milli, description, created_at) VALUES (?, 'add', ?, ?, ?)",
        (target_id, amount, f"Admin add by {message.from_user.id}", datetime.now(VN_TZ).isoformat())
    )
    
    await message.answer(f"✅ Đã cộng {amount} milli cho user {target_id}")
    try:
        await bot.send_message(target_id, f"💰 Tài khoản được cộng <code>{amount}</code> milli bởi Admin")
    except:
        pass

@dp.message(Command("deductbal"))
async def cmd_deductbal(message: Message):
    if not is_admin(message.from_user.id):
        return await message.answer("❌ Không có quyền!")
    
    parts = message.text.split()
    if len(parts) < 3:
        return await message.answer("Usage: /deductbal <user_id> <amount>")
    
    try:
        target_id = int(parts[1])
        amount = int(parts[2])
    except:
        return await message.answer("❌ Tham số không hợp lệ!")
    
    await db_execute(
        "UPDATE users SET balance_milli = balance_milli - ? WHERE user_id = ?",
        (amount, target_id)
    )
    await db_execute(
        "INSERT INTO history (user_id, type, amount_milli, description, created_at) VALUES (?, 'deduct', ?, ?, ?)",
        (target_id, amount, f"Admin deduct by {message.from_user.id}", datetime.now(VN_TZ).isoformat())
    )
    
    await message.answer(f"✅ Đã trừ {amount} milli từ user {target_id}")

@dp.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    if not is_admin(message.from_user.id):
        return await message.answer("❌ Không có quyền!")
    
    text = message.text.replace("/broadcast", "").strip()
    if not text:
        return await message.answer("Usage: /broadcast <message>")
    
    users = await db_query("SELECT user_id FROM users")
    sent = 0
    failed = 0
    
    for row in users:
        try:
            await bot.send_message(row[0], f"📢 <b>Thông báo:</b>\n\n{text}")
            sent += 1
            await asyncio.sleep(0.1)
        except:
            failed += 1
    
    await message.answer(f"✅ Gửi thành công: {sent}\n❌ Thất bại: {failed}")

@dp.message(Command("health"))
async def cmd_health(message: Message):
    if not is_admin(message.from_user.id):
        return await message.answer("❌ Không có quyền!")
    
    users = await db_query("SELECT COUNT(*) FROM users", fetchone=True)
    orders = await db_query("SELECT COUNT(*) FROM orders", fetchone=True)
    pending = await db_query("SELECT COUNT(*) FROM orders WHERE status = 'pending'", fetchone=True)
    
    await message.answer(
        f"🏥 <b>System Health</b>\n\n"
        f"👥 Users: {users[0]}\n"
        f"📦 Total Orders: {orders[0]}\n"
        f"⏳ Pending: {pending[0]}\n"
        f"🕐 Time: {datetime.now(VN_TZ).strftime('%Y-%m-%d %H:%M:%S')}"
    )

@dp.message(Command("pollnow"))
async def cmd_pollnow(message: Message):
    if not is_admin(message.from_user.id):
        return await message.answer("❌ Không có quyền!")
    
    await message.answer("🔄 Đang force poll...")
    asyncio.create_task(poll_otp_once())
    await message.answer("✅ Đã trigger poll OTP")

# =====================================================
# OTP POLLER
# =====================================================
async def poll_otp_once():
    pending = await db_query("SELECT * FROM orders WHERE status = 'pending' AND source IN ('mk', 'np', 'bs')")
    if not pending:
        return
    
    for order in pending:
        order_dict = {
            'order_id': order[0], 'user_id': order[1], 'phone_number': order[2],
            'country_code': order[3], 'country_name': order[4], 'service': order[5],
            'service_name': order[6], 'source': order[7], 'external_id': order[8],
            'status': order[9], 'otp_code': order[10], 'price_milli': order[11]
        }
        
        otp = None
        
        if order_dict['source'] == 'mk':
            resp = await mk_api_request(f"check/{order_dict['external_id']}")
            if resp and resp.get('data', {}).get('code'):
                otp = resp['data']['code']
        elif order_dict['source'] == 'np':
            resp = await np_api_request("status", {"id": order_dict['external_id']})
            if resp and 'sms' in resp:
                otp = resp['sms']
        elif order_dict['source'] == 'bs':
            resp = await basha_api_request("check", {"order_id": order_dict['external_id']})
            if resp and resp.get('code'):
                otp = resp['code']
        
        if otp:
            await process_otp_received(order_dict['order_id'], otp)

async def process_otp_received(order_id, otp):
    now = datetime.now(VN_TZ).isoformat()
    await db_execute(
        "UPDATE orders SET status = 'completed', otp_code = ?, completed_at = ? WHERE order_id = ?",
        (otp, now, order_id)
    )
    
    order = await db_query("SELECT user_id, phone_number, country_name FROM orders WHERE order_id = ?", (order_id,), fetchone=True)
    if not order:
        return
    
    user_id, phone, country = order
    
    await db_execute(
        "UPDATE users SET balance_milli = balance_milli + ?, total_earned_milli = total_earned_milli + ? WHERE user_id = ?",
        (REWARD_MILLI_PER_OTP, REWARD_MILLI_PER_OTP, user_id)
    )
    
    msg = (
        f"✅ <b>OTP ĐÃ VỀ!</b>\n\n"
        f"📱 Số: <code>{phone}</code>\n"
        f"🌍 Quốc gia: {country}\n"
        f"🔢 Mã OTP: <code>{otp}</code>\n\n"
        f"💰 Bạn nhận được +{REWARD_MILLI_PER_OTP} milli thưởng!"
    )
    
    try:
        await bot.send_message(user_id, msg)
    except:
        pass
    
    try:
        await bot.send_message(OTP_GROUP_ID, f"📤 OTP gửi đến User {user_id}:\n📱 {phone}\n🔢 {otp}")
    except:
        pass

async def otp_poller():
    while True:
        if MK_POLL_ENABLED:
            try:
                await poll_otp_once()
            except Exception as e:
                logger.error(f"Poller error: {e}")
        await asyncio.sleep(random.randint(MK_POLL_MIN_SEC, MK_POLL_MAX_SEC))

# =====================================================
# WEB SERVER & MINI APP (ZYNEXA STYLE)
# =====================================================
async def webapp_handler(request):
    user_id = request.query.get('user_id', '')
    html_content = f'''<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Fast Ivas - OTP Service</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
        
        :root {{
            --bg: #0a1628;
            --bg-secondary: #0d1f35;
            --surface: rgba(255, 255, 255, 0.05);
            --surface-hover: rgba(255, 255, 255, 0.08);
            --border: rgba(255, 255, 255, 0.1);
            --text: #ffffff;
            --text-muted: rgba(255, 255, 255, 0.6);
            --text-dim: rgba(255, 255, 255, 0.4);
            --primary: #00d4ff;
            --secondary: #00ff88;
            --accent-gradient: linear-gradient(135deg, #00d4ff 0%, #00ff88 100%);
            --glass: rgba(13, 31, 53, 0.8);
            --card-bg: rgba(255, 255, 255, 0.03);
            --success: #00ff88;
            --warning: #ffb800;
            --danger: #ff4757;
        }}
        
        body {{
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            overflow-x: hidden;
            padding-bottom: 90px;
        }}
        
        /* Background mesh */
        .bg-mesh {{
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: 
                radial-gradient(circle at 0% 0%, rgba(0, 212, 255, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 100% 100%, rgba(0, 255, 136, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 50% 50%, rgba(0, 212, 255, 0.05) 0%, transparent 70%);
            pointer-events: none;
            z-index: 0;
        }}
        
        /* Header */
        .header {{
            position: fixed;
            top: 0; left: 0; right: 0;
            height: 70px;
            background: var(--glass);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 20px;
            z-index: 100;
        }}
        
        .menu-btn {{
            width: 44px; height: 44px;
            border-radius: 14px;
            background: var(--surface);
            border: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 5px;
            cursor: pointer;
            transition: all 0.3s;
        }}
        
        .menu-btn:hover {{ background: var(--surface-hover); transform: scale(1.05); }}
        .menu-btn span {{
            width: 20px; height: 2px;
            background: var(--text);
            border-radius: 2px;
            transition: all 0.3s;
        }}
        
        .logo {{
            font-size: 22px;
            font-weight: 800;
            background: var(--accent-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: 1px;
        }}
        
        .balance-pill {{
            background: var(--surface);
            border: 1px solid var(--border);
            padding: 10px 18px;
            border-radius: 24px;
            font-size: 14px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        
        .balance-pill::before {{
            content: '💎';
            font-size: 12px;
        }}
        
        /* Sidebar */
        .sidebar {{
            position: fixed;
            top: 0; left: -320px;
            width: 300px; height: 100vh;
            background: var(--glass);
            backdrop-filter: blur(30px);
            border-right: 1px solid var(--border);
            z-index: 200;
            transition: left 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            padding: 90px 20px 20px;
        }}
        
        .sidebar.open {{ left: 0; }}
        .sidebar-overlay {{
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.6);
            z-index: 150;
            opacity: 0; pointer-events: none;
            transition: opacity 0.3s;
        }}
        .sidebar-overlay.active {{ opacity: 1; pointer-events: auto; }}
        
        .nav-item {{
            padding: 18px;
            border-radius: 16px;
            margin-bottom: 8px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 14px;
            transition: all 0.3s;
            border: 1px solid transparent;
            font-weight: 500;
        }}
        
        .nav-item:hover {{
            background: var(--surface-hover);
            border-color: var(--border);
            transform: translateX(4px);
        }}
        
        .nav-item.active {{
            background: var(--accent-gradient);
            border-color: transparent;
            font-weight: 600;
        }}
        
        .nav-item .icon {{ font-size: 22px; width: 28px; text-align: center; }}
        
        /* Main Content */
        .main-content {{
            margin-top: 90px;
            padding: 20px;
            max-width: 600px;
            margin-left: auto;
            margin-right: auto;
        }}
        
        /* Cards */
        .glass-card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 24px;
            padding: 24px;
            margin-bottom: 20px;
            backdrop-filter: blur(10px);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        
        .glass-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.4);
        }}
        
        .card-title {{
            font-size: 13px;
            color: var(--text-dim);
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 20px;
            font-weight: 600;
        }}
        
        /* Phone Order Card */
        .order-card {{
            background: linear-gradient(135deg, rgba(0, 212, 255, 0.08) 0%, rgba(0, 255, 136, 0.03) 100%);
            border: 1px solid rgba(0, 212, 255, 0.2);
            border-radius: 20px;
            padding: 24px;
            margin-bottom: 16px;
            position: relative;
            overflow: hidden;
            transition: all 0.3s;
        }}
        
        .order-card::before {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; height: 2px;
            background: var(--accent-gradient);
        }}
        
        .order-card.has-otp {{
            background: linear-gradient(135deg, rgba(0, 255, 136, 0.1) 0%, rgba(0, 212, 255, 0.05) 100%);
            border-color: var(--success);
            animation: glow 2s ease-in-out infinite;
        }}
        
        @keyframes glow {{
            0%, 100% {{ box-shadow: 0 0 0 0 rgba(0, 255, 136, 0.4); }}
            50% {{ box-shadow: 0 0 30px 5px rgba(0, 255, 136, 0.2); }}
        }}
        
        .phone-number {{
            font-size: 28px;
            font-weight: 700;
            font-family: 'Courier New', monospace;
            letter-spacing: 1px;
            margin-bottom: 12px;
            background: var(--accent-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .order-meta {{
            display: flex;
            gap: 16px;
            color: var(--text-muted);
            font-size: 14px;
            margin-bottom: 20px;
            align-items: center;
        }}
        
        .flag {{ font-size: 20px; }}
        
        .status-badge {{
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
        }}
        
        .status-pending {{ background: rgba(255, 184, 0, 0.2); color: var(--warning); }}
        .status-success {{ background: rgba(0, 255, 136, 0.2); color: var(--success); }}
        .status-cancelled {{ background: rgba(255, 71, 87, 0.2); color: var(--danger); }}
        
        .copy-btn {{
            background: var(--surface);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 12px 24px;
            border-radius: 12px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            transition: all 0.2s;
        }}
        
        .copy-btn:hover {{
            background: var(--primary);
            border-color: var(--primary);
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(0, 212, 255, 0.3);
        }}
        
        .copy-btn.copied {{
            background: var(--success);
            border-color: var(--success);
        }}
        
        .otp-display {{
            font-size: 36px;
            font-weight: 800;
            background: var(--accent-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 16px 0;
            letter-spacing: 8px;
            text-align: center;
        }}
        
        .otp-label {{
            text-align: center;
            color: var(--text-dim);
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 8px;
        }}
        
        /* Grid Stats */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
        }}
        
        .stat-box {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 20px;
            text-align: center;
            transition: all 0.2s;
        }}
        
        .stat-box:hover {{ transform: translateY(-2px); background: var(--surface-hover); }}
        
        .stat-value {{
            font-size: 32px;
            font-weight: 800;
            background: var(--accent-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 6px;
        }}
        
        .stat-label {{ font-size: 12px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 1px; }}
        
        /* Country List */
        .country-grid {{
            display: grid;
            gap: 10px;
        }}
        
        .country-item {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 18px;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 14px;
        }}
        
        .country-item:hover {{
            background: var(--surface-hover);
            border-color: var(--primary);
            transform: translateX(4px);
        }}
        
        .country-info {{ flex: 1; }}
        .country-name {{ font-weight: 600; font-size: 15px; margin-bottom: 2px; }}
        .country-code-small {{ color: var(--text-dim); font-size: 13px; }}
        
        /* Bottom Nav */
        .bottom-nav {{
            position: fixed;
            bottom: 0; left: 0; right: 0;
            height: 80px;
            background: var(--glass);
            backdrop-filter: blur(20px);
            border-top: 1px solid var(--border);
            display: flex;
            justify-content: space-around;
            align-items: center;
            z-index: 100;
            padding-bottom: env(safe-area-inset-bottom, 10px);
        }}
        
        .nav-btn {{
            flex: 1;
            height: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 6px;
            cursor: pointer;
            color: var(--text-dim);
            transition: all 0.2s;
            border: none;
            background: transparent;
            font-size: 11px;
            font-weight: 500;
            position: relative;
        }}
        
        .nav-btn.active {{
            color: var(--primary);
        }}
        
        .nav-btn.active::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 50%;
            transform: translateX(-50%);
            width: 40px;
            height: 3px;
            background: var(--accent-gradient);
            border-radius: 0 0 10px 10px;
        }}
        
        .nav-icon {{ font-size: 24px; transition: transform 0.2s; }}
        .nav-btn:hover .nav-icon {{ transform: scale(1.1); }}
        
        /* Utility */
        .hidden {{ display: none !important; }}
        .text-center {{ text-align: center; }}
        .mb-4 {{ margin-bottom: 16px; }}
        .mt-4 {{ margin-top: 16px; }}
        .flex {{ display: flex; }}
        .gap-2 {{ gap: 10px; }}
        
        .btn-primary {{
            background: var(--accent-gradient);
            border: none;
            color: var(--bg);
            padding: 16px 32px;
            border-radius: 16px;
            font-size: 16px;
            font-weight: 700;
            cursor: pointer;
            width: 100%;
            transition: all 0.2s;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .btn-primary:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(0, 212, 255, 0.4);
        }}
        
        .btn-primary:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }}
        
        .empty-state {{
            text-align: center;
            padding: 50px 20px;
            color: var(--text-dim);
        }}
        
        .empty-state-icon {{ font-size: 56px; margin-bottom: 20px; opacity: 0.4; }}
        .empty-state-text {{ font-size: 15px; }}
        
        /* Loading */
        .spinner {{
            width: 48px; height: 48px;
            border: 3px solid var(--surface);
            border-top-color: var(--primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 30px auto;
        }}
        
        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
        
        /* Admin */
        .admin-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-bottom: 20px;
        }}
        
        .admin-stat {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 24px;
            text-align: center;
        }}
        
        .admin-value {{
            font-size: 36px;
            font-weight: 800;
            background: var(--accent-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .admin-label {{ font-size: 12px; color: var(--text-dim); margin-top: 8px; text-transform: uppercase; letter-spacing: 1px; }}
        
        .input-field {{
            width: 100%;
            background: var(--surface);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 16px 20px;
            border-radius: 16px;
            font-size: 16px;
            margin-bottom: 14px;
            outline: none;
            transition: all 0.2s;
        }}
        
        .input-field:focus {{ 
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(0, 212, 255, 0.1);
        }}
        
        /* Animations */
        .fade-in {{
            animation: fadeIn 0.4s ease;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(15px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        /* Scrollbar */
        ::-webkit-scrollbar {{ width: 6px; }}
        ::-webkit-scrollbar-track {{ background: var(--bg); }}
        ::-webkit-scrollbar-thumb {{ background: var(--surface); border-radius: 3px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: var(--primary); }}
        
        /* Withdraw card */
        .withdraw-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 18px;
            margin-bottom: 12px;
        }}
        
        .withdraw-info {{ margin-bottom: 14px; }}
        .withdraw-row {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            font-size: 14px;
        }}
        .withdraw-label {{ color: var(--text-dim); }}
        .withdraw-value {{ font-weight: 600; }}
        
        .withdraw-actions {{
            display: flex;
            gap: 10px;
        }}
        
        .btn-approve {{
            flex: 1;
            background: var(--success);
            color: var(--bg);
            border: none;
            padding: 12px;
            border-radius: 12px;
            font-weight: 700;
            cursor: pointer;
        }}
        
        .btn-reject {{
            flex: 1;
            background: var(--danger);
            color: white;
            border: none;
            padding: 12px;
            border-radius: 12px;
            font-weight: 700;
            cursor: pointer;
        }}
        
        /* History item */
        .history-item {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 18px;
            margin-bottom: 12px;
        }}
        
        .history-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}
        
        .history-date {{ color: var(--text-dim); font-size: 13px; }}
        
        .history-body {{
            display: flex;
            gap: 12px;
            align-items: flex-start;
        }}
        
        .history-icon {{
            width: 44px;
            height: 44px;
            border-radius: 14px;
            background: var(--card-bg);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
        }}
        
        .history-details {{ flex: 1; }}
        .history-phone {{ font-size: 17px; font-weight: 700; margin-bottom: 4px; font-family: monospace; }}
        .history-meta {{ color: var(--text-muted); font-size: 13px; }}
        
        .history-otp {{
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .otp-code {{
            font-size: 20px;
            font-weight: 800;
            color: var(--success);
            font-family: monospace;
            letter-spacing: 2px;
        }}
    </style>
</head>
<body>
    <div class="bg-mesh"></div>
    
    <!-- Header -->
    <div class="header">
        <div class="menu-btn" onclick="toggleSidebar()">
            <span></span>
            <span></span>
            <span></span>
        </div>
        <div class="logo">FAST IVAS</div>
        <div class="balance-pill" id="header-balance">0 Ⓜ</div>
    </div>
    
    <!-- Sidebar -->
    <div class="sidebar" id="sidebar">
        <div class="nav-item active" onclick="showPage('home'); toggleSidebar()">
            <span class="icon">🏠</span> Trang chủ
        </div>
        <div class="nav-item" onclick="showPage('buy'); toggleSidebar()">
            <span class="icon">🛒</span> Mua số
        </div>
        <div class="nav-item" onclick="showPage('history'); toggleSidebar()">
            <span class="icon">📜</span> Lịch sử
        </div>
        <div class="nav-item" onclick="showPage('wallet'); toggleSidebar()">
            <span class="icon">💰</span> Ví
        </div>
        <div class="nav-item hidden" id="admin-nav" onclick="showPage('admin'); toggleSidebar()">
            <span class="icon">⚙️</span> Admin Panel
        </div>
    </div>
    <div class="sidebar-overlay" id="sidebar-overlay" onclick="toggleSidebar()"></div>
    
    <!-- Main Content -->
    <div class="main-content">
        <!-- Home Page -->
        <div id="page-home" class="page">
            <div class="glass-card">
                <div class="card-title">📊 Tổng quan</div>
                <div class="stats-grid">
                    <div class="stat-box">
                        <div class="stat-value" id="user-balance">0</div>
                        <div class="stat-label">Số dư (Milli)</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value" id="user-orders">0</div>
                        <div class="stat-label">Đơn hôm nay</div>
                    </div>
                </div>
            </div>
            
            <div class="glass-card">
                <div class="card-title">⏳ Đơn đang chờ</div>
                <div id="pending-orders">
                    <div class="empty-state">
                        <div class="empty-state-icon">📭</div>
                        <div class="empty-state-text">Không có đơn nào đang chờ</div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Buy Page -->
        <div id="page-buy" class="page hidden">
            <div class="glass-card">
                <div class="card-title">🌍 Chọn quốc gia</div>
                <div class="country-grid" id="country-list">
                    <div class="spinner"></div>
                </div>
            </div>
        </div>
        
        <!-- History Page -->
        <div id="page-history" class="page hidden">
            <div class="glass-card">
                <div class="card-title">📜 Lịch sử đơn hàng</div>
                <div id="history-list">
                    <div class="spinner"></div>
                </div>
            </div>
        </div>
        
        <!-- Wallet Page -->
        <div id="page-wallet" class="page hidden">
            <div class="glass-card" style="text-align: center; padding: 40px 24px;">
                <div class="card-title" style="margin-bottom: 30px;">💰 Số dư ví</div>
                <div style="font-size: 48px; font-weight: 800; background: var(--accent-gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 10px;" id="wallet-balance">0 Ⓜ</div>
                <div style="color: var(--text-dim); margin-bottom: 30px;">≈ 0 VND</div>
                <button class="btn-primary" onclick="showWithdrawModal()">🏦 Rút tiền</button>
            </div>
            
            <div class="glass-card">
                <div class="card-title">📋 Giao dịch gần đây</div>
                <div id="wallet-history">
                    <div class="empty-state">
                        <div class="empty-state-text">Chưa có giao dịch</div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Admin Page -->
        <div id="page-admin" class="page hidden">
            <div class="glass-card">
                <div class="card-title">📊 Thống kê hệ thống</div>
                <div class="admin-grid">
                    <div class="admin-stat">
                        <div class="admin-value" id="stat-users">0</div>
                        <div class="admin-label">Tổng Users</div>
                    </div>
                    <div class="admin-stat">
                        <div class="admin-value" id="stat-orders">0</div>
                        <div class="admin-label">Tổng Đơn</div>
                    </div>
                    <div class="admin-stat">
                        <div class="admin-value" id="stat-pending">0</div>
                        <div class="admin-label">Đang chờ</div>
                    </div>
                    <div class="admin-stat">
                        <div class="admin-value" id="stat-today">0</div>
                        <div class="admin-label">Hôm nay</div>
                    </div>
                </div>
            </div>
            
            <div class="glass-card">
                <div class="card-title">➕ Thêm số BS (Basha)</div>
                <input type="text" class="input-field" id="bs-phone" placeholder="Số điện thoại (VD: 84912345678)">
                <button class="btn-primary" onclick="addBSNumber()">Thêm số</button>
            </div>
            
            <div class="glass-card">
                <div class="card-title">💸 Yêu cầu rút tiền</div>
                <div id="withdraw-requests">
                    <div class="empty-state">
                        <div class="empty-state-text">Không có yêu cầu nào</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Bottom Nav -->
    <div class="bottom-nav">
        <button class="nav-btn active" onclick="showPage('home')">
            <span class="nav-icon">🏠</span>
            <span>Trang chủ</span>
        </button>
        <button class="nav-btn" onclick="showPage('buy')">
            <span class="nav-icon">🛒</span>
            <span>Mua số</span>
        </button>
        <button class="nav-btn" onclick="showPage('history')">
            <span class="nav-icon">📜</span>
            <span>Lịch sử</span>
        </button>
        <button class="nav-btn" onclick="showPage('wallet')">
            <span class="nav-icon">💰</span>
            <span>Ví</span>
        </button>
    </div>
    
    <script>
        const USER_ID = "{user_id}";
        const IS_ADMIN = USER_ID === "{ADMIN_ID}";
        let currentPage = 'home';
        let refreshInterval = null;
        
        // Init
        if (IS_ADMIN) {{
            document.getElementById('admin-nav').classList.remove('hidden');
        }}
        
        // Navigation
        function toggleSidebar() {{
            document.getElementById('sidebar').classList.toggle('open');
            document.getElementById('sidebar-overlay').classList.toggle('active');
        }}
        
        function showPage(page) {{
            document.querySelectorAll('.page').forEach(p => p.classList.add('hidden'));
            document.getElementById('page-' + page).classList.remove('hidden');
            document.getElementById('page-' + page).classList.add('fade-in');
            
            document.querySelectorAll('.nav-btn').forEach((btn, idx) => {{
                btn.classList.toggle('active', 
                    (page === 'home' && idx === 0) ||
                    (page === 'buy' && idx === 1) ||
                    (page === 'history' && idx === 2) ||
                    (page === 'wallet' && idx === 3)
                );
            }});
            
            currentPage = page;
            
            if (page !== 'home' && refreshInterval) {{
                clearInterval(refreshInterval);
                refreshInterval = null;
            }}
            
            if (page === 'home') {{
                loadHome();
                refreshInterval = setInterval(loadPendingOrders, 5000);
            }} else if (page === 'buy') {{
                loadCountries();
            }} else if (page === 'history') {{
                loadHistory();
            }} else if (page === 'wallet') {{
                loadWallet();
            }} else if (page === 'admin' && IS_ADMIN) {{
                loadAdminStats();
                loadWithdrawRequests();
            }}
        }}
        
        // API
        async function apiCall(action, data = {{}}) {{
            try {{
                const response = await fetch('/api/' + action, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ user_id: USER_ID, ...data }})
                }});
                return await response.json();
            }} catch (e) {{
                console.error('API Error:', e);
                return {{ success: false, error: e.message }};
            }}
        }}
        
        // Home
        async function loadHome() {{
            const result = await apiCall('user_info');
            if (result.success) {{
                document.getElementById('user-balance').textContent = result.balance_milli;
                document.getElementById('header-balance').textContent = result.balance_milli + ' Ⓜ';
                document.getElementById('user-orders').textContent = result.today_orders;
            }}
            loadPendingOrders();
        }}
        
        async function loadPendingOrders() {{
            const result = await apiCall('pending_orders');
            const container = document.getElementById('pending-orders');
            
            if (!result.orders || result.orders.length === 0) {{
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">📭</div>
                        <div class="empty-state-text">Không có đơn nào đang chờ</div>
                    </div>
                `;
                return;
            }}
            
            container.innerHTML = result.orders.map(order => {{
                const hasOtp = order.otp_code && order.otp_code !== 'null';
                return `
                    <div class="order-card ${{hasOtp ? 'has-otp' : ''}}">
                        <div class="phone-number">${{order.phone_number}}</div>
                        <div class="order-meta">
                            <span class="flag">${{order.flag || '🏳️'}}</span>
                            <span>${{order.country_name}}</span>
                            <span class="status-badge status-pending">${{order.status}}</span>
                        </div>
                        <div class="flex gap-2">
                            <button class="copy-btn" onclick="copyText('${{order.phone_number}}', this)">📋 Copy Số</button>
                            ${{hasOtp ? `<button class="copy-btn" onclick="copyText('${{order.otp_code}}', this)">🔢 Copy OTP</button>` : ''}}
                        </div>
                        ${{hasOtp ? `
                            <div class="otp-label">MÃ OTP CỦA BẠN</div>
                            <div class="otp-display">${{order.otp_code}}</div>
                        ` : ''}}
                    </div>
                `;
            }}).join('');
        }}
        
        // Countries
        async function loadCountries() {{
            const result = await apiCall('countries');
            const container = document.getElementById('country-list');
            
            if (result.countries) {{
                container.innerHTML = result.countries.map(c => `
                    <div class="country-item" onclick="selectCountry('${{c.code}}', '${{c.name}}')">
                        <span style="font-size: 28px;">${{c.flag}}</span>
                        <div class="country-info">
                            <div class="country-name">${{c.name}}</div>
                            <div class="country-code-small">+${{c.code}}</div>
                        </div>
                        <span style="color: var(--primary); font-size: 20px;">›</span>
                    </div>
                `).join('');
            }}
        }}
        
        function selectCountry(code, name) {{
            alert('Chọn dịch vụ cho ' + name + ' (Tính năng đang phát triển)');
        }}
        
        // History
        async function loadHistory() {{
            const result = await apiCall('order_history');
            const container = document.getElementById('history-list');
            
            if (!result.orders || result.orders.length === 0) {{
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">📭</div>
                        <div class="empty-state-text">Chưa có đơn hàng nào</div>
                    </div>
                `;
                return;
            }}
            
            container.innerHTML = result.orders.map(order => {{
                const date = new Date(order.created_at).toLocaleString('vi-VN');
                const statusClass = order.status === 'completed' ? 'status-success' : 
                                   order.status === 'cancelled' ? 'status-cancelled' : 'status-pending';
                return `
                    <div class="history-item">
                        <div class="history-header">
                            <span class="status-badge ${{statusClass}}">${{order.status.toUpperCase()}}</span>
                            <span class="history-date">${{date}}</span>
                        </div>
                        <div class="history-body">
                            <div class="history-icon">📱</div>
                            <div class="history-details">
                                <div class="history-phone">${{order.phone_number || 'N/A'}}</div>
                                <div class="history-meta">
                                    ${{order.country_name}} ${{order.flag}} • Nguồn: ${{order.source.toUpperCase()}}
                                </div>
                            </div>
                        </div>
                        ${{order.otp_code && order.otp_code !== 'null' ? `
                            <div class="history-otp">
                                <span class="history-meta">OTP:</span>
                                <span class="otp-code">${{order.otp_code}}</span>
                                <button class="copy-btn" style="padding: 8px 16px;" onclick="copyText('${{order.otp_code}}', this)">Copy</button>
                            </div>
                        ` : ''}}
                    </div>
                `;
            }}).join('');
        }}
        
        // Wallet
        async function loadWallet() {{
            const result = await apiCall('user_info');
            if (result.success) {{
                document.getElementById('wallet-balance').textContent = result.balance_milli + ' Ⓜ';
            }}
        }}
        
        function showWithdrawModal() {{
            const addr = prompt('Nhập địa chỉ TON để rút tiền:');
            if (addr && addr.length > 10) {{
                apiCall('withdraw', {{ ton_address: addr }}).then(r => {{
                    if (r.success) alert('✅ Yêu cầu rút tiền đã được gửi!');
                    else alert('❌ Lỗi: ' + (r.error || 'Unknown'));
                }});
            }}
        }}
        
        // Admin
        async function loadAdminStats() {{
            const result = await apiCall('admin_stats');
            if (result.success) {{
                document.getElementById('stat-users').textContent = result.users || 0;
                document.getElementById('stat-orders').textContent = result.orders || 0;
                document.getElementById('stat-pending').textContent = result.pending || 0;
                document.getElementById('stat-today').textContent = result.today || 0;
            }}
        }}
        
        async function loadWithdrawRequests() {{
            const result = await apiCall('withdraw_requests');
            const container = document.getElementById('withdraw-requests');
            
            if (!result.requests || result.requests.length === 0) {{
                container.innerHTML = '<div class="empty-state"><div class="empty-state-text">Không có yêu cầu nào</div></div>';
                return;
            }}
            
            container.innerHTML = result.requests.map(req => `
                <div class="withdraw-card">
                    <div class="withdraw-info">
                        <div class="withdraw-row">
                            <span class="withdraw-label">User ID</span>
                            <span class="withdraw-value">${{req.user_id}}</span>
                        </div>
                        <div class="withdraw-row">
                            <span class="withdraw-label">Số tiền</span>
                            <span class="withdraw-value" style="color: var(--success);">${{req.amount_milli}} Ⓜ</span>
                        </div>
                        <div class="withdraw-row">
                            <span class="withdraw-label">Địa chỉ TON</span>
                            <span class="withdraw-value" style="font-size: 12px; font-family: monospace;">${{req.ton_address.substring(0, 20)}}...</span>
                        </div>
                    </div>
                    <div class="withdraw-actions">
                        <button class="btn-approve" onclick="processWithdraw(${{req.id}}, 'approve')">✅ Duyệt</button>
                        <button class="btn-reject" onclick="processWithdraw(${{req.id}}, 'reject')">❌ Từ chối</button>
                    </div>
                </div>
            `).join('');
        }}
        
        async function processWithdraw(id, action) {{
            await apiCall('process_withdraw', {{ request_id: id, action: action }});
            loadWithdrawRequests();
        }}
        
        async function addBSNumber() {{
            const phone = document.getElementById('bs-phone').value.trim();
            if (!phone) return alert('Vui lòng nhập số điện thoại');
            
            const result = await apiCall('add_bs_number', {{ phone_number: phone }});
            if (result.success) {{
                alert('✅ Đã thêm số BS thành công!');
                document.getElementById('bs-phone').value = '';
            }} else {{
                alert('❌ Lỗi: ' + (result.error || 'Unknown'));
            }}
        }}
        
        // Utils
        function copyText(text, btn) {{
            navigator.clipboard.writeText(text).then(() => {{
                const original = btn.innerHTML;
                btn.innerHTML = '✅ Đã copy';
                btn.classList.add('copied');
                setTimeout(() => {{
                    btn.innerHTML = original;
                    btn.classList.remove('copied');
                }}, 2000);
            }});
        }}
        
        // Init
        showPage('home');
    </script>
</body>
</html>'''
    return web.Response(text=html_content, content_type='text/html')

# API Routes
async def api_user_info(request):
    data = await request.json()
    user_id = data.get('user_id')
    
    user = await db_query(
        "SELECT balance_milli, total_spent_milli, total_earned_milli FROM users WHERE user_id = ?", 
        (user_id,), fetchone=True
    )
    
    if not user:
        return web.json_response({"success": False, "error": "User not found"})
    
    today = datetime.now(VN_TZ).strftime('%Y-%m-%d')
    today_orders = await db_query(
        "SELECT COUNT(*) FROM orders WHERE user_id = ? AND DATE(created_at) = ?", 
        (user_id, today), fetchone=True
    )
    
    return web.json_response({
        "success": True,
        "balance_milli": user[0],
        "total_spent": user[1],
        "total_earned": user[2],
        "today_orders": today_orders[0] if today_orders else 0
    })

async def api_pending_orders(request):
    data = await request.json()
    user_id = data.get('user_id')
    
    orders = await db_query(
        """SELECT order_id, phone_number, country_name, country_code, service_name, 
           status, otp_code, created_at, source 
           FROM orders 
           WHERE user_id = ? AND status IN ('pending', 'active') 
           ORDER BY created_at DESC""",
        (user_id,)
    )
    
    result = []
    for row in orders:
        result.append({
            "order_id": row[0],
            "phone_number": row[1] or "N/A",
            "country_name": row[2] or "Unknown",
            "country_code": row[3] or "",
            "service_name": row[4] or "N/A",
            "status": row[5] or "pending",
            "otp_code": row[6],
            "created_at": row[7],
            "source": row[8] or "N/A",
            "flag": get_flag_emoji(row[3])
        })
    
    return web.json_response({"success": True, "orders": result})

async def api_countries(request):
    countries = []
    for code, (name, flag) in COUNTRY_CODES.items():
        countries.append({
            "code": code,
            "name": name,
            "flag": flag
        })
    return web.json_response({"success": True, "countries": countries})

async def api_order_history(request):
    data = await request.json()
    user_id = data.get('user_id')
    
    orders = await db_query(
        """SELECT order_id, phone_number, country_name, country_code, service_name,
           status, otp_code, created_at, source 
           FROM orders 
           WHERE user_id = ? 
           ORDER BY created_at DESC 
           LIMIT ?""",
        (user_id, MAX_HISTORY_RECORDS)
    )
    
    result = []
    for row in orders:
        result.append({
            "order_id": row[0],
            "phone_number": row[1] or "N/A",
            "country_name": row[2] or "Unknown",
            "country_code": row[3] or "",
            "service_name": row[4] or "N/A",
            "status": row[5] or "unknown",
            "otp_code": row[6],
            "created_at": row[7],
            "source": row[8] or "N/A",
            "flag": get_flag_emoji(row[3]) if row[3] else "🏳️"
        })
    
    return web.json_response({"success": True, "orders": result})

async def api_withdraw(request):
    data = await request.json()
    user_id = int(data.get('user_id'))
    ton_address = data.get('ton_address')
    
    user = await db_query("SELECT balance_milli FROM users WHERE user_id = ?", (user_id,), fetchone=True)
    if not user or user[0] < MIN_WITHDRAW_MILLI:
        return web.json_response({"success": False, "error": f"Minimum withdraw is {MIN_WITHDRAW_MILLI} milli"})
    
    await db_execute(
        "INSERT INTO withdrawals (user_id, amount_milli, ton_address, status, requested_at) VALUES (?, ?, ?, 'pending', ?)",
        (user_id, user[0], ton_address, datetime.now(VN_TZ).isoformat())
    )
    
    await db_execute("UPDATE users SET balance_milli = 0 WHERE user_id = ?", (user_id,))
    return web.json_response({"success": True})

async def api_admin_stats(request):
    data = await request.json()
    user_id = int(data.get('user_id'))
    
    if user_id != ADMIN_ID:
        return web.json_response({"success": False, "error": "Unauthorized"})
    
    users = await db_query("SELECT COUNT(*) FROM users", fetchone=True)
    orders = await db_query("SELECT COUNT(*) FROM orders", fetchone=True)
    pending = await db_query("SELECT COUNT(*) FROM orders WHERE status = 'pending'", fetchone=True)
    today = datetime.now(VN_TZ).strftime('%Y-%m-%d')
    today_orders = await db_query("SELECT COUNT(*) FROM orders WHERE DATE(created_at) = ?", (today,), fetchone=True)
    
    return web.json_response({
        "success": True,
        "users": users[0] if users else 0,
        "orders": orders[0] if orders else 0,
        "pending": pending[0] if pending else 0,
        "today": today_orders[0] if today_orders else 0
    })

async def api_withdraw_requests(request):
    data = await request.json()
    user_id = int(data.get('user_id'))
    
    if user_id != ADMIN_ID:
        return web.json_response({"success": False, "error": "Unauthorized"})
    
    requests = await db_query("SELECT * FROM withdrawals WHERE status = 'pending' ORDER BY requested_at DESC")
    result = []
    for row in requests:
        result.append({
            "id": row[0],
            "user_id": row[1],
            "amount_milli": row[2],
            "ton_address": row[3],
            "requested_at": row[5]
        })
    return web.json_response({"success": True, "requests": result})

async def api_process_withdraw(request):
    data = await request.json()
    user_id = int(data.get('user_id'))
    
    if user_id != ADMIN_ID:
        return web.json_response({"success": False, "error": "Unauthorized"})
    
    req_id = data.get('request_id')
    action = data.get('action')
    
    now = datetime.now(VN_TZ).isoformat()
    if action == 'approve':
        await db_execute("UPDATE withdrawals SET status = 'approved', processed_at = ?, processed_by = ? WHERE id = ?", 
                        (now, user_id, req_id))
    else:
        req = await db_query("SELECT user_id, amount_milli FROM withdrawals WHERE id = ?", (req_id,), fetchone=True)
        if req:
            await db_execute("UPDATE users SET balance_milli = balance_milli + ? WHERE user_id = ?", (req[1], req[0]))
            await db_execute("UPDATE withdrawals SET status = 'rejected', processed_at = ?, processed_by = ? WHERE id = ?", 
                            (now, user_id, req_id))
    
    return web.json_response({"success": True})

async def api_add_bs_number(request):
    data = await request.json()
    user_id = int(data.get('user_id'))
    
    if user_id != ADMIN_ID:
        return web.json_response({"success": False, "error": "Unauthorized"})
    
    phone = data.get('phone_number')
    now = datetime.now(VN_TZ).isoformat()
    
    try:
        await db_execute(
            "INSERT INTO admin_numbers (phone_number, source, added_by, added_at) VALUES (?, 'bs', ?, ?)",
            (phone, user_id, now)
        )
        return web.json_response({"success": True})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)})

# Setup Web Server
async def init_web():
    app = web.Application()
    app.router.add_get('/', webapp_handler)
    app.router.add_post('/api/user_info', api_user_info)
    app.router.add_post('/api/pending_orders', api_pending_orders)
    app.router.add_post('/api/countries', api_countries)
    app.router.add_post('/api/order_history', api_order_history)
    app.router.add_post('/api/withdraw', api_withdraw)
    app.router.add_post('/api/admin_stats', api_admin_stats)
    app.router.add_post('/api/withdraw_requests', api_withdraw_requests)
    app.router.add_post('/api/process_withdraw', api_process_withdraw)
    app.router.add_post('/api/add_bs_number', api_add_bs_number)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.getenv('PORT', 8080)))
    await site.start()
    logger.info("Web server started on port %s", os.getenv('PORT', 8080))

# =====================================================
# MAIN
# =====================================================
async def main():
    global BOT_USERNAME
    await init_db()
    me = await bot.get_me()
    BOT_USERNAME = me.username
    
    commands = [
        BotCommand(command="start", description="Mở Mini App"),
        BotCommand(command="help", description="Hướng dẫn sử dụng")
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    
    await init_web()
    asyncio.create_task(otp_poller())
    
    logger.info(f"Bot @{BOT_USERNAME} started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
