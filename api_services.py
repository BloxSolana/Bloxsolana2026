import os
import json
import asyncio
import aiohttp
import logging
import re
from datetime import timedelta
from database import db_exec, get_user, change_usd, now_text, now, mask_phone, safe, get_country_flag, detect_otp_platform, get_network_icon

logger = logging.getLogger("FAST_IVAS")

MK_API_KEY     = os.getenv("MK_API_KEY", "badacaa33d287233567a49db").strip()
MK_API_BASE    = "https://mknetworkbd.com/api/v3/public"
NP_API_KEY     = os.getenv("NP_API_KEY", "np_live_lrRtdKcOeg-syi8UCpmaA_idYmBZY0zbpwl5P--gF-g").strip()
BASHA_API_KEY  = os.getenv("BASHA_API_KEY", "").strip()
SLVN_API_KEY   = os.getenv("SLVN_API_KEY", "").strip()

async def api_request(method: str, endpoint: str, payload: dict = None, params: dict = None, api_type: str = "MK") -> tuple:
    base_urls = {"MK": MK_API_BASE, "NP": "https://numberpanel.tech/api", "BASHA": "https://basha.cc/api", "SLVN": "https://slvirtualnumber.com/api/v1/developer"}
    keys = {"MK": MK_API_KEY, "NP": NP_API_KEY, "BASHA": BASHA_API_KEY, "SLVN": SLVN_API_KEY}
    
    url = base_urls.get(api_type, "")
    key = keys.get(api_type, "")
    if not url or not key: return None, f"API key cho {api_type} chưa được cấu hình."
    
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if str(api_type).upper() == "MK": headers["mknetwork-key"] = key
    else: headers["Authorization"] = f"Bearer {key}"
        
    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url + "/" + endpoint.lstrip("/"), json=payload, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=25)) as resp:
                text = await resp.text()
                if resp.status in (401, 403): return None, f"Lỗi xác thực API ({resp.status})."
                try: data = json.loads(text)
                except json.JSONDecodeError: return None, f"Phản hồi không phải JSON (HTTP {resp.status})."
                meta = data.get("meta", {})
                if meta.get("code") and meta.get("code") != 200: return None, data.get("message") or meta.get("status") or "Lỗi API."
                return data, None
    except asyncio.TimeoutError: return None, "Timeout – API không phản hồi sau 25s."
    except Exception as e: return None, f"Lỗi mạng: {str(e)}"

class MkOtpPoller:
    def __init__(self, bot_instance, group_id, interval=3):
        self.bot = bot_instance
        self.group_id = int(group_id) if group_id else 0
        self.interval = interval
        self.is_running = False
        self._consecutive_errors = 0

    async def run_forever(self):
        self.is_running = True
        logger.info("MkOtpPoller started for Real-Time OTP checking...")
        while self.is_running:
            try: await self._poll_once()
            except Exception as e: logger.error(f"Poller error: {e}")
            await asyncio.sleep(self.interval)

    async def _poll_once(self):
        try:
            # Xử lý đơn MK (Gọi 1 lần batch API)
            pending_mk = await db_exec("SELECT * FROM orders WHERE status='PENDING' AND provider='MK' LIMIT 100", fetch="all")
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
                                otp_code = res.get("otp_code") or res.get("otp") or res.get("code")
                                full_sms = res.get("full_sms") or res.get("message") or ""
                                if (otp_code or full_sms) and str(res.get("status", "")).lower() in ["success", "completed", ""]:
                                    if not otp_code and full_sms:
                                        match = re.search(r'\b\d{4,8}\b', full_sms)
                                        if match: otp_code = match.group(0)
                                    if otp_code:
                                        await self._process_otp(order, otp_code, full_sms)

            # Xử lý đơn NP (Gọi riêng lẻ hoặc theo endpoint tùy nhà cung cấp)
            pending_np = await db_exec("SELECT * FROM orders WHERE status='PENDING' AND provider='NP' LIMIT 50", fetch="all")
            for r in (pending_np or []):
                data, err = await api_request("GET", "latest_otp", params={"number": r["phone"]}, api_type="NP")
                if not err and data and data.get("has_otp"):
                    await self._process_otp(r, data["otp_code"], data.get("message", f"OTP: {data['otp_code']}"))

            # (Bỏ qua BASHA và SLVN trong poller mẫu này để code gọn, nếu cần bro thêm logic tương tự như trên)
            return 0, 0, None
        except Exception as e:
            logger.error(f"Poller internal error: {e}")
            return 0, 0, str(e)

    async def _process_otp(self, row, otp, sms):
        plat = detect_otp_platform(sms)
        icon = get_network_icon(plat)
        flag = get_country_flag(row['country'])
        phone = row['phone']
        uid = row['user_id']
        
        # 1. Cập nhật Database
        db = await asyncio.get_running_loop().run_in_executor(None, __import__('database').open_db)
        try:
            db.execute("BEGIN IMMEDIATE")
            chk = db.execute("SELECT status FROM orders WHERE id=?", (row["id"],)).fetchone()
            if not chk or chk[0] != "PENDING": db.rollback(); return False
            db.execute("UPDATE orders SET status='COMPLETED', otp_code=?, full_sms=?, platform=?, updated_at=? WHERE id=?", (otp, sms, plat, now_text(), row["id"]))
            db.commit()
        except Exception: db.rollback(); return False
        finally: db.close()

        # 2. Gửi thông báo cho User
        user_text = (
            f"🎉 <b>ĐÃ NHẬN ĐƯỢC MÃ OTP!</b>\n\n"
            f"📱 Số: <code>{phone}</code>\n"
            f"{flag} Quốc gia: <b>{row['country']}</b>\n"
            f"{icon} Nền tảng: <b>{plat}</b>\n"
            f"🔑 Mã OTP: <code><b>{otp}</b></code>\n"
            f"💬 Nội dung: <i>{safe(sms, 300)}</i>"
        )
        try: await self.bot.send_message(uid, user_text)
        except: pass

        # 3. Gửi thông báo Real-Time đến OTP_GROUP_ID
        if self.group_id and self.group_id != 0:
            group_text = (
                f"⚡ <b>FAST IVAS - REAL-TIME OTP</b>\n\n"
                f"📱 Số: <code>{phone}</code>\n"
                f"{flag} Quốc gia: <b>{row['country']}</b>\n"
                f"{icon} Nền tảng: <b>{plat}</b>\n"
                f"🔑 Mã OTP: <code>{otp}</code>\n"
                f"💬 Nội dung: <i>{safe(sms, 300)}</i>"
            )
            try: await self.bot.send_message(self.group_id, group_text)
            except: pass
        return True
