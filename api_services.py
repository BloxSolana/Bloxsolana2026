# File: api_services.py

import os
import logging
import aiohttp
import asyncio
import re
from datetime import datetime
from database import open_db, db_exec, get_user, change_usd, now_text, detect_otp_platform, get_country_flag, get_network_icon

logger = logging.getLogger("FAST_IVAS")

MK_API_KEY   = os.getenv("MK_API_KEY", "badacaa33d287233567a49db").strip()
MK_API_URL   = os.getenv("MK_API_URL", "https://mknetworkbd.com/api/v3/public").strip()
NP_API_KEY   = os.getenv("NP_API_KEY", "").strip()
SLVN_API_KEY = os.getenv("SLVN_API_KEY", "").strip()

async def api_request(method, endpoint, json_data=None, params=None, api_type="MK"):
    url = ""
    headers = {}
    if api_type == "MK":
        base_url = MK_API_URL.rstrip('/')
        url = f"{base_url}/{endpoint.lstrip('/')}"
        headers = {"mknetwork-key": MK_API_KEY, "Content-Type": "application/json"}
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
        logger.info("MkOtpPoller started for Real-Time OTP checking (API v3 batch)...")
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

        request_ids_map = {}
        for order in pending_orders:
            try:
                rid = int(order["request_id"])
                request_ids_map[rid] = order
            except:
                continue

        if not request_ids_map:
            return 0, 0, None

        req_ids_list = list(request_ids_map.keys())
        checked_count = 0
        new_otp_count = 0

        # API v3 check status theo dạng batch (tối đa 100 ID mỗi lần gọi POST /check/status)
        for i in range(0, len(req_ids_list), 100):
            chunk = req_ids_list[i:i+100]
            checked_count += len(chunk)
            
            data, err = await api_request("POST", "check/status", {"request_ids": chunk}, api_type="MK")
            if err or not data:
                continue

            resp_data = data.get("data", {})
            results = resp_data.get("results", [])
            
            for res in results:
                rid = res.get("request_id")
                if rid not in request_ids_map:
                    continue
                
                order = request_ids_map[rid]
                oid = order["id"]
                phone = order["phone"]
                country = order["country"]
                
                status = str(res.get("status", "")).lower()
                otp_code = res.get("otp_code") or res.get("otp") or res.get("code")
                full_sms = res.get("full_sms") or res.get("message") or ""

                if otp_code or status in ["success", "completed"] or full_sms:
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
        
