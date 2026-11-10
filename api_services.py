# File: api_services.py

import os
import logging
import aiohttp
import asyncio
import re
from datetime import datetime
from database import open_db, db_exec, get_user, change_usd, now_text, detect_otp_platform, get_country_flag, get_network_icon

logger = logging.getLogger("FAST_IVAS")

MK_API_KEY   = os.getenv("MK_API_KEY", "").strip()
NP_API_KEY   = os.getenv("NP_API_KEY", "").strip()
SLVN_API_KEY = os.getenv("SLVN_API_KEY", "").strip()

async def api_request(method, endpoint, json_data=None, params=None, api_type="MK"):
    url = ""
    headers = {}
    if api_type == "MK":
        url = f"https://api.number1.vn/v1/{endpoint}"
        headers = {"Authorization": f"Bearer {MK_API_KEY}", "Content-Type": "application/json"}
    elif api_type == "NP":
        url = f"https://api.number2.vn/v1/{endpoint}"
        headers = {"Authorization": f"Bearer {NP_API_KEY}", "Content-Type": "application/json"}
    elif api_type == "SLVN":
        url = f"https://api.slvn.vn/v1/{endpoint}"
        headers = {"Authorization": f"Bearer {SLVN_API_KEY}", "Content-Type": "application/json"}
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.request(method, url, json=json_data, params=params, headers=headers, timeout=20) as resp:
                text = await resp.text()
                try:
                    data = await resp.json()
                except:
                    data = {"raw": text}
                if resp.status >= 400:
                    return None, f"HTTP {resp.status}: {text}"
                return data, None
        except Exception as e:
            return None, str(e)

class MkOtpPoller:
    def __init__(self, bot, group_id, interval=3):
        self.bot = bot
        self.group_id = group_id
        self.interval = interval
        self.is_running = False

    async def run_forever(self):
        self.is_running = True
        logger.info("MkOtpPoller started for Real-Time OTP checking...")
        while self.is_running:
            try:
                await self._poll_once()
            except Exception as e:
                logger.error(f"Poller error: {e}")
            await asyncio.sleep(self.interval)

    async def _poll_once(self):
        # Lấy danh sách đơn hàng đang PENDING của provider MK
        pending_orders = await db_exec("SELECT id, user_id, request_id, phone, country FROM orders WHERE status='PENDING' AND provider='MK'", fetch="all")
        if not pending_orders:
            return 0, 0, None

        checked_count = len(pending_orders)
        new_otp_count = 0

        for order in pending_orders:
            oid = order["id"]
            uid = order["user_id"]
            req_id = order["request_id"]
            phone = order["phone"]
            country = order["country"]

            # Gọi API kiểm tra trạng thái đơn hàng MK
            data, err = await api_request("GET", "getnum/status", params={"request_id": req_id}, api_type="MK")
            if err or not data:
                continue

            resp_data = data.get("data", data)
            status = str(resp_data.get("status", "")).upper()
            otp_code = resp_data.get("otp") or resp_data.get("code") or resp_data.get("otp_code")
            full_sms = resp_data.get("message") or resp_data.get("sms") or resp_data.get("full_sms") or ""

            if otp_code or status in ["COMPLETED", "SUCCESS"] or full_sms:
                if not otp_code and full_sms:
                    match = re.search(r'\b\d{4,8}\b', full_sms)
                    if match:
                        otp_code = match.group(0)

                if otp_code:
                    plat = detect_otp_platform(full_sms)
                    icon = get_network_icon(plat)
                    flag = get_country_flag(country)

                    # Cập nhật trạng thái đơn hàng thành COMPLETED trong CSDL
                    await db_exec("UPDATE orders SET status='COMPLETED', otp_code=?, full_sms=?, platform=?, updated_at=? WHERE id=?", 
                                  (str(otp_code), str(full_sms), plat, now_text(), oid))
                    
                    new_otp_count += 1

                    # Gửi thông báo real-time trực tiếp về Group Telegram
                    group_text = (
                        f"⚡ <b>FAST IVAS - REAL-TIME OTP RECEIVED</b>\n\n"
                        f"📱 Số điện thoại: <code>{phone}</code>\n"
                        f"{flag} Quốc gia: <b>{country}</b>\n"
                        f"{icon} Nền tảng: <b>{plat}</b>\n"
                        f"🔑 Mã OTP: <code>{otp_code}</code>\n"
                        f"💬 Nội dung SMS: <i>{full_sms}</i>"
                    )
                    try:
                        await self.bot.send_message(self.group_id, group_text)
                    except Exception as e:
                        logger.error(f"Failed to send OTP to group: {e}")

        return checked_count, new_otp_count, None
        
