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

async def api_request(method, endpoint, payload=None, params=None, api_type="MK"):
    headers = {"Accept": "application/json"}
    if api_type == "MK": 
        if not MK_API_KEY: return None, "Missing MK_API_KEY on server."
        headers["mknetwork-key"] = MK_API_KEY; base = MK_API_BASE
    elif api_type == "NP": 
        if not NP_API_KEY: return None, "Missing NP_API_KEY on server."
        headers["Authorization"] = f"Bearer {NP_API_KEY}"; base = NP_API_BASE
    elif api_type == "BASHA": 
        if not BASHA_API_KEY: return None, "Missing BASHA_API_KEY on server."
        headers["Authorization"] = f"Bearer {BASHA_API_KEY}"; base = BASHA_API_BASE
    elif api_type == "SLVN": 
        if not SLVN_API_KEY: return None, "Missing SLVN_API_KEY on server."
        headers["x-api-key"] = SLVN_API_KEY; base = SLVN_API_BASE
    
    if payload is not None: headers["Content-Type"] = "application/json"
    url = f"{base}/{endpoint.lstrip('/')}"
    timeout = aiohttp.ClientTimeout(total=25)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.request(method, url, headers=headers, json=payload, params=params) as r:
                raw = await r.text()
                try: data = json.loads(raw)
                except json.JSONDecodeError: data = {"response": raw[:1000]}
                if r.status >= 400: 
                    err_msg = data.get("message", raw) if isinstance(data, dict) else raw
                    return None, f"API Error {r.status}: {err_msg}"
                return data, None
    except asyncio.TimeoutError: return None, "Connection timeout."
    except Exception as e: return None, str(e)

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
