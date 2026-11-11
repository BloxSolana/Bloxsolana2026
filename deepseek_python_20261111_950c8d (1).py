import os
import sys
import json
import hashlib
import hmac
import logging
import asyncio
import re
import time
import random
import string
from urllib.parse import parse_qsl
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
from aiohttp import web, ClientSession

from aiogram import Bot, Dispatcher, BaseMiddleware, F
from aiogram.filters import Command, CommandStart
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault, MenuButtonWebApp, WebAppInfo, Message, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from database import (
    init_db, db_exec, get_setting, set_setting, get_user, register_user, now, now_text, 
    is_admin, unix_now, clean_old_orders, open_db, change_usd, safe,
    COUNTRY_CODES, SORTED_PREFIXES, ISO_MAP, FALLBACK_COUNTRIES, get_country_flag, get_network_icon, detect_otp_platform
)
from miniapp_html import MINIAPP_HTML

BOT_TOKEN        = os.getenv("BOT_TOKEN", "").strip()
WEBAPP_URL       = os.getenv("WEBAPP_URL", "").strip()
ADMIN_ID         = int(os.getenv("ADMIN_ID", "0") or 0)
OTP_GROUP_ID     = int(os.getenv("OTP_GROUP_ID", "-1004341368656") or -1004341368656)
PORT             = int(os.getenv("PORT", "10000"))

MK_API_KEY       = os.getenv("MK_API_KEY", "badacaa33d287233567a49db").strip()
MK_API_URL       = "https://mknetworkbd.com/api/v3/public"
NP_API_KEY       = os.getenv("NP_API_KEY", "np_live_lrRtdKcOeg-syi8UCpmaA_idYmBZY0zbpwl5P--gF-g").strip()
NP_API_URL       = "https://numberpanel.tech/api" 
BS_API_KEY       = os.getenv("BS_API_KEY", "bsh_k24s8NA57a0M4A52NwbDmX0hTm1GTlJW").strip()
BS_API_URL       = "https://basha.cc/api"
SLVN_API_KEY     = os.getenv("SLVN_API_KEY", "sl_live_ffd4ae564be89edb2d26d9a06ef2d4ff8a39387cafa00bd2").strip()
SLVN_API_URL     = "https://slvirtualnumber.com/api/v1/developer"

# CẤU HÌNH API AHO (ACCHUB)
AHO_API_KEY      = "91eed28ba2525b208cb868ad81dcbf" # Đã kiểm tra kỹ key
AHO_API_URL      = "https://acchub.io/api/freelancer"

ORDER_LIFETIME_MINUTES = 15
MIN_WITHDRAW_MILLI     = 1000
HISTORY_PAGE_SIZE      = 10

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FAST_IVAS")

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp  = Dispatcher()
BOT_USERNAME = ""
_mk_poller = None

@dp.message(CommandStart())
async def cmd_start(message: Message):
    try: await message.delete()
    except: pass
    try:
        args = message.text.split(maxsplit=1)
        ref = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
        try: await register_user(message.from_user, ref)
        except Exception as e: logger.error(f"Register user error: {e}")

        if await get_setting("maintenance", "off") == "on" and not is_admin(message.from_user.id):
            return await message.answer("🛠 <b>HỆ THỐNG ĐANG BẢO TRÌ</b>\n\nVui lòng quay lại sau.")
        
        if WEBAPP_URL.startswith("https://"):
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚡ MỞ ỨNG DỤNG FAST IVAS", web_app=WebAppInfo(url=WEBAPP_URL + "?v=29"))]])
            await message.answer("🚀 Chào mừng đến với <b>FAST IVAS</b>!\n\nVui lòng bấm nút bên dưới để mở ứng dụng.", reply_markup=kb)
        else:
            await message.answer("⚠️ Lỗi: Chưa cấu hình WEBAPP_URL.")
    except Exception as e:
        logger.error(f"Start command error: {e}")
        try: await message.answer("⚠️ Hệ thống đang bận. Vui lòng thử lại sau giây lát!")
        except: pass

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

@dp.callback_query(F.data.startswith("admin_bonus_"))
async def handle_admin_bonus_click(callback: CallbackQuery):
    try:
        data = callback.data.split("_")
        action, amt, target_uid = data[2], int(data[3]), int(data[4])
        uid = callback.from_user.id

        if action == "accept":
            ok, msg = await change_usd(uid, amt, "ADMIN_BONUS", "Nhận tiền từ Admin")
            if ok:
                await callback.message.edit_text(f"✅ Bạn đã nhận thành công <b>${amt/1000:.3f}</b> từ Admin!")
                await callback.answer("Đã cộng tiền vào tài khoản!", show_alert=True)
            else: await callback.answer(f"Lỗi: {msg}", show_alert=True)
        elif action == "reject":
            await callback.message.edit_text("❌ Bạn đã từ chối nhận tiền từ Admin.")
            await callback.answer("Đã hủy nhận tiền.", show_alert=False)
    except Exception as e:
        logger.error(f"Bonus click error: {e}")
        await callback.answer("Có lỗi xảy ra, vui lòng thử lại sau.", show_alert=True)

async def api_request(method, endpoint, json_data=None, params=None, api_type="MK"):
    url, headers = "", {"Accept": "application/json"}
    if api_type == "MK":
        url, headers["mknetwork-key"] = f"{MK_API_URL}/{endpoint.lstrip('/')}", MK_API_KEY
    elif api_type == "NP":
        url, headers["Authorization"] = f"{NP_API_URL}/{endpoint.lstrip('/')}", f"Bearer {NP_API_KEY}"
    elif api_type == "BS":
        url, headers["Authorization"] = f"{BS_API_URL}/{endpoint.lstrip('/')}", f"Bearer {BS_API_KEY}"
    elif api_type == "SLVN":
        url, headers["x-api-key"] = f"{SLVN_API_URL}/{endpoint.lstrip('/')}", SLVN_API_KEY
    elif api_type == "AHO":
        url = f"{AHO_API_URL}/{endpoint.lstrip('/')}"
        # AHO thường yêu cầu thêm User-Agent để không bị chặn
        headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        
    if json_data is not None: headers["Content-Type"] = "application/json"
    async with ClientSession() as session:
        try:
            async with session.request(method, url, json=json_data, params=params, headers=headers, timeout=20) as resp:
                text = await resp.text()
                try: data = await resp.json()
                except: data = {"raw": text}
                if resp.status >= 400: return None, f"HTTP {resp.status}: {text}"
                return data, None
        except Exception as e: return None, str(e)

class MkOtpPoller:
    def __init__(self, bot_instance, group_id, interval=3):
        self.bot = bot_instance
        self.group_id = int(group_id) if group_id else 0
        self.interval = interval
        self.is_running = False

    async def run_forever(self):
        self.is_running = True
        while self.is_running:
            try: await self._poll_once()
            except Exception as e: logger.error(f"Poller error: {e}")
            await asyncio.sleep(self.interval)

    async def _poll_once(self):
        try:
            # 1. Poll MK
            pending_mk = await db_exec("SELECT id, user_id, provider, request_id, phone, country FROM orders WHERE status='PENDING' AND provider='MK'", fetch="all")
            if pending_mk:
                request_ids_map = {int(o["request_id"]): o for o in pending_mk if str(o["request_id"]).isdigit()}
                if request_ids_map:
                    req_ids_list = list(request_ids_map.keys())
                    data, err = await api_request("POST", "check/status", {"request_ids": req_ids_list}, api_type="MK")
                    if not err and data:
                        results = data.get("data", {}).get("results", [])
                        for res in results:
                            rid = res.get("request_id")
                            if rid in request_ids_map:
                                order = request_ids_map[rid]
                                otp_code, full_sms = res.get("otp_code"), res.get("full_sms", "")
                                if otp_code: await self._process_otp(order, otp_code, full_sms)

            # 2. Poll SLVN
            pending_slvn = await db_exec("SELECT id, user_id, provider, request_id, phone, country FROM orders WHERE status='PENDING' AND provider='SLVN'", fetch="all")
            for order in (pending_slvn or []):
                rid = order["request_id"]
                data, err = await api_request("GET", f"check-otp/{rid}", api_type="SLVN")
                if not err and data and data.get("status") == "success":
                    inner = data.get("data", {})
                    if inner.get("status") == "RECEIVED":
                        otp_code, full_sms = inner.get("otpCode"), inner.get("fullSms", "")
                        if otp_code: await self._process_otp(order, otp_code, full_sms)

            # 3. Poll NP
            pending_np = await db_exec("SELECT id, user_id, provider, request_id, phone, country FROM orders WHERE status='PENDING' AND provider='NP'", fetch="all")
            for order in (pending_np or []):
                data, err = await api_request("GET", "latest_otp", params={"number": order["phone"]}, api_type="NP")
                if not err and data and data.get("has_otp"):
                    otp_code = data.get("otp_code")
                    if otp_code: await self._process_otp(order, otp_code, f"OTP: {otp_code}")

            # 4. Poll BS
            pending_bs = await db_exec("SELECT id, user_id, provider, request_id, phone, country FROM orders WHERE status='PENDING' AND provider='BS'", fetch="all")
            for order in (pending_bs or []):
                data, err = await api_request("POST", "legacy/get-last-sms", {"number": order["phone"]}, api_type="BS")
                if not err and data and data.get("message"):
                    otp_match = re.search(r'\b(\d{4,8})\b', data["message"])
                    if otp_match: await self._process_otp(order, otp_match.group(1), data["message"])

            # 5. Poll AHO
            pending_aho = await db_exec("SELECT id, user_id, provider, request_id, phone, country FROM orders WHERE status='PENDING' AND provider='AHO'", fetch="all")
            for order in (pending_aho or []):
                data, err = await api_request("GET", f"otp/get-otp/{AHO_API_KEY}/{order['phone']}", api_type="AHO")
                if not err and isinstance(data, list) and len(data) > 0:
                    latest = data[0]
                    otp_code, sms_text = latest.get("otp_code"), latest.get("sms_text")
                    if otp_code: await self._process_otp(order, otp_code, sms_text)

            return 0, 0, None
        except Exception as e:
            logger.error(f"Poller internal error: {e}")
            return 0, 0, str(e)

    async def _process_otp(self, order, otp_code, full_sms):
        plat = detect_otp_platform(full_sms)
        icon = get_network_icon(plat)
        flag = get_country_flag(order["country"])

        await db_exec("UPDATE orders SET status='COMPLETED', otp_code=?, full_sms=?, platform=?, updated_at=? WHERE id=?", 
                      (str(otp_code), str(full_sms), plat, now_text(), order["id"]))

        if order["provider"] in ["MK", "SLVN", "FAST_IVAS", "AHO"]:
            try: await change_usd(order["user_id"], 2, "OTP_REWARD", f"Reward {order['provider']} OTP")
            except Exception as e: logger.error(f"[REWARD ERROR] {e}")

        if self.group_id != 0:
            group_text = (
                f"⚡ <b>FAST IVAS - REAL-TIME OTP</b> ⚡\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"📱 <b>Số:</b> <code>{order['phone']}</code>\n"
                f"{flag} <b>Quốc gia:</b> {order['country']}\n"
                f"{icon} <b>Nền tảng:</b> {plat}\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔑 <b>Mã OTP:</b> <code><b>{otp_code}</b></code>\n"
                f"💬 <b>Nội dung:</b> <i>{safe(full_sms, 200)}</i>\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"⏰ <b>Thời gian:</b> {now().strftime('%H:%M:%S %d/%m/%Y')}"
            )
            try: await self.bot.send_message(self.group_id, group_text)
            except Exception as e: logger.error(f"[GROUP ERROR] {e}")

        try:
            user_text = (
                f"🎉 <b>ĐÃ NHẬN ĐƯỢC MÃ OTP!</b>\n\n"
                f"📱 Số: <code>{order['phone']}</code>\n"
                f"{icon} Nền tảng: <b>{plat}</b>\n"
                f"🔑 Mã OTP: <code><b>{otp_code}</b></code>\n"
                f"💬 Nội dung: <i>{full_sms}</i>"
            )
            await self.bot.send_message(order["user_id"], user_text)
        except Exception as e: pass

async def auto_expire_orders():
    while True:
        try:
            now_str = now().isoformat()
            await db_exec("UPDATE orders SET status='EXPIRED', updated_at=? WHERE status='PENDING' AND expires_at < ?", (now_text(), now_str))
        except Exception as e: pass
        await asyncio.sleep(60)

class ErrorMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        try: return await handler(event, data)
        except Exception as e:
            logger.error(f"Handler error: {e}")
            try:
                if isinstance(event, Message): await event.answer("⚠️ <b>Hệ thống đang bận. Vui lòng thử lại sau!</b>")
            except: pass

dp.message.middleware(ErrorMiddleware())
dp.callback_query.middleware(ErrorMiddleware())

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
    try:
        if request.path.startswith("/api/mini/"):
            tg_user = validate_telegram_init_data(request.headers.get("X-Telegram-Init-Data", ""))
            if not tg_user: return web.json_response({"error": "Phiên làm việc không hợp lệ"}, status=401)
            request["tg_user"] = tg_user
            await register_user(SimpleNamespace(id=int(tg_user["id"]), username=tg_user.get("username"), first_name=tg_user.get("first_name") or "User"))
        return await handler(request)
    except Exception as e:
        logger.error(f"Auth middleware error: {e}")
        return web.json_response({"error": "Lỗi xác thực hệ thống"}, status=500)

def mini_uid(request): return int(request["tg_user"]["id"])
def mini_admin_guard(request): return is_admin(mini_uid(request))

async def mini_me(request):
    try:
        uid = mini_uid(request)
        u = await get_user(uid)
        total = await db_exec("SELECT COUNT(*) as c FROM orders WHERE user_id=?", (uid,), fetch="one")
        today = await db_exec("SELECT COUNT(*) as c FROM orders WHERE user_id=? AND status='COMPLETED' AND created_at >= ?", (uid, now().strftime("%Y-%m-%d")), fetch="one")
        total_otps = await db_exec("SELECT COUNT(*) as c FROM orders WHERE user_id=? AND status='COMPLETED'", (uid,), fetch="one")
        
        return web.json_response({
            "user": {"id": u['user_id'], "first_name": u['first_name'], "usd_milli": u['usd_milli'], "wallet_ton": u['wallet_ton'] or "", "joined_at": u['joined_at'], "language": u.get('language', 'vi')}, 
            "total_orders": total["c"] if total else 0, 
            "today_otps": today["c"] if today else 0,
            "total_otps": total_otps["c"] if total_otps else 0,
            "is_admin": is_admin(uid), 
            "referral_link": f"https://t.me/{BOT_USERNAME}?start={uid}",
            "maintenance": await get_setting("maintenance", "off"),
            "maint_message": await get_setting("maint_message", ""),
            "maint_image": await get_setting("maint_image", "")
        })
    except Exception as e: return web.json_response({"error": "Lỗi tải thông tin"}, status=500)

async def mini_language_update(request):
    try:
        uid = mini_uid(request); body = await request.json()
        await db_exec("UPDATE users SET language=? WHERE user_id=?", (body.get("language", "vi"), uid))
        return web.json_response({"ok": True})
    except: return web.json_response({"error": "Lỗi"}, status=500)

async def mini_stats(request):
    try:
        today_str = now().strftime("%Y-%m-%d")
        today_res = await db_exec("SELECT COUNT(*) as c FROM orders WHERE status='COMPLETED' AND created_at >= ?", (today_str,), fetch='one')
        today_otps = today_res['c'] if today_res else 0
        
        total_res = await db_exec("SELECT COUNT(*) as c FROM orders WHERE status='COMPLETED'", fetch='one')
        total_all_otps = total_res['c'] if total_res else 0
        
        countries = await db_exec("SELECT country, COUNT(id) as c FROM orders WHERE status='COMPLETED' AND created_at >= ? GROUP BY country ORDER BY c DESC", (today_str,), fetch='all')
        platforms = await db_exec("SELECT COALESCE(NULLIF(platform, ''), 'Other') as p, COUNT(id) as c FROM orders WHERE status='COMPLETED' AND created_at >= ? GROUP BY p ORDER BY c DESC", (today_str,), fetch='all')

        return web.json_response({
            "today_otps": today_otps,
            "total_all_otps": total_all_otps,
            "countries": [{"country": r['country'], "count": r['c'], "flag": get_country_flag(r['country'])} for r in (countries or [])],
            "platforms": [{"platform": r['p'], "count": r['c'], "icon": get_network_icon(r['p'])} for r in (platforms or [])]
        })
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

async def mini_radar_feed(request):
    formatted_items, platform_counts, country_counts = [], {}, {}
    current_unix = int(time.time())
    try:
        data, err = await api_request("GET", "radar", params={"charts": "true", "limit": 100}, api_type="MK")
        if not err and data:
            resp_data = data.get("data", {})
            charts = resp_data.get("charts", {})
            for p in charts.get("platforms", []): platform_counts[detect_otp_platform(p.get("name", "Other"))] = platform_counts.get(detect_otp_platform(p.get("name", "Other")), 0) + p.get("count", 0)
            for c in charts.get("countries", []): country_counts[c.get("name", "Unknown")] = country_counts.get(c.get("name", "Unknown"), 0) + c.get("count", 0)
            
            items = resp_data.get("feed") or resp_data.get("items") or []
            if isinstance(items, list):
                for idx, item in enumerate(items):
                    plat = detect_otp_platform(item.get("platform") or item.get("service") or item.get("message") or "Other")
                    country = item.get("country") or item.get("country_name") or "Vietnam"
                    if not charts:
                        platform_counts[plat] = platform_counts.get(plat, 0) + 1
                        country_counts[country] = country_counts.get(country, 0) + 1
                    
                    time_str = item.get("time")
                    if time_str:
                        try: timestamp = int(datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())
                        except: timestamp = current_unix - (idx * 5)
                    else: timestamp = current_unix - (idx * 5)

                    formatted_items.append({
                        "phone": item.get("number") or item.get("phone") or "N/A",
                        "country": country, "flag": get_country_flag(country),
                        "operator": item.get("operator") or item.get("network") or "Network",
                        "message": item.get("otp") or item.get("message") or item.get("sms") or "OTP Code received",
                        "timestamp": timestamp, "platform": plat
                    })
    except Exception as e: pass

    try:
        cutoff_time = (now() - timedelta(minutes=30)).isoformat()
        local_orders = await db_exec("SELECT phone, country, operator, full_sms, platform, updated_at, created_at FROM orders WHERE status='COMPLETED' AND (updated_at >= ? OR created_at >= ?) ORDER BY id DESC LIMIT 50", (cutoff_time, cutoff_time), fetch="all")
        for r in (local_orders or []):
            plat = r["platform"] or detect_otp_platform(r["full_sms"])
            if not platform_counts.get(plat): platform_counts[plat] = 1
            country = r["country"] or "Vietnam"
            t_str = r["updated_at"] or r["created_at"]
            try: timestamp = int(datetime.fromisoformat(t_str).timestamp())
            except: timestamp = current_unix
            formatted_items.append({"phone": r["phone"] or "N/A", "country": country, "flag": get_country_flag(country), "operator": r["operator"] or "Network", "message": r["full_sms"] or "OTP Received successfully", "timestamp": timestamp, "platform": plat})
    except Exception as e: pass

    formatted_items.sort(key=lambda x: x["timestamp"], reverse=True)
    platforms = [{"name": k, "count": v, "icon": get_network_icon(k)} for k, v in sorted(platform_counts.items(), key=lambda x: x[1], reverse=True) if v > 0]
    countries = [{"name": k, "count": v, "flag": get_country_flag(k)} for k, v in sorted(country_counts.items(), key=lambda x: x[1], reverse=True)]
    return web.json_response({"items": formatted_items[:100], "platforms": platforms, "countries": countries, "total_records": len(formatted_items)})

async def mini_leaderboard(request):
    try:
        top_users = await db_exec("SELECT u.user_id, u.first_name, u.usd_milli, (SELECT COUNT(*) FROM orders WHERE user_id = u.user_id AND status = 'COMPLETED') as total_otps FROM users u ORDER BY total_otps DESC, u.usd_milli DESC LIMIT 10", fetch="all")
        today_str = now().strftime("%Y-%m-%d")
        today_top = await db_exec("SELECT u.user_id, u.first_name, COUNT(o.id) as today_otps FROM users u JOIN orders o ON u.user_id = o.user_id WHERE o.status = 'COMPLETED' AND o.created_at >= ? GROUP BY u.user_id ORDER BY today_otps DESC LIMIT 10", (today_str,), fetch="all")
        return web.json_response({
            "leaderboard": [{"name": u["first_name"], "balance": u["usd_milli"], "total_otps": u["total_otps"]} for u in top_users] if top_users else [],
            "today_leaderboard": [{"name": u["first_name"], "today_otps": u["today_otps"]} for u in today_top] if today_top else []
        })
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

async def mini_active_orders(request):
    try:
        uid = mini_uid(request)
        cutoff = (now() - timedelta(minutes=30)).isoformat()
        rows = await db_exec("SELECT id, provider, phone, country, status, created_at, expires_at, otp_code, platform, full_sms FROM orders WHERE user_id=? AND (status='PENDING' OR (status='COMPLETED' AND (updated_at >= ? OR created_at >= ?))) ORDER BY id DESC", (uid, cutoff, cutoff), fetch="all")
        orders = []
        for r in (rows or []):
            plat = r["platform"] or detect_otp_platform(r["full_sms"])
            exp_at = r["expires_at"]
            if not exp_at and r["status"] == "PENDING":
                try:
                    c_dt = datetime.fromisoformat(r["created_at"])
                    duration = 30 if r["provider"] == "SLVN" else 15
                    exp_at = (c_dt + timedelta(minutes=duration)).isoformat()
                except: exp_at = (now() + timedelta(minutes=15)).isoformat()

            orders.append({
                "id": r["id"], "provider": r["provider"], "phone": r["phone"], "country": r["country"], 
                "status": r["status"], "created_at": r["created_at"], "expires_at": exp_at,
                "otp": r["otp_code"], "platform": plat, "icon": get_network_icon(plat), "flag": get_country_flag(r["country"]), "full_sms": r["full_sms"]
            })
        return web.json_response({"orders": orders})
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

async def mini_history_orders(request):
    try:
        uid = mini_uid(request)
        try: page = int(request.query.get("page", "1"))
        except: page = 1
        if page < 1: page = 1
        offset = (page - 1) * HISTORY_PAGE_SIZE
        total_res = await db_exec("SELECT COUNT(*) as c FROM orders WHERE user_id=?", (uid,), fetch="one")
        total = total_res["c"] if total_res else 0
        total_pages = max(1, (total + HISTORY_PAGE_SIZE - 1) // HISTORY_PAGE_SIZE)
        if page > total_pages: page = total_pages
        
        rows = await db_exec("SELECT id, provider, phone, country, status, created_at, expires_at, otp_code, platform, full_sms FROM orders WHERE user_id=? ORDER BY id DESC LIMIT ? OFFSET ?", (uid, HISTORY_PAGE_SIZE, offset), fetch="all")
        orders = []
        for r in (rows or []):
            plat = r["platform"] or detect_otp_platform(r["full_sms"])
            orders.append({
                "id": r["id"], "provider": r["provider"], "phone": r["phone"], "country": r["country"], 
                "status": r["status"], "created_at": r["created_at"], "expires_at": r["expires_at"], 
                "otp": r["otp_code"], "platform": plat, "icon": get_network_icon(plat), "flag": get_country_flag(r["country"])
            })
        return web.json_response({"orders": orders, "current_page": page, "total_pages": total_pages, "total_records": total})
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

async def mini_clear_history(request):
    try:
        uid = mini_uid(request)
        await db_exec("DELETE FROM orders WHERE user_id=? AND status IN ('COMPLETED', 'CANCELLED', 'EXPIRED')", (uid,))
        return web.json_response({"ok": True})
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

async def mini_create_order(request):
    try:
        if await get_setting("maintenance", "off") == "on": return web.json_response({"error": "Hệ thống đang bảo trì."}, status=403)
        uid = mini_uid(request); body = await request.json()
        provider = body.get("provider")
        
        if provider == "MK":
            range_val = body.get("range")
            if not range_val: return web.json_response({"error": "Lỗi MK: Range không hợp lệ."}, status=400)
            data, err = await api_request("POST", "getnum/number", {"range": str(range_val).strip()}, api_type="MK")
            if err: return web.json_response({"error": f"Lỗi MK: {err}"}, status=400)
            inner_data = data.get("data", {})
            rid, phone, country = inner_data.get("request_id"), inner_data.get("number") or inner_data.get("full_number") or "N/A", inner_data.get("country") or body.get("country_name") or "Unknown"
            if not rid: return web.json_response({"error": "Lỗi MK: API không trả về ID."}, status=400)
            await db_exec("INSERT INTO orders (user_id, request_id, provider, phone, country, range_code, status, created_at, expires_at) VALUES (?, ?, 'MK', ?, ?, ?, 'PENDING', ?, ?)", (uid, str(rid), str(phone), country, str(range_val), now_text(), (now() + timedelta(minutes=15)).isoformat()))
            await clean_old_orders(uid)
            return web.json_response({"ok": True})

        elif provider == "SLVN":
            payload = {"service": "ANY", "countryCode": body.get("country_code"), "tag": body.get("tag")}
            data, err = await api_request("POST", "rent", payload, api_type="SLVN")
            if err: return web.json_response({"error": f"Lỗi SLVN: {err}"}, status=400)
            order_data = data.get("data", {})
            rid, phone, country = order_data.get("rentalId"), order_data.get("phoneNumber"), order_data.get("country")
            if not rid: return web.json_response({"error": "Lỗi SLVN: Không lấy được rentalId."}, status=400)
            await db_exec("INSERT INTO orders (user_id, request_id, provider, phone, country, range_code, status, created_at, expires_at) VALUES (?, ?, 'SLVN', ?, ?, ?, 'PENDING', ?, ?)", (uid, rid, phone, country, body.get("tag"), now_text(), (now() + timedelta(minutes=30)).isoformat()))
            await clean_old_orders(uid)
            return web.json_response({"ok": True})

        elif provider == "NP":
            data, err = await api_request("POST", "request_number", {"service": body.get("service"), "country": body.get("country")}, api_type="NP")
            if err: return web.json_response({"error": f"Lỗi NP: {err}"}, status=400)
            phone = data.get("number"); rid = data.get("id") or phone
            if not phone: return web.json_response({"error": "Lỗi NP: API không trả về số."}, status=400)
            await db_exec("INSERT INTO orders (user_id, request_id, provider, phone, country, operator, range_code, status, created_at, expires_at) VALUES (?, ?, 'NP', ?, ?, ?, ?, 'PENDING', ?, ?)", (uid, str(rid), str(phone), body.get("country"), body.get("service"), body.get("service"), now_text(), (now() + timedelta(minutes=15)).isoformat()))
            await clean_old_orders(uid)
            return web.json_response({"ok": True})

        elif provider == "BS":
            row = await db_exec("SELECT phone, country FROM basha_numbers WHERE country=? ORDER BY RANDOM() LIMIT 1", (body.get("country"),), fetch="one")
            if not row: return web.json_response({"error": "Hết số BS cho quốc gia này"}, status=404)
            phone, country_val = row["phone"] if isinstance(row, dict) else row[0], row["country"] if isinstance(row, dict) else row[1]
            req_id = f"BS_{phone}_{int(time.time())}"
            await db_exec("INSERT INTO orders (user_id, request_id, provider, phone, country, range_code, status, created_at, expires_at) VALUES (?, ?, 'BS', ?, ?, ?, 'PENDING', ?, ?)", (uid, req_id, str(phone), country_val, country_val, now_text(), (now() + timedelta(minutes=15)).isoformat()))
            await clean_old_orders(uid)
            return web.json_response({"ok": True})
            
        elif provider == "FAST_IVAS":
            row = await db_exec("SELECT phone, country FROM fast_ivas_numbers WHERE country=? ORDER BY RANDOM() LIMIT 1", (body.get("country"),), fetch="one")
            if not row: return web.json_response({"error": "Hết số FAST IVAS cho quốc gia này"}, status=404)
            phone, country_val = row["phone"], row["country"]
            req_id = f"FAST_IVAS_{phone}_{int(time.time())}"
            await db_exec("INSERT INTO orders (user_id, request_id, provider, phone, country, range_code, status, created_at, expires_at) VALUES (?, ?, 'FAST_IVAS', ?, ?, ?, 'PENDING', ?, ?)", (uid, req_id, str(phone), country_val, country_val, now_text(), (now() + timedelta(minutes=15)).isoformat()))
            await clean_old_orders(uid)
            return web.json_response({"ok": True})

        elif provider == "AHO":
            cid = body.get("country_id")
            oid = body.get("operator_id")
            if not cid or not oid: return web.json_response({"error": "Thiếu thông tin quốc gia hoặc nhà mạng."}, status=400)
            data, err = await api_request("GET", f"get-number/{AHO_API_KEY}/{cid}/{oid}", api_type="AHO")
            if err: return web.json_response({"error": f"Lỗi AHO: {err}"}, status=400)
            
            phone = data.get("phone_number")
            country = body.get("country_name") or "Unknown"
            operator = data.get("operator_name") or "Network"
            if not phone: return web.json_response({"error": "Lỗi AHO: Không lấy được số."}, status=400)
            
            req_id = f"AHO_{phone}_{int(time.time())}"
            await db_exec("INSERT INTO orders (user_id, request_id, provider, phone, country, operator, range_code, status, created_at, expires_at) VALUES (?, ?, 'AHO', ?, ?, ?, ?, 'PENDING', ?, ?)", 
                          (uid, req_id, str(phone), country, operator, str(oid), now_text(), (now() + timedelta(minutes=15)).isoformat()))
            await clean_old_orders(uid)
            return web.json_response({"ok": True})

        return web.json_response({"error": "Provider không hợp lệ"}, status=400)
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

async def mini_cancel_order(request):
    try:
        oid = int(request.match_info["oid"])
        order = await db_exec("SELECT provider, request_id, phone FROM orders WHERE id=? AND user_id=?", (oid, mini_uid(request)), fetch="one")
        if not order: return web.json_response({"error": "Not found"}, status=404)
        if order["provider"] == "SLVN": await api_request("POST", f"cancel/{order['request_id']}", api_type="SLVN")
        elif order["provider"] == "NP": await api_request("POST", "release_number", {"number": order["phone"]}, api_type="NP")
        await db_exec("UPDATE orders SET status='CANCELLED' WHERE id=?", (oid,))
        return web.json_response({"ok": True})
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

async def mini_save_wallet(request):
    try:
        uid = mini_uid(request); body = await request.json()
        address = str(body.get("address", "")).strip()
        if not re.fullmatch(r"(?:EQ|UQ)[a-zA-Z0-9_-]{46}", address): return web.json_response({"error": "Địa chỉ TON không đúng định dạng."}, status=400)
        await db_exec("UPDATE users SET wallet_ton=? WHERE user_id=?", (address, uid))
        return web.json_response({"ok": True})
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

async def mini_withdraw(request):
    try:
        if await get_setting("maintenance", "off") == "on": return web.json_response({"error": "Hệ thống đang bảo trì."}, status=403)
        uid = mini_uid(request); body = await request.json()
        amt_milli = int(float(body.get("amount", 0)) * 1000)
        u = await db_exec("SELECT wallet_ton, usd_milli FROM users WHERE user_id=?", (uid,), fetch="one")
        if not u or not u["wallet_ton"]: return web.json_response({"error": "Chưa cài ví TON"}, status=400)
        if amt_milli < MIN_WITHDRAW_MILLI or amt_milli > u["usd_milli"]: return web.json_response({"error": "Số dư không đủ hoặc dưới $1.00"}, status=400)
        ok, res = await change_usd(uid, -amt_milli, "WITHDRAW_HOLD", "TON Withdrawal")
        if not ok: return web.json_response({"error": res}, status=400)
        wid = await db_exec("INSERT INTO withdrawals (user_id, amount_milli, wallet_ton, status, created_at) VALUES (?, ?, ?, 'PENDING', ?)", (uid, amt_milli, u["wallet_ton"], now_text()))
        return web.json_response({"ok": True, "withdrawal_id": wid})
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

async def mini_admin_data(request):
    try:
        if not mini_admin_guard(request): return web.json_response({"error": "Forbidden"}, status=403)
        users = await db_exec("SELECT COUNT(*) as c FROM users", fetch="one")
        orders = await db_exec("SELECT COUNT(*) as c FROM orders", fetch="one")
        pending_wd = await db_exec("SELECT COUNT(*) as c FROM withdrawals WHERE status='PENDING'", fetch="one")
        bs_count = await db_exec("SELECT COUNT(*) as c FROM basha_numbers", fetch="one")
        wd_list = await db_exec("SELECT w.id, w.user_id, w.amount_milli, w.wallet_ton, u.first_name FROM withdrawals w JOIN users u ON u.user_id=w.user_id WHERE w.status='PENDING' ORDER BY w.id DESC LIMIT 20", fetch="all")
        return web.json_response({"stats": {"users": users["c"], "orders": orders["c"], "pending_wd": pending_wd["c"], "bs_count": bs_count["c"]}, "withdrawals": [{"id": r["id"], "user_id": r["user_id"], "amount": r["amount_milli"], "wallet": r["wallet_ton"], "name": r["first_name"]} for r in wd_list] if wd_list else [], "maintenance": await get_setting("maintenance", "off")})
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

async def mini_admin_users(request):
    try:
        if not mini_admin_guard(request): return web.json_response({"error": "Forbidden"}, status=403)
        users = await db_exec("SELECT user_id, first_name, username, usd_milli, joined_at FROM users ORDER BY joined_at DESC LIMIT 50", fetch="all")
        return web.json_response({"users": [{"id": r["user_id"], "name": r["first_name"], "username": r["username"], "balance": r["usd_milli"], "joined": r["joined_at"]} for r in users]})
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

async def mini_admin_user_detail(request):
    try:
        if not mini_admin_guard(request): return web.json_response({"error": "Forbidden"}, status=403)
        uid = int(request.match_info["uid"]); page = int(request.query.get("page", "1"))
        u = await db_exec("SELECT user_id, first_name, username, usd_milli, joined_at FROM users WHERE user_id=?", (uid,), fetch="one")
        if not u: return web.json_response({"error": "User not found"}, status=404)
        total_res = await db_exec("SELECT COUNT(*) as c FROM orders WHERE user_id=?", (uid,), fetch="one")
        total_pages = max(1, ((total_res["c"] if total_res else 0) + HISTORY_PAGE_SIZE - 1) // HISTORY_PAGE_SIZE)
        if page > total_pages: page = total_pages
        offset = (page - 1) * HISTORY_PAGE_SIZE
        orders = await db_exec("SELECT id, provider, phone, status, created_at FROM orders WHERE user_id=? ORDER BY id DESC LIMIT ? OFFSET ?", (uid, HISTORY_PAGE_SIZE, offset), fetch="all")
        stats = await db_exec("SELECT provider, COUNT(*) as c FROM orders WHERE user_id=? GROUP BY provider", (uid,), fetch="all")
        s_map = {"MK": 0, "NP": 0, "BS": 0, "SLVN": 0, "FAST_IVAS": 0, "AHO": 0}
        for s in (stats or []): s_map[s["provider"]] = s["c"]
        return web.json_response({"user": {"id": u["user_id"], "name": u["first_name"], "username": u["username"], "balance": u["usd_milli"], "joined": u["joined_at"]}, "stats": s_map, "orders": [{"id": r["id"], "provider": r["provider"], "phone": r["phone"], "status": r["status"], "date": r["created_at"]} for r in (orders or [])], "current_page": page, "total_pages": total_pages})
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

async def mini_admin_user_history(request):
    try:
        if not mini_admin_guard(request): return web.json_response({"error": "Forbidden"}, status=403)
        uid = int(request.match_info["uid"])
        rows = await db_exec("SELECT id, amount_milli, note, created_at FROM admin_history WHERE user_id = ? ORDER BY id DESC LIMIT 50", (uid,), fetch="all")
        history = [{"id": r["id"], "amount": r["amount_milli"], "note": r["note"], "date": r["created_at"]} for r in (rows or [])]
        return web.json_response({"history": history})
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

async def mini_admin_user_action(request):
    try:
        if not mini_admin_guard(request): return web.json_response({"error": "Forbidden"}, status=403)
        uid = int(request.match_info["uid"]); body = await request.json(); action = body.get("action")
        
        if action == "bonus":
            amt = int(float(body.get("amount", 0)) * 1000)
            if amt <= 0: return web.json_response({"error": "Số tiền không hợp lệ"}, status=400)
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Chấp nhận", callback_data=f"admin_bonus_accept_{amt}_{uid}"), InlineKeyboardButton(text="❌ Hủy", callback_data=f"admin_bonus_reject_{amt}_{uid}")]])
            try:
                await bot.send_message(uid, f"🎁 <b>Bạn nhận được tiền từ Admin!</b>\n\nSố tiền: <b>${amt/1000:.3f}</b>\nBấm chấp nhận để cộng vào số dư tài khoản.", reply_markup=kb)
                await db_exec("INSERT INTO admin_history (admin_id, user_id, amount_milli, note, created_at) VALUES (?, ?, ?, ?, ?)", (mini_uid(request), uid, amt, "Gửi yêu cầu cộng tiền", now_text()))
                return web.json_response({"ok": True, "msg": "Đã gửi thông báo cho user!"})
            except Exception as e: return web.json_response({"error": f"Không thể gửi tin nhắn: {str(e)}"}, status=400)
                
        elif action == "deduct":
            amt = int(float(body.get("amount", 0)) * 1000)
            if amt <= 0: return web.json_response({"error": "Số tiền không hợp lệ"}, status=400)
            u = await get_user(uid)
            if not u or u["usd_milli"] < amt: return web.json_response({"error": "Số dư của user không đủ để trừ!"}, status=400)
            ok, res = await change_usd(uid, -amt, "ADMIN_DEDUCT", "Admin deducted balance")
            if ok:
                try: await bot.send_message(uid, f"⚠️ Số dư của bạn đã bị Admin trừ <b>${amt/1000:.3f}</b>.")
                except: pass
                return web.json_response({"ok": True, "msg": f"Đã trừ ${amt/1000:.3f} của user!"})
            return web.json_response({"error": res}, status=400)
                
        elif action == "revoke":
            u = await get_user(uid)
            if not u or u["usd_milli"] <= 0: return web.json_response({"error": "User không có số dư để thu hồi"}, status=400)
            current_bal = u["usd_milli"]
            ok, res = await change_usd(uid, -current_bal, "ADMIN_REVOKE", "Admin revoked balance")
            if ok:
                try: await bot.send_message(uid, f"⚠️ Số dư của bạn đã bị Admin thu hồi (${current_bal/1000:.3f}).")
                except: pass
                return web.json_response({"ok": True, "msg": "Đã thu hồi toàn bộ số dư!"})
            return web.json_response({"error": res}, status=400)
            
        elif action == "set_min":
            min_val = int(float(body.get("amount", 0)) * 1000)
            u = await get_user(uid)
            if not u: return web.json_response({"error": "User not found"}, status=404)
            diff = min_val - u["usd_milli"]
            if diff != 0: await change_usd(uid, diff, "ADMIN_SET", "Admin adjusted balance")
            return web.json_response({"ok": True, "msg": f"Đã cập nhật số dư thành ${min_val/1000:.3f}!"})
        return web.json_response({"error": "Action không hợp lệ"}, status=400)
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

async def mini_admin_revoke_manual(request):
    try:
        if not mini_admin_guard(request): return web.json_response({"error": "Forbidden"}, status=403)
        body = await request.json()
        uid, amt_milli = int(body.get("uid")), int(float(body.get("amount", 0)) * 1000)
        if amt_milli <= 0: return web.json_response({"error": "Số tiền không hợp lệ"}, status=400)
        
        u = await get_user(uid)
        if not u: return web.json_response({"error": "User not found"}, status=404)
        
        ok, res = await change_usd(uid, -amt_milli, "ADMIN_REVOKE_MANUAL", "Thu hồi thủ công từ Admin")
        if ok:
            try: await bot.send_message(uid, f"⚠️ Số dư của bạn đã bị Admin thu hồi <b>${amt_milli/1000:.3f}</b>.")
            except: pass
            return web.json_response({"ok": True, "msg": f"Đã thu hồi ${amt_milli/1000:.3f} thành công!"})
        return web.json_response({"error": res}, status=400)
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

async def mini_admin_broadcast_radar(request):
    try:
        if not mini_admin_guard(request): return web.json_response({"error": "Forbidden"}, status=403)
        body = await request.json()
        platform, custom_msg, image_b64 = body.get("platform", "All"), body.get("message", "").strip(), body.get("image_b64", "").strip()
        text_content = custom_msg if custom_msg else f"🚨 <b>THÔNG BÁO RADAR OTP CAO</b>\n\nNền tảng đang có tỷ lệ nhận OTP cao: <b>{platform}</b>\nNhanh tay vào ứng dụng lấy số ngay nào anh em!"
        photo_bytes = None
        if image_b64:
            try:
                import base64
                header, encoded = image_b64.split(",", 1); photo_bytes = base64.b64decode(encoded)
            except: pass
        users = await db_exec("SELECT user_id FROM users", fetch="all")
        sent = 0
        for row in users or []:
            try:
                if photo_bytes: await bot.send_photo(row["user_id"], photo=BufferedInputFile(photo_bytes, filename="radar.jpg"), caption=text_content)
                else: await bot.send_message(row["user_id"], text_content)
                sent += 1; await asyncio.sleep(0.05)
            except: pass
        return web.json_response({"ok": True, "msg": f"Đã gửi thông báo Radar đến {sent} user!"})
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

async def mini_admin_cmd(request):
    try:
        if not mini_admin_guard(request): return web.json_response({"error": "Forbidden"}, status=403)
        try: cmd = (await request.json()).get("cmd")
        except: return web.json_response({"ok": True, "msg": "Invalid command payload"})
            
        if cmd == "pollnow":
            if not _mk_poller: return web.json_response({"ok": True, "msg": "Poller not running"})
            c, n, err = await _mk_poller._poll_once()
            if err: return web.json_response({"ok": True, "msg": f"Lỗi khi Poll OTP: {err}"})
            return web.json_response({"ok": True, "msg": f"Checked: {c} đơn.\nNew OTPs: {n}\nTrạng thái: OK"})
        elif cmd == "health":
            pending = await db_exec("SELECT COUNT(*) FROM orders WHERE status='PENDING'", fetch='one')
            pending_count = pending[0] if pending and len(pending) > 0 else 0
            poller = "OFF" if not _mk_poller else f"ON ({_mk_poller.interval}s)"
            return web.json_response({"ok": True, "msg": f"DB: Turso\nMK Key: {'OK' if MK_API_KEY else 'MISSING'}\nNP Key: {'OK' if NP_API_KEY else 'MISSING'}\nBS Key: {'OK' if BS_API_KEY else 'MISSING'}\nSLVN Key: {'OK' if SLVN_API_KEY else 'MISSING'}\nPending Orders: {pending_count}\nPoller: {poller}"})
        elif cmd == "whoami":
            data, err = await api_request("GET", "whoami", api_type="MK")
            return web.json_response({"ok": True, "msg": f"API Error: {err}" if err else json.dumps(data, indent=2, ensure_ascii=False)})
        elif cmd == "testnp":
            data, err = await api_request("GET", "services", api_type="NP")
            return web.json_response({"ok": True, "msg": f"API Error: {err}" if err else json.dumps(data, indent=2, ensure_ascii=False)[:1000]})
        elif cmd == "radar":
            data, err = await api_request("GET", "radar", params={"charts": "true", "limit": 10}, api_type="MK")
            return web.json_response({"ok": True, "msg": f"API Error: {err}" if err else json.dumps(data, indent=2, ensure_ascii=False)[:2000]})
        return web.json_response({"ok": True, "msg": "Unknown command"})
    except Exception as e: return web.json_response({"ok": True, "msg": f"Lỗi thực thi: {str(e)}"})

async def mini_admin_maintenance(request):
    try:
        if not mini_admin_guard(request): return web.json_response({"error": "Forbidden"}, status=403)
        body = await request.json(); action = body.get("action")
        
        if action == "enable": 
            message = body.get("message", "").strip()
            if not message: message = "🎉 <b>Bot đã hoạt động trở lại!</b>\nMời anh em vào lấy số tiếp nhé!"
            await set_setting("maintenance", "off")
            users = await db_exec("SELECT user_id FROM users", fetch="all"); sent = 0
            for row in users or []:
                try: await bot.send_message(row["user_id"], f"🟢 <b>THÔNG BÁO</b>\n\n{message}"); sent += 1
                except: pass
                await asyncio.sleep(0.05)
            return web.json_response({"ok": True, "msg": f"Đã TẮT bảo trì. Đã thông báo {sent} user."})
            
        elif action == "disable":
            message, image_b64 = body.get("message", ""), body.get("image_b64", "")
            await set_setting("maintenance", "on"); await set_setting("maint_message", message); await set_setting("maint_image", image_b64)
            users = await db_exec("SELECT user_id FROM users", fetch="all"); sent = 0; photo_bytes = None
            if image_b64:
                try:
                    import base64
                    header, encoded = image_b64.split(",", 1); photo_bytes = base64.b64decode(encoded)
                except: pass
            for row in users or []:
                try:
                    if photo_bytes: await bot.send_photo(row["user_id"], photo=BufferedInputFile(photo_bytes, filename="maintenance.jpg"), caption=f"🛠 <b>THÔNG BÁO BẢO TRÌ</b>\n\n{message}")
                    else: await bot.send_message(row["user_id"], f"🛠 <b>THÔNG BÁO BẢO TRÌ</b>\n\n{message}")
                    sent += 1
                except: pass
                await asyncio.sleep(0.05)
            return web.json_response({"ok": True, "msg": f"Đã BẬT bảo trì. Đã gửi thông báo đến {sent} user."})
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

async def mini_admin_bs_add(request):
    try:
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
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

async def mini_admin_bs_delete(request):
    try:
        if not mini_admin_guard(request): return web.json_response({"error": "Forbidden"}, status=403)
        body = await request.json(); country = body.get("country")
        if country == "ALL": await db_exec("DELETE FROM basha_numbers")
        else: await db_exec("DELETE FROM basha_numbers WHERE country=?", (country,))
        return web.json_response({"ok": True})
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

async def mini_admin_fastivas_add(request):
    try:
        if not mini_admin_guard(request): return web.json_response({"error": "Forbidden"}, status=403)
        body = await request.json()
        numbers_list = body.get("numbers", [])
        
        if not numbers_list: return web.json_response({"error": "Danh sách trống"}, status=400)

        added = 0
        to_insert = []
        for phone in numbers_list:
            phone = str(phone).strip().lstrip("+")
            if not phone.isdigit() or len(phone) < 7: continue
            
            country = "Unknown"
            for pfx in SORTED_PREFIXES:
                if phone.startswith(pfx):
                    country = COUNTRY_CODES[pfx][0]
                    break
            to_insert.append((phone, country, now_text()))

        if to_insert:
            def _bulk_insert():
                db = open_db()
                try:
                    db.executemany("INSERT OR IGNORE INTO fast_ivas_numbers (phone, country, added_at) VALUES (?, ?, ?)", to_insert)
                    db.commit()
                    return True
                except Exception as e:
                    logger.error(f"Bulk insert error: {e}")
                    return False
                finally:
                    db.close()
            await asyncio.get_running_loop().run_in_executor(None, _bulk_insert)
            
        return web.json_response({"ok": True, "added": len(to_insert)})
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

async def mini_admin_fastivas_delete(request):
    try:
        if not mini_admin_guard(request): return web.json_response({"error": "Forbidden"}, status=403)
        body = await request.json(); country = body.get("country")
        if country == "ALL": await db_exec("DELETE FROM fast_ivas_numbers")
        else: await db_exec("DELETE FROM fast_ivas_numbers WHERE country=?", (country,))
        return web.json_response({"ok": True})
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

async def mini_admin_wd_action(request):
    try:
        if not mini_admin_guard(request): return web.json_response({"error": "Forbidden"}, status=403)
        body = await request.json(); wid = int(body.get("wid")); action = body.get("action")
        if action == "approve":
            await db_exec("UPDATE withdrawals SET status='APPROVED', processed_at=? WHERE id=?", (now_text(), wid))
            return web.json_response({"ok": True})
        elif action == "reject":
            row = await db_exec("SELECT user_id, amount_milli FROM withdrawals WHERE id=? AND status='PENDING'", (wid,), fetch="one")
            if not row: return web.json_response({"error": "Not found"}, status=404)
            await db_exec("UPDATE withdrawals SET status='REJECTED', processed_at=? WHERE id=?", (now_text(), wid))
            await change_usd(row["user_id"], row["amount_milli"], "WITHDRAW_REFUND", f"Refund #{wid}")
            return web.json_response({"ok": True})
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

async def mini_mk_ranges(request):
    try:
        data, err = await api_request("GET", "access_list", params={"limit": 1000}, api_type="MK")
        countries = []
        if not err and data and isinstance(data, dict):
            items = data.get("data", {}).get("items") or data.get("items") or []
            if items:
                c_map = {}
                for item in items:
                    c_name, r_val = item.get("country") or item.get("country_name"), item.get("range") or item.get("prefix") or item.get("code")
                    if c_name and r_val: c_map.setdefault(c_name, []).append(str(r_val))
                for c_name, ranges in c_map.items(): countries.append({"name": c_name, "range": ranges[0], "flag": get_country_flag(c_name)})
        if not countries: countries = [{"name": k, "range": v, "flag": get_country_flag(k)} for k, v in FALLBACK_COUNTRIES.items()]
        return web.json_response({"countries": countries})
    except Exception as e: return web.json_response({"countries": [{"name": k, "range": v, "flag": get_country_flag(k)} for k, v in FALLBACK_COUNTRIES.items()]})

async def mini_np_services(request):
    try:
        data, err = await api_request("GET", "services", api_type="NP")
        srvs = data.get("services", []) if data and not err else []
        return web.json_response({"services": [{"name": s["name"], "key": s["name"], "count": s["count"]} for s in srvs if s.get("count", 0) > 0]})
    except Exception as e: return web.json_response({"services": []})

async def mini_np_countries(request):
    try:
        service_name = request.query.get("service")
        data, err = await api_request("GET", "countries", params={"service": service_name}, api_type="NP")
        countries = data.get("countries", []) if data and not err else []
        return web.json_response({"countries": [{"code": c["name"], "name": ISO_MAP.get(c["name"], c["name"]), "count": c["count"]} for c in countries if c.get("count", 0) > 0]})
    except Exception as e: return web.json_response({"countries": []})

async def mini_bs_countries(request):
    try:
        rows = await db_exec("SELECT country, flag, COUNT(*) as c FROM basha_numbers GROUP BY country, flag", fetch="all")
        return web.json_response({"countries": [{"name": r["country"], "flag": r["flag"], "count": r["c"]} for r in rows] if rows else []})
    except Exception as e: return web.json_response({"countries": []})

async def mini_fastivas_countries(request):
    try:
        rows = await db_exec("SELECT country, COUNT(*) as c FROM fast_ivas_numbers GROUP BY country", fetch="all")
        return web.json_response({"countries": [{"name": r["country"], "flag": get_country_flag(r["country"]), "count": r["c"]} for r in rows] if rows else []})
    except Exception as e: return web.json_response({"countries": []})

async def mini_slvn_countries(request):
    try:
        data, err = await api_request("GET", "available-countries", params={"service": "any"}, api_type="SLVN")
        if err or not data: return web.json_response({"countries": []})
        return web.json_response({"countries": [{"name": c.get("country"), "code": c.get("countryCode"), "flag": c.get("flag"), "tag": c.get("tag"), "rate": c.get("rateUsd")} for c in data.get("data", [])]})
    except Exception as e: return web.json_response({"countries": []})

# LOGIC LẤY API AHO
async def mini_aho_countries(request):
    try:
        # Phải gọi include=available-countries để lấy danh sách
        data, err = await api_request("GET", f"get-data/{AHO_API_KEY}?include=available-countries", api_type="AHO")
        
        if err: 
            logger.error(f"AHO Countries API Error: {err}")
            return web.json_response({"countries": []})
            
        if not data or data.get("status") != "success":
            logger.error(f"AHO API Response Error: {data}")
            return web.json_response({"countries": []})

        # Parse chính xác theo cấu trúc: data -> availableCountries -> data
        countries_raw = data.get("data", {}).get("availableCountries", {}).get("data", [])
        
        result = [{"id": c["id"], "name": c["name"], "flag": get_country_flag(c["name"])} for c in countries_raw]
        return web.json_response({"countries": result})
    except Exception as e: 
        logger.error(f"AHO Countries Exception: {e}")
        return web.json_response({"countries": []})

async def mini_aho_operators(request):
    try:
        country_id = request.query.get("country_id")
        if not country_id: return web.json_response({"operators": []})
        
        data, err = await api_request("GET", f"get-data/{AHO_API_KEY}?include=available-operators&country_id={country_id}", api_type="AHO")
        
        if err:
            logger.error(f"AHO Operators API Error: {err}")
            return web.json_response({"operators": []})
            
        if not data or data.get("status") != "success":
            logger.error(f"AHO Operators Response Error: {data}")
            return web.json_response({"operators": []})

        operators_raw = data.get("data", {}).get("availableOperators", {}).get("data", [])
        
        result = [{"id": o["id"], "name": o["name"]} for o in operators_raw]
        return web.json_response({"operators": result})
    except Exception as e: 
        logger.error(f"AHO Operators Exception: {e}")
        return web.json_response({"operators": []})

async def mini_mail_domains(request):
    try:
        data, err = await api_request("GET", "mail/domains", api_type="NP")
        if err: return web.json_response({"domains": []})
        return web.json_response({"domains": data.get("domains", [])})
    except Exception as e: return web.json_response({"domains": []})

async def mini_mail_generate(request):
    try:
        body = await request.json(); username, domain = body.get("username"), body.get("domain")
        payload = {}
        if username: payload["username"] = username
        if domain: payload["domain"] = domain
        data, err = await api_request("POST", "mail/generate", payload, api_type="NP")
        if err: return web.json_response({"error": err}, status=500)
        return web.json_response({"success": True, "mail": data.get("mail", {})})
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

async def mini_mail_history(request):
    try:
        data, err = await api_request("GET", "mail/history", api_type="NP")
        if err: return web.json_response({"history": []})
        return web.json_response({"history": data.get("history", [])})
    except Exception as e: return web.json_response({"history": []})

async def mini_mail_messages(request):
    try:
        address = request.query.get("address")
        if not address: return web.json_response({"messages": []})
        data, err = await api_request("GET", "mail/messages", params={"address": address}, api_type="NP")
        if err: return web.json_response({"messages": []})
        return web.json_response({"messages": data.get("messages", [])})
    except Exception as e: return web.json_response({"messages": []})

async def web_server():
    try:
        app = web.Application(middlewares=[mini_auth_middleware], client_max_size=20 * 1024 * 1024)
        
        async def serve_html(request): return web.Response(text=MINIAPP_HTML, content_type='text/html')
        async def health(request): return web.json_response({"ok": True})
            
        app.router.add_get('/', serve_html)
        app.router.add_get('/miniapp', serve_html)
        app.router.add_get('/health', health)
        
        app.router.add_get('/api/mini/me', mini_me)
        app.router.add_post('/api/mini/language', mini_language_update)
        app.router.add_get('/api/mini/stats', mini_stats)
        app.router.add_get('/api/mini/radar', mini_radar_feed)
        app.router.add_get('/api/mini/leaderboard', mini_leaderboard)
        app.router.add_get('/api/mini/orders/active', mini_active_orders)
        app.router.add_get('/api/mini/orders', mini_history_orders)
        app.router.add_post('/api/mini/orders', mini_create_order)
        app.router.add_post('/api/mini/orders/clear', mini_clear_history)
        app.router.add_post('/api/mini/orders/{oid}/cancel', mini_cancel_order)
        app.router.add_get('/api/mini/mk/ranges', mini_mk_ranges)
        app.router.add_get('/api/mini/np/services', mini_np_services)
        app.router.add_get('/api/mini/np/countries', mini_np_countries)
        app.router.add_get('/api/mini/bs/countries', mini_bs_countries)
        app.router.add_get('/api/mini/fastivas/countries', mini_fastivas_countries)
        app.router.add_get('/api/mini/slvn/countries', mini_slvn_countries)
        app.router.add_get('/api/mini/aho/countries', mini_aho_countries)
        app.router.add_get('/api/mini/aho/operators', mini_aho_operators)
        app.router.add_post('/api/mini/wallet/address', mini_save_wallet)
        app.router.add_post('/api/mini/wallet/withdraw', mini_withdraw)
        
        app.router.add_get('/api/mini/mail/domains', mini_mail_domains)
        app.router.add_post('/api/mini/mail/generate', mini_mail_generate)
        app.router.add_get('/api/mini/mail/history', mini_mail_history)
        app.router.add_get('/api/mini/mail/messages', mini_mail_messages)
        
        app.router.add_get('/api/mini/admin/data', mini_admin_data)
        app.router.add_get('/api/mini/admin/users', mini_admin_users)
        app.router.add_get('/api/mini/admin/users/{uid}', mini_admin_user_detail)
        app.router.add_get('/api/mini/admin/users/{uid}/history', mini_admin_user_history)
        app.router.add_post('/api/mini/admin/users/{uid}/action', mini_admin_user_action)
        app.router.add_post('/api/mini/admin/revoke', mini_admin_revoke_manual)
        app.router.add_post('/api/mini/admin/broadcast/radar', mini_admin_broadcast_radar)
        app.router.add_post('/api/mini/admin/cmd', mini_admin_cmd)
        app.router.add_post('/api/mini/admin/maintenance', mini_admin_maintenance)
        app.router.add_post('/api/mini/admin/withdraw/action', mini_admin_wd_action)
        app.router.add_post('/api/mini/admin/bs/add', mini_admin_bs_add)
        app.router.add_post('/api/mini/admin/bs/delete', mini_admin_bs_delete)
        app.router.add_post('/api/mini/admin/fastivas/add', mini_admin_fastivas_add)
        app.router.add_post('/api/mini/admin/fastivas/delete', mini_admin_fastivas_delete)
        
        runner = web.AppRunner(app); await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", PORT); await site.start()
        logger.info(f"✅ Web server started on port {PORT}")
    except Exception as e:
        logger.error(f"❌ WEB SERVER ERROR: {e}")

async def set_bot_commands():
    try:
        user_commands = [BotCommand(command="start", description="Open main menu")]
        await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())
        admin_commands = user_commands + [BotCommand(command="admin", description="[Admin] Panel"), BotCommand(command="broadcast", description="[Admin] Broadcast")]
        try: await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=ADMIN_ID))
        except Exception as e: logger.error(f"Error: {e}")
    except Exception as e: logger.error(f"set_bot_commands error: {e}")

async def main():
    global BOT_USERNAME, _mk_poller
    if not BOT_TOKEN: return logger.error("❌ BOT_TOKEN IS EMPTY!")
    try: 
        me = await bot.get_me(); BOT_USERNAME = me.username; await set_bot_commands()
        if WEBAPP_URL.startswith("https://"):
            await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="FAST IVAS", web_app=WebAppInfo(url=WEBAPP_URL + "?v=29")))
    except Exception as e: return logger.error(f"❌ Error getting bot info: {e}")
    
    await init_db()
    asyncio.create_task(web_server())
    _mk_poller = MkOtpPoller(bot, OTP_GROUP_ID, interval=3)
    asyncio.create_task(_mk_poller.run_forever())
    asyncio.create_task(auto_expire_orders())
    
    logger.info("🚀 FAST IVAS starting polling...")
    await dp.start_polling(bot, drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())