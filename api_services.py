# File: api_services.py

import os
import aiohttp
import asyncio
import logging
import re
from database import db_exec, get_country_flag, get_network_icon, detect_otp_platform, now_text

logger = logging.getLogger("FAST_IVAS")

MK_API_KEY = os.getenv("MK_API_KEY", "").strip()
NP_API_KEY = os.getenv("NP_API_KEY", "").strip()
SLVN_API_KEY = os.getenv("SLVN_API_KEY", "").strip()

MK_BASE_URL = "https://mknetworkbd.com/api/v1/"
NP_BASE_URL = "https://api.nonvoip.com/v1/" # Hoặc endpoint NP của bro
SLVN_BASE_URL = "https://api.slvn.io/v1/"

async def api_request(method, endpoint, params=None, data=None, api_type="MK"):
    base_url = MK_BASE_URL
    api_key = MK_API_KEY
    if api_type == "NP":
        base_url = NP_BASE_URL
        api_key = NP_API_KEY
    elif api_type == "SLVN":
        base_url = SLVN_BASE_URL
        api_key = SLVN_API_KEY

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    url = base_url + endpoint.lstrip("/")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.request(method, url, headers=headers, params=params, json=data, timeout=20) as resp:
                if resp.content_type == "application/json":
                    res_json = await resp.json()
                    return res_json, None
                text = await resp.text()
                return {"text": text}, None
        except Exception as e:
            return None, str(e)

class MkOtpPoller:
    def __init__(self, bot, group_id, interval=4):
        self.bot = bot
        self.group_id = group_id
        self.interval = interval

    async def run_forever(self):
        logger.info("MkOtpPoller started successfully.")
        while True:
            try:
                await self._poll_once()
            except Exception as e:
                logger.error(f"Error in MkOtpPoller: {e}")
            await asyncio.sleep(self.interval)

    async def _poll_once(self):
        pending_orders = await db_exec("SELECT * FROM orders WHERE status='PENDING' AND provider='MK'", fetch="all")
        if not pending_orders:
            return 0, 0, None

        data, err = await api_request("GET", "getnum/active", params={"limit": 200}, api_type="MK")
        if err or not data:
            return 0, 0, err

        active_items = data.get("data", {}).get("items") or data.get("items") or []
        active_map = {}
        for item in active_items:
            rid = str(item.get("request_id") or item.get("id") or "")
            if rid:
                active_map[rid] = item

        checked = 0
        new_otps = 0

        for order in pending_orders:
            checked += 1
            rid = str(order["request_id"])
            item = active_map.get(rid)

            if not item:
                continue

            status = str(item.get("status", "")).upper()
            sms_text = item.get("message") or item.get("sms") or item.get("text") or ""
            otp_code = item.get("otp") or item.get("code") or ""

            if not otp_code and sms_text:
                match = re.search(r'\b\d{4,8}\b', sms_text)
                if match:
                    otp_code = match.group(0)

            if status in ["COMPLETED", "SUCCESS"] or otp_code or (sms_text and "otp" in sms_text.lower()):
                if not otp_code:
                    otp_code = "SUCCESS"

                platform = detect_otp_platform(sms_text)
                
                await db_exec(
                    "UPDATE orders SET status='COMPLETED', otp_code=?, full_sms=?, platform=?, updated_at=? WHERE id=?",
                    (str(otp_code), str(sms_text), str(platform), now_text(), order["id"])
                )
                new_otps += 1

                user_id = order["user_id"]
                phone = order["phone"]
                country = order["country"]
                flag = get_country_flag(country)
                icon = get_network_icon(platform)

                user_msg = (
                    f"🎉 <b>ĐÃ NHẬN MÃ OTP THÀNH CÔNG!</b>\n\n"
                    f"📱 Số điện thoại: <code>{phone}</code>\n"
                    f"🌍 Quốc gia: {flag} {country}\n"
                    f"🌐 Nền tảng: {icon} <b>{platform}</b>\n"
                    f"🔑 Mã OTP: <code>{otp_code}</code>\n\n"
                    f"💬 Nội dung SMS:\n<code>{sms_text}</code>"
                )

                try:
                    await self.bot.send_message(user_id, user_msg)
                except Exception as e:
                    logger.error(f"Failed to send OTP to user {user_id}: {e}")

                if self.group_id:
                    group_msg = (
                        f"⚡ <b>NEW OTP CAPTURED (FAST IVAS)</b>\n\n"
                        f"📱 Phone: <code>{phone}</code>\n"
                        f"🌍 Country: {flag} {country}\n"
                        f"🌐 Platform: {icon} <b>{platform}</b>\n"
                        f"🔑 OTP: <code>{otp_code}</code>\n"
                        f"👤 User ID: <code>{user_id}</code>\n"
                        f"💬 SMS: <code>{sms_text}</code>"
                    )
                    try:
                        await self.bot.send_message(self.group_id, group_msg)
                    except Exception as e:
                        logger.error(f"Failed to send OTP to group {self.group_id}: {e}")

            elif status in ["EXPIRED", "CANCELLED", "FAILED"]:
                await db_exec("UPDATE orders SET status=?, updated_at=? WHERE id=?", (status, now_text(), order["id"]))

        return checked, new_otps, None
        
