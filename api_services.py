import os
import json
import asyncio
import aiohttp
import logging
import re
from datetime import timedelta
from database import db_exec, get_user, change_usd, now_text, now, mask_phone, safe, get_country_flag, detect_otp_platform

logger = logging.getLogger("FAST_IVAS")

MK_API_KEY     = os.getenv("MK_API_KEY", "badacaa33d287233567a49db").strip()
MK_API_BASE    = "https://mknetworkbd.com/api/v3/public"

NP_API_KEY     = os.getenv("NP_API_KEY", "np_live_lrRtdKcOeg-syi8UCpmaA_idYmBZY0zbpwl5P--gF-g").strip()
NP_API_BASE    = "https://numberpanel.tech/api"

BASHA_API_KEY  = os.getenv("BASHA_API_KEY", "").strip()
BASHA_API_BASE = "https://basha.cc/api"

SLVN_API_KEY   = os.getenv("SLVN_API_KEY", "").strip()
SLVN_API_BASE  = "https://slvirtualnumber.com/api/v1/developer"

REWARD_MILLI_PER_OTP = 2

async def api_request(method: str, endpoint: str, payload: dict = None, params: dict = None, api_type: str = "MK") -> tuple:
    base_urls = {"MK": MK_API_BASE, "NP": NP_API_BASE, "BASHA": BASHA_API_BASE, "SLVN": SLVN_API_BASE}
    keys = {"MK": MK_API_KEY, "NP": NP_API_KEY, "BASHA": BASHA_API_KEY, "SLVN": SLVN_API_KEY}
    
    url = base_urls.get(api_type, "")
    key = keys.get(api_type, "")
    if not url or not key:
        return None, f"API key cho {api_type} chưa được cấu hình."
    
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if str(api_type).upper() == "MK":
        headers["mknetwork-key"] = key
    else:
        headers["Authorization"] = f"Bearer {key}"
        
    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method, url + "/" + endpoint.lstrip("/"),
                json=payload, params=params, headers=headers,
                timeout=aiohttp.ClientTimeout(total=25)
            ) as resp:
                text = await resp.text()
                if resp.status in (401, 403):
                    return None, f"Lỗi xác thực API ({resp.status})."
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    return None, f"Phản hồi không phải JSON (HTTP {resp.status})."
                meta = data.get("meta", {})
                if meta.get("code") and meta.get("code") != 200:
                    return None, data.get("message") or meta.get("status") or "Lỗi API."
                return data, None
    except asyncio.TimeoutError:
        return None, "Timeout – API không phản hồi sau 25s."
    except Exception as e:
        return None, f"Lỗi mạng: {str(e)}"

class MkOtpPoller:
    def __init__(self, bot, otp_group_id):
        self.bot = bot
        self.otp_group_id = otp_group_id
        self.interval = 10
        self._consecutive_errors = 0

    async def _process_otp(self, row, otp, sms):
        reward = REWARD_MILLI_PER_OTP
        if row.get("provider") in ["NP", "SLVN"]: reward = 0; platform = row.get("operator", "Other").capitalize()
        elif row.get("provider") == "BASHA": reward = 0; platform = "Basha Service"
        else: platform = detect_otp_platform(sms)
        
        db = await asyncio.get_running_loop().run_in_executor(None, __import__('database').open_db)
        try:
            db.execute("BEGIN IMMEDIATE")
            chk = db.execute("SELECT status FROM orders WHERE id=?", (row["id"],)).fetchone()
            if not chk or chk[0] != "PENDING": db.rollback(); return False
            db.execute("UPDATE orders SET status='COMPLETED', otp_code=?, full_sms=?, platform=?, reward_milli=?, updated_at=? WHERE id=?", (otp, sms, platform, reward, now_text(), row["id"])); db.commit()
        except Exception: db.rollback(); return False
        finally: db.close()
        
        if reward > 0:
            await change_usd(row["user_id"], reward, "OTP_REWARD", f"Reward OTP #{row['id']}")
            
        u = await get_user(row["user_id"])
        user_name = u["first_name"] if u else "User"
        flag = get_country_flag(row['country'])
        
        user_text = f"📱 <b>{platform}</b> 🌍 {row['country']}\n<b>OTP Received</b>\n👤 User: <a href='tg://user?id={row['user_id']}'>{user_name}</a>\n\n🔒 <b>OTP :</b> <code>{otp}</code>\n📞 <code>{row['phone']}</code>"
        await self.bot.send_message(row["user_id"], user_text)
        
        if self.otp_group_id:
            group_text = f"📱 <b>{platform}</b> 🌍 {row['country']} {flag}\n<b>OTP Received</b>\n👤 User: <a href='tg://user?id={row['user_id']}'>{user_name}</a>\n\n🔒 <b>OTP :</b> <code>{otp}</code>\n📞 <code>{mask_phone(row['phone'])}</code>"
            if sms: group_text += f"\n<blockquote>💬 {safe(sms, 300)}</blockquote>"
            try: await self.bot.send_message(self.otp_group_id, group_text)
            except: pass
        return True

    async def _poll_once(self):
        rows = await db_exec("SELECT * FROM orders WHERE status='PENDING' LIMIT 100", fetch="all")
        if not rows: return 0, 0, None
        checked = new_otp = 0
        error_msg = None
        
        for r in rows:
            if r["provider"] == "MK":
                checked += 1
                data, err = await api_request("POST", "check/status", {"request_ids": [int(r["request_id"])]})
                if err: error_msg = err
                elif data:
                    inner = data.get("data", {})
                    res = inner.get("results", [])
                    if res and res[0].get("status") == "success":
                        if await self._process_otp(r, res[0]["otp_code"], res[0].get("full_sms", "")): new_otp += 1
            elif r["provider"] == "NP":
                checked += 1
                data, err = await api_request("GET", "latest_otp", params={"number": r["phone"]}, api_type="NP")
                if err: error_msg = err
                elif data and data.get("has_otp"):
                    if await self._process_otp(r, data["otp_code"], f"OTP: {data['otp_code']}"): new_otp += 1
            elif r["provider"] == "BASHA":
                checked += 1
                data, err = await api_request("POST", "legacy/get-last-sms", {"number": r["phone"]}, api_type="BASHA")
                if err: error_msg = err
                elif data and data.get("message"):
                    otp_match = re.search(r'\b(\d{4,8})\b', data["message"])
                    if otp_match and await self._process_otp(r, otp_match.group(1), data["message"]): new_otp += 1
            elif r["provider"] == "SLVN":
                checked += 1
                data, err = await api_request("GET", f"check-otp/{r['request_id']}", api_type="SLVN")
                if err: error_msg = err
                elif data and data.get("status") == "success":
                    inner = data.get("data", {})
                    if inner.get("status") == "RECEIVED":
                        if await self._process_otp(r, inner.get("otpCode"), inner.get("fullSms", "")): new_otp += 1
        return checked, new_otp, error_msg

    async def run_forever(self):
        while True:
            try: 
                await self._poll_once()
            except Exception as e: logger.error(f"Poller error: {e}")
            await asyncio.sleep(10)
