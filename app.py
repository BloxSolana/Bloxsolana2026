# File: app.py

import os
import json
import hashlib
import hmac
import logging
import asyncio
import re
import time
from urllib.parse import parse_qsl
from types import SimpleNamespace
from datetime import datetime, timedelta
from aiohttp import web

from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault, MenuButtonWebApp, WebAppInfo, Message, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile

from database import (
    init_db, db_exec, get_setting, set_setting, get_user, register_user, now, now_text, 
    is_admin, unix_now, clean_old_orders, open_db, change_usd, safe,
    COUNTRY_CODES, SORTED_PREFIXES, ISO_MAP, FALLBACK_COUNTRIES, get_country_flag, get_network_icon, detect_otp_platform
)
from api_services import api_request, MkOtpPoller, MK_API_KEY, NP_API_KEY
from handlers import setup_handlers
from miniapp_html import MINIAPP_HTML

BOT_TOKEN        = os.getenv("BOT_TOKEN", "").strip()
WEBAPP_URL       = os.getenv("WEBAPP_URL", "").strip()
ADMIN_ID         = int(os.getenv("ADMIN_ID", "0") or 0)
OTP_GROUP_ID     = int(os.getenv("OTP_GROUP_ID", "-1004341368656"))
PORT             = int(os.getenv("PORT", "10000"))

ORDER_LIFETIME_MINUTES = 15
MIN_WITHDRAW_MILLI     = 1000
HISTORY_PAGE_SIZE      = 10

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FAST_IVAS")

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp  = Dispatcher()
BOT_USERNAME = ""
_mk_poller = None

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

async def mini_language_update(request):
    uid = mini_uid(request); body = await request.json()
    await db_exec("UPDATE users SET language=? WHERE user_id=?", (body.get("language", "vi"), uid))
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
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

async def mini_radar_feed(request):
    formatted_items = []
    platform_counts = {}
    country_counts = {}
    current_unix = int(time.time())

    # 1. Lấy dữ liệu từ MK API v3 (/radar?charts=true)
    try:
        data, err = await api_request("GET", "radar", params={"charts": "true", "limit": 100}, api_type="MK")
        if not err and data:
            resp_data = data.get("data", data)
            items = resp_data.get("feed") or resp_data.get("items") or []
            if isinstance(items, list):
                for idx, item in enumerate(items):
                    p_name = item.get("platform") or item.get("service") or item.get("app") or item.get("message") or "Other"
                    plat = detect_otp_platform(p_name)
                    platform_counts[plat] = platform_counts.get(plat, 0) + 1

                    country = item.get("country") or item.get("country_name") or "Vietnam"
                    country_counts[country] = country_counts.get(country, 0) + 1

                    timestamp = current_unix - (idx * 3)

                    formatted_items.append({
                        "phone": item.get("number") or item.get("phone") or item.get("full_number") or "N/A",
                        "country": country,
                        "flag": get_country_flag(country),
                        "operator": item.get("operator") or item.get("network") or "Network",
                        "message": item.get("otp") or item.get("message") or item.get("sms") or "OTP Code received",
                        "timestamp": timestamp,
                        "platform": plat
                    })
    except Exception as e:
        logger.warning(f"MK API v3 Radar Fetch Error: {e}")

    # 2. Lấy đơn hàng COMPLETED thực tế trong Database (30 phút gần nhất)
    cutoff_time = (now() - timedelta(minutes=30)).isoformat()
    local_orders = await db_exec(
        "SELECT phone, country, operator, full_sms, platform, updated_at, created_at FROM orders WHERE status='COMPLETED' AND (updated_at >= ? OR created_at >= ?) ORDER BY id DESC LIMIT 50", 
        (cutoff_time, cutoff_time), fetch="all"
    )
    for r in (local_orders or []):
        plat = r["platform"] or detect_otp_platform(r["full_sms"])
        platform_counts[plat] = platform_counts.get(plat, 0) + 1
        country = r["country"] or "Vietnam"
        country_counts[country] = country_counts.get(country, 0) + 1
        
        t_str = r["updated_at"] or r["created_at"]
        try:
            dt = datetime.fromisoformat(t_str)
            timestamp = int(dt.timestamp())
        except:
            timestamp = current_unix

        formatted_items.append({
            "phone": r["phone"] or "N/A",
            "country": country,
            "flag": get_country_flag(country),
            "operator": r["operator"] or "Network",
            "message": r["full_sms"] or "OTP Received successfully",
            "timestamp": timestamp,
            "platform": plat
        })

    formatted_items.sort(key=lambda x: x["timestamp"], reverse=True)
    formatted_items = formatted_items[:100]

    total_records = len(formatted_items)
    platforms = [{"name": k, "count": v, "icon": get_network_icon(k)} for k, v in sorted(platform_counts.items(), key=lambda x: x[1], reverse=True) if v > 0]
    countries = [{"name": k, "count": v, "flag": get_country_flag(k)} for k, v in sorted(country_counts.items(), key=lambda x: x[1], reverse=True)]

    return web.json_response({
        "items": formatted_items,
        "platforms": platforms,
        "countries": countries,
        "total_records": total_records
    })

async def mini_leaderboard(request):
    top_users = await db_exec("""
        SELECT u.user_id, u.first_name, u.usd_milli, 
        (SELECT COUNT(*) FROM orders WHERE user_id = u.user_id AND status = 'COMPLETED') as total_otps 
        FROM users u ORDER BY u.usd_milli DESC LIMIT 10
    """, fetch="all")
    return web.json_response({"leaderboard": [{"name": u["first_name"], "balance": u["usd_milli"], "total_otps": u["total_otps"]} for u in top_users] if top_users else []})

async def mini_active_orders(request):
    uid = mini_uid(request)
    rows = await db_exec("SELECT id, provider, phone, country, status, created_at, otp_code, platform, full_sms FROM orders WHERE user_id=? AND status='PENDING' ORDER BY id DESC", (uid,), fetch="all")
    orders = []
    for r in (rows or []):
        plat = r["platform"] or detect_otp_platform(r["full_sms"])
        orders.append({
            "id": r["id"], "provider": r["provider"], "phone": r["phone"], "country": r["country"], 
            "status": r["status"], "created_at": r["created_at"], "otp": r["otp_code"], 
            "platform": plat, "icon": get_network_icon(plat), "flag": get_country_flag(r["country"])
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
    
    rows = await db_exec("SELECT id, provider, phone, country, status, created_at, otp_code, platform, full_sms FROM orders WHERE user_id=? ORDER BY id DESC LIMIT ? OFFSET ?", (uid, HISTORY_PAGE_SIZE, offset), fetch="all")
    orders = []
    for r in (rows or []):
        plat = r["platform"] or detect_otp_platform(r["full_sms"])
        orders.append({
            "id": r["id"], "provider": r["provider"], "phone": r["phone"], "country": r["country"], 
            "status": r["status"], "created_at": r["created_at"], "otp": r["otp_code"], 
            "platform": plat, "icon": get_network_icon(plat), "flag": get_country_flag(r["country"])
        })
    return web.json_response({"orders": orders, "current_page": page, "total_pages": total_pages, "total_records": total})

async def mini_create_order(request):
    if await get_setting("maintenance", "off") == "on": return web.json_response({"error": "Hệ thống đang bảo trì, không thể mua số."}, status=403)
    uid = mini_uid(request); body = await request.json()
    provider = body.get("provider")
    
    if provider == "MK":
        range_val = body.get("range")
        if not range_val or range_val == "undefined" or range_val == "null":
            return web.json_response({"error": "Lỗi MK: Range không hợp lệ."}, status=400)
        data, err = await api_request("POST", "getnum/number", {"range": str(range_val).strip()}, api_type="MK")
        if err: return web.json_response({"error": f"Lỗi MK: {err}"}, status=400)
        inner_data = data.get("data", {})
        rid = inner_data.get("request_id")
        phone = inner_data.get("number") or inner_data.get("full_number") or "N/A"
        country = inner_data.get("country") or body.get("country_name") or "Unknown"
        if not rid: return web.json_response({"error": f"Lỗi MK: API không trả về ID."}, status=400)
        await db_exec("INSERT INTO orders (user_id, request_id, provider, phone, country, range_code, status, created_at, expires_at) VALUES (?, ?, 'MK', ?, ?, ?, 'PENDING', ?, ?)", (uid, str(rid), str(phone), country, str(range_val), now_text(), (now() + timedelta(minutes=15)).isoformat()))
        await clean_old_orders(uid)
        return web.json_response({"ok": True})

    elif provider == "NP":
        if not NP_API_KEY:
            return web.json_response({"error": "Chưa cấu hình NP_API_KEY trên server!"}, status=400)
        data, err = await api_request("POST", "request_number", {"service": body.get("service"), "country": body.get("country")}, api_type="NP")
        if err: return web.json_response({"error": f"Lỗi NP: {err}"}, status=400)
        if not data or not isinstance(data, dict):
            return web.json_response({"error": "Phản hồi từ NP không hợp lệ"}, status=400)
        phone = data.get("number") or data.get("phone")
        if not phone: return web.json_response({"error": "Lỗi NP: API không trả về số."}, status=400)
        req_id = f"NP_{phone}_{int(time.time())}"
        await db_exec("INSERT INTO orders (user_id, request_id, provider, phone, country, operator, range_code, status, created_at, expires_at) VALUES (?, ?, 'NP', ?, ?, ?, ?, 'PENDING', ?, ?)", (uid, req_id, str(phone), body.get("country"), body.get("service"), body.get("service"), now_text(), (now() + timedelta(minutes=15)).isoformat()))
        await clean_old_orders(uid)
        return web.json_response({"ok": True})

    elif provider == "BASHA":
        row = await db_exec("SELECT phone, country FROM basha_numbers WHERE country=? ORDER BY RANDOM() LIMIT 1", (body.get("country"),), fetch="one")
        if not row: return web.json_response({"error": "Hết số BS cho quốc gia này"}, status=404)
        
        phone = row["phone"] if isinstance(row, dict) else row[0]
        country_val = row["country"] if isinstance(row, dict) else row[1]
        
        req_id = f"BS_{phone}_{int(time.time())}"
        await db_exec("INSERT INTO orders (user_id, request_id, provider, phone, country, range_code, status, created_at, expires_at) VALUES (?, ?, 'BASHA', ?, ?, ?, 'PENDING', ?, ?)", (uid, req_id, str(phone), country_val, country_val, now_text(), (now() + timedelta(minutes=15)).isoformat()))
        await clean_old_orders(uid)
        return web.json_response({"ok": True})

    elif provider == "SLVN":
        payload = {"service": "ANY", "countryCode": body.get("country_code"), "tag": body.get("tag")}
        data, err = await api_request("POST", "rent", payload, api_type="SLVN")
        if err: return web.json_response({"error": f"Lỗi SLVN: {err}"}, status=400)
        order_data = data.get("data", {})
        await db_exec("INSERT INTO orders (user_id, request_id, provider, phone, country, range_code, status, created_at, expires_at) VALUES (?, ?, 'SLVN', ?, ?, ?, 'PENDING', ?, ?)", (uid, order_data.get("rentalId"), order_data.get("phoneNumber"), order_data.get("country"), body.get("tag"), now_text(), (now() + timedelta(minutes=15)).isoformat()))
        await clean_old_orders(uid)
        return web.json_response({"ok": True})

    return web.json_response({"error": "Provider không hợp lệ"}, status=400)

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
    if not re.fullmatch(r"(?:EQ|UQ)[a-zA-Z0-9_-]{46}", address): return web.json_response({"error": "Địa chỉ TON không đúng định dạng."}, status=400)
    await db_exec("UPDATE users SET wallet_ton=? WHERE user_id=?", (address, uid))
    return web.json_response({"ok": True})

async def mini_withdraw(request):
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

async def mini_admin_data(request):
    if not mini_admin_guard(request): return web.json_response({"error": "Forbidden"}, status=403)
    users = await db_exec("SELECT COUNT(*) as c FROM users", fetch="one")
    orders = await db_exec("SELECT COUNT(*) as c FROM orders", fetch="one")
    pending_wd = await db_exec("SELECT COUNT(*) as c FROM withdrawals WHERE status='PENDING'", fetch="one")
    bs_count = await db_exec("SELECT COUNT(*) as c FROM basha_numbers", fetch="one")
    wd_list = await db_exec("SELECT w.id, w.user_id, w.amount_milli, w.wallet_ton, u.first_name FROM withdrawals w JOIN users u ON u.user_id=w.user_id WHERE w.status='PENDING' ORDER BY w.id DESC LIMIT 20", fetch="all")
    return web.json_response({"stats": {"users": users["c"], "orders": orders["c"], "pending_wd": pending_wd["c"], "bs_count": bs_count["c"]}, "withdrawals": [{"id": r["id"], "user_id": r["user_id"], "amount": r["amount_milli"], "wallet": r["wallet_ton"], "name": r["first_name"]} for r in wd_list] if wd_list else [], "maintenance": await get_setting("maintenance", "off")})

async def mini_admin_users(request):
    if not mini_admin_guard(request): return web.json_response({"error": "Forbidden"}, status=403)
    users = await db_exec("SELECT user_id, first_name, username, usd_milli, joined_at FROM users ORDER BY joined_at DESC LIMIT 50", fetch="all")
    return web.json_response({"users": [{"id": r["user_id"], "name": r["first_name"], "username": r["username"], "balance": r["usd_milli"], "joined": r["joined_at"]} for r in users]})

async def mini_admin_user_detail(request):
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
    s_map = {"MK": 0, "NP": 0, "BASHA": 0, "SLVN": 0}
    for s in (stats or []): s_map[s["provider"]] = s["c"]
    return web.json_response({"user": {"id": u["user_id"], "name": u["first_name"], "username": u["username"], "balance": u["usd_milli"], "joined": u["joined_at"]}, "stats": s_map, "orders": [{"id": r["id"], "provider": r["provider"], "phone": r["phone"], "status": r["status"], "date": r["created_at"]} for r in (orders or [])], "current_page": page, "total_pages": total_pages})

async def mini_admin_user_action(request):
    if not mini_admin_guard(request): return web.json_response({"error": "Forbidden"}, status=403)
    uid = int(request.match_info["uid"])
    body = await request.json()
    action = body.get("action")
    
    if action == "bonus":
        amt = int(float(body.get("amount", 0)) * 1000)
        if amt <= 0: return web.json_response({"error": "Số tiền không hợp lệ"}, status=400)
        
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Chấp nhận", callback_data=f"admin_bonus_accept_{amt}"),
            InlineKeyboardButton(text="❌ Hủy", callback_data=f"admin_bonus_reject_{amt}")
        ]])
        try:
            await bot.send_message(uid, f"🎁 <b>Bạn nhận được tiền từ Admin!</b>\n\nSố tiền: <b>${amt/1000:.3f}</b>\nBấm chấp nhận để cộng vào số dư tài khoản.", reply_markup=kb)
            return web.json_response({"ok": True, "msg": "Đã gửi thông báo cho user!"})
        except Exception as e:
            return web.json_response({"error": f"Không thể gửi tin nhắn: {str(e)}"}, status=400)
            
    elif action == "deduct":
        amt = int(float(body.get("amount", 0)) * 1000)
        if amt <= 0: return web.json_response({"error": "Số tiền không hợp lệ"}, status=400)
        u = await get_user(uid)
        if not u or u["usd_milli"] < amt:
            return web.json_response({"error": "Số dư của user không đủ để trừ!"}, status=400)
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
        if diff != 0:
            await change_usd(uid, diff, "ADMIN_SET", "Admin adjusted balance")
        return web.json_response({"ok": True, "msg": f"Đã cập nhật số dư thành ${min_val/1000:.3f}!"})
        
    return web.json_response({"error": "Action không hợp lệ"}, status=400)

async def mini_admin_broadcast_radar(request):
    if not mini_admin_guard(request): return web.json_response({"error": "Forbidden"}, status=403)
    body = await request.json()
    platform = body.get("platform", "All")
    custom_msg = body.get("message", "").strip()
    image_b64 = body.get("image_b64", "").strip()

    text_content = custom_msg if custom_msg else f"🚨 <b>THÔNG BÁO RADAR OTP CAO</b>\n\nNền tảng đang có tỷ lệ nhận OTP cao: <b>{platform}</b>\nNhanh tay vào ứng dụng lấy số ngay nào anh em!"

    photo_bytes = None
    if image_b64:
        try:
            import base64
            header, encoded = image_b64.split(",", 1)
            photo_bytes = base64.b64decode(encoded)
        except: pass

    users = await db_exec("SELECT user_id FROM users", fetch="all")
    sent = 0
    for row in users or []:
        try:
            if photo_bytes:
                await bot.send_photo(row["user_id"], photo=BufferedInputFile(photo_bytes, filename="radar.jpg"), caption=text_content)
            else:
                await bot.send_message(row["user_id"], text_content)
            sent += 1
            await asyncio.sleep(0.05)
        except: pass

    return web.json_response({"ok": True, "msg": f"Đã gửi thông báo Radar đến {sent} user!"})

async def mini_admin_cmd(request):
    if not mini_admin_guard(request): return web.json_response({"error": "Forbidden"}, status=403)
    try:
        body = await request.json()
        cmd = body.get("cmd")
    except Exception:
        return web.json_response({"ok": True, "msg": "Invalid command payload"})
        
    try:
        if cmd == "pollnow":
            if not _mk_poller: return web.json_response({"ok": True, "msg": "Poller not running"})
            c, n, err = await _mk_poller._poll_once()
            if err: return web.json_response({"ok": True, "msg": f"Lỗi khi Poll OTP: {err}"})
            return web.json_response({"ok": True, "msg": f"Checked: {c} đơn.\nNew OTPs: {n}\nTrạng thái: OK"})
        elif cmd == "health":
            pending = await db_exec("SELECT COUNT(*) FROM orders WHERE status='PENDING'", fetch='one')
            pending_count = pending[0] if pending and len(pending) > 0 else 0
            poller = "OFF" if not _mk_poller else f"ON ({_mk_poller.interval}s)"
            return web.json_response({"ok": True, "msg": f"DB: Turso\nMK Key: {'OK' if MK_API_KEY else 'MISSING'}\nNP Key: {'OK' if NP_API_KEY else 'MISSING'}\nPending Orders: {pending_count}\nPoller: {poller}"})
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
    except Exception as e:
        return web.json_response({"ok": True, "msg": f"Lỗi thực thi: {str(e)}"})

async def mini_admin_maintenance(request):
    if not mini_admin_guard(request): return web.json_response({"error": "Forbidden"}, status=403)
    body = await request.json(); action = body.get("action")
    if action == "enable":
        await set_setting("maintenance", "off")
        return web.json_response({"ok": True, "msg": "Đã TẮT bảo trì. Bot hoạt động bình thường."})
    elif action == "disable":
        message = body.get("message", ""); image_b64 = body.get("image_b64", "")
        await set_setting("maintenance", "on"); await set_setting("maint_message", message); await set_setting("maint_image", image_b64)
        users = await db_exec("SELECT user_id FROM users", fetch="all"); sent = 0
        photo_bytes = None
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
    body = await request.json(); country = body.get("country")
    if country == "ALL": await db_exec("DELETE FROM basha_numbers")
    else: await db_exec("DELETE FROM basha_numbers WHERE country=?", (country,))
    return web.json_response({"ok": True})

async def mini_admin_wd_action(request):
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

async def mini_mk_ranges(request):
    # API v3 /access_list
    data, err = await api_request("GET", "access_list", params={"limit": 1000}, api_type="MK")
    countries = []
    if not err and data and isinstance(data, dict):
        items = data.get("data", {}).get("items") or data.get("items") or []
        if items:
            c_map = {}
            for item in items:
                c_name = item.get("country") or item.get("country_name")
                r_val = item.get("range") or item.get("prefix") or item.get("code")
                if c_name and r_val:
                    c_map.setdefault(c_name, []).append(str(r_val))
            for c_name, ranges in c_map.items():
                countries.append({"name": c_name, "range": ranges[0], "flag": get_country_flag(c_name)})
    if not countries:
        countries = [{"name": k, "range": v, "flag": get_country_flag(k)} for k, v in FALLBACK_COUNTRIES.items()]
    return web.json_response({"countries": countries})

async def mini_np_services(request):
    data, err = await api_request("GET", "services", api_type="NP")
    srvs = data.get("services", []) if data and not err else []
    return web.json_response({"services": [{"name": s["name"], "key": s["name"], "count": s["count"]} for s in srvs if s.get("count", 0) > 0]})

async def mini_np_countries(request):
    data, err = await api_request("GET", "countries", params={"service": request.match_info["service"]}, api_type="NP")
    countries = data.get("countries", []) if data and not err else []
    return web.json_response({"countries": [{"code": c["name"], "name": ISO_MAP.get(c["name"], c["name"]), "count": c["count"]} for c in countries if c.get("count", 0) > 0]})

async def mini_bs_countries(request):
    rows = await db_exec("SELECT country, flag, COUNT(*) as c FROM basha_numbers GROUP BY country, flag", fetch="all")
    return web.json_response({"countries": [{"name": r["country"], "flag": r["flag"], "count": r["c"]} for r in rows] if rows else []})

async def mini_slvn_countries(request):
    data, err = await api_request("GET", "available-countries", params={"service": "any"}, api_type="SLVN")
    if err or not data: return web.json_response({"countries": []})
    return web.json_response({"countries": [{"name": c.get("country"), "code": c.get("countryCode"), "flag": c.get("flag"), "tag": c.get("tag"), "rate": c.get("rateUsd")} for c in data.get("data", [])]})

async def web_server():
    app = web.Application(middlewares=[mini_auth_middleware], client_max_size=10 * 1024 * 1024)
    
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
    app.router.add_post('/api/mini/admin/users/{uid}/action', mini_admin_user_action)
    app.router.add_post('/api/mini/admin/broadcast/radar', mini_admin_broadcast_radar)
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

async def main():
    global BOT_USERNAME, _mk_poller
    try: 
        me = await bot.get_me(); BOT_USERNAME = me.username; await set_bot_commands()
        if WEBAPP_URL.startswith("https://"):
            await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="FAST IVAS", web_app=WebAppInfo(url=WEBAPP_URL)))
    except Exception as e: logger.error(f"Error setting menu: {e}")
    
    await init_db()
    setup_handlers(dp, bot, WEBAPP_URL, ADMIN_ID)
    
    asyncio.create_task(web_server())
    _mk_poller = MkOtpPoller(bot, OTP_GROUP_ID)
    asyncio.create_task(_mk_poller.run_forever())
    
    logger.info("FAST IVAS starting...")
    await dp.start_polling(bot, drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
