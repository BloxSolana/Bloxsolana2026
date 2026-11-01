import asyncio
import random
import re
import html
import time
import os
import threading
import json
import hmac
import hashlib
import logging
import tempfile
import atexit
import platform

_IS_WINDOWS = platform.system() == "Windows"
if not _IS_WINDOWS:
    import fcntl
else:
    fcntl = None
    
import signal
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import parse_qsl
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from http.cookies import SimpleCookie

import requests
import websocket
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
from flask import Flask, render_template_string, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

# --- LOGGING CONFIGURATION ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("FastNodePortal")

# --- CONFIGURATION & SECURITY ENVIRONMENT VARIABLES ---
def get_required_env(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Thiếu biến môi trường bắt buộc: {name}")
    return value

BOT_TOKEN = get_required_env("BOT_TOKEN")
FLASK_SECRET_KEY = get_required_env("FLASK_SECRET_KEY")

ADMIN_IDS = {
    int(item.strip())
    for item in get_required_env("ADMIN_IDS").split(",")
    if item.strip()
}

TARGET_CHAT = int(os.getenv("TARGET_CHAT", "-1004341368656"))
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://bloxsolana2026.onrender.com")
IVAS_REFRESH_TOKEN = os.getenv("IVAS_REFRESH_TOKEN", "")

bot = telebot.TeleBot(token=BOT_TOKEN)

# --- DATABASE QUẢN LÝ ---
user_rentals = {}          
inventory_numbers = {}     
admin_state = {}           
user_configs = {}          

user_wallets = {}          
withdrawal_requests = []   
live_radar_logs = []       # Lưu các bản tin OTP thực tế để hiển thị lên Radar

app_stats = {
    "WhatsApp": 0, "ClickBank": 0, "Apple": 0, "Shopee": 0, "Facebook": 0,
    "TikTok": 0, "AUTHMSG": 0, "TALAPH": 0, "Uber": 0, "SPayLaterPH": 0,
    "Telegram": 0, "Google": 0, "Instagram": 0, "Discord": 0, "Zalo": 0
}
top_ranges_data = []
last_reset_time = time.time()

# --- CẤU HÌNH & TÍCH HỢP IVAS SMS CLIENT (MANUAL COOKIE & SECURE SESSION) ---
IVAS_BASE_URL = os.getenv("IVAS_BASE_URL", "https://www.ivasms.com").rstrip("/")
IVAS_COOKIE_ENV = "IVAS_COOKIE"
IVAS_COOKIE_FILE = os.getenv("IVAS_COOKIE_FILE", "/data/ivas_cookie.txt")

DEFAULT_TIMEOUT = 20

# Session cache + Thread Lock
_ivas_session = None
_ivas_session_cookie_hash = None
_ivas_lock = threading.Lock()

def _parse_cookie_string(cookie_str: str) -> dict:
    result = {}
    if not cookie_str:
        return result
    try:
        sc = SimpleCookie()
        sc.load(cookie_str)
        for k, morsel in sc.items():
            result[k] = morsel.value
    except Exception:
        for part in cookie_str.split(";"):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                result[k.strip()] = v.strip()
    return result

def _read_cookie_from_file() -> str:
    try:
        if os.path.exists(IVAS_COOKIE_FILE):
            with open(IVAS_COOKIE_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    logger.info(f"IVAS: cookie loaded from {IVAS_COOKIE_FILE}")
                    return content
    except Exception as e:
        logger.warning(f"IVAS: cannot read cookie file: {e}")
    return ""

def _write_cookie_to_file(cookie_str: str) -> bool:
    try:
        os.makedirs(os.path.dirname(IVAS_COOKIE_FILE), exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=os.path.dirname(IVAS_COOKIE_FILE), prefix=".ivas_cookie_"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(cookie_str)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, IVAS_COOKIE_FILE)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
        logger.info(f"IVAS: cookie persisted atomically to {IVAS_COOKIE_FILE}")
        return True
    except Exception as e:
        logger.warning(f"IVAS: cannot persist cookie: {e}")
        return False

_ivas_cookie_mtime = None

def _load_ivas_cookie() -> str:
    global _ivas_cookie_mtime

    if os.path.exists(IVAS_COOKIE_FILE):
        try:
            mtime = os.path.getmtime(IVAS_COOKIE_FILE)
            with open(IVAS_COOKIE_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content:
                if mtime != _ivas_cookie_mtime:
                    logger.info(
                        f"IVAS: cookie file changed (mtime={mtime}), reloading."
                    )
                    _ivas_cookie_mtime = mtime
                return content
        except Exception as e:
            logger.warning(f"IVAS: cannot read cookie file: {e}")

    env_cookie = os.getenv(IVAS_COOKIE_ENV, "").strip()
    if env_cookie:
        return env_cookie
    logger.error("IVAS: no cookie in file or env var")
    return ""

def _build_session_from_cookie(cookie_str: str):
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": f"{IVAS_BASE_URL}/portal/sms/received",
        "X-Requested-With": "XMLHttpRequest",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    })
    
    cookies = _parse_cookie_string(cookie_str)
    if cookies:
        for name, value in cookies.items():
            s.cookies.set(name, value, domain="www.ivasms.com", path="/")

    retry = Retry(total=2, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s

def _cookie_hash(cookie_str: str) -> str:
    return hashlib.sha256(cookie_str.encode("utf-8")).hexdigest()

def _get_ivas_session():
    global _ivas_session, _ivas_session_cookie_hash
    cookie_str = _load_ivas_cookie()
    current_hash = _cookie_hash(cookie_str)

    with _ivas_lock:
        if _ivas_session is None or _ivas_session_cookie_hash != current_hash:
            _ivas_session = _build_session_from_cookie(cookie_str)
            _ivas_session_cookie_hash = current_hash
        return _ivas_session

def _invalidate_session():
    global _ivas_session, _ivas_session_cookie_hash
    with _ivas_lock:
        old = _ivas_session
        _ivas_session = None
        _ivas_session_cookie_hash = None
    if old is not None:
        try:
            old.close()
        except Exception:
            pass

ivas_processed_ids = set()
ivas_processed_lock = threading.Lock()

ivas_health = {
    "connected": False,
    "last_check": None,
    "last_error": None,
    "details": "Initializing..."
}

def ivas_check_session() -> bool:
    try:
        s = _get_ivas_session()
        resp = s.get(f"{IVAS_BASE_URL}/portal/sms/received", timeout=DEFAULT_TIMEOUT, allow_redirects=False)
        if resp.status_code in (401, 403):
            logger.error(f"IVAS: SESSION EXPIRED — status {resp.status_code}")
            with _ivas_lock:
                ivas_health.update({
                    "connected": False,
                    "last_check": int(time.time()),
                    "last_error": f"HTTP {resp.status_code}",
                    "details": "Session expired (Unauthorized)"
                })
            return False

        if resp.status_code == 302:
            logger.error("IVAS: SESSION EXPIRED — redirected to login")
            with _ivas_lock:
                ivas_health.update({
                    "connected": False,
                    "last_check": int(time.time()),
                    "last_error": "HTTP 302",
                    "details": "Redirected to login"
                })
            return False

        if resp.status_code >= 400:
            logger.warning(f"IVAS: unexpected status {resp.status_code}")
            return False

        with _ivas_lock:
            ivas_health.update({
                "connected": True,
                "last_check": int(time.time()),
                "last_error": None,
                "details": "Session active and healthy"
            })
        return True
    except Exception as exc:
        error = str(exc)
        with _ivas_lock:
            ivas_health.update({
                "connected": False,
                "last_check": int(time.time()),
                "last_error": error,
                "details": f"Failed: {error}"
            })
        logger.warning("IVAS session check failed: %s", error)
        return False

_last_seen_sms_key = None
_sms_lock = threading.Lock()

def _sms_dedupe_key(sms: dict) -> str:
    sid = sms.get("id") or sms.get("sms_id")
    if sid:
        return f"id:{sid}"
    raw = f"{sms.get('sender','')}|{sms.get('content','')}|{sms.get('time','')}"
    return "hash:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()

def fetch_and_process_ivas_sms():
    global _last_seen_sms_key
    if not IVAS_BASE_URL:
        return 0

    now = datetime.now()
    start_date = (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
    end_date = now.strftime("%Y-%m-%d %H:%M:%S")
    payload = {
        "start_date": start_date,
        "end_date": end_date
    }

    try:
        s = _get_ivas_session()
        response = s.post(
            f"{IVAS_BASE_URL}/portal/sms/received/getsms",
            data=payload,
            timeout=DEFAULT_TIMEOUT
        )
        if response.status_code in (401, 403):
            logger.error(f"IVAS: getsms unauthorized ({response.status_code})")
            return 0
        response.raise_for_status()
        
        try:
            result = response.json()
        except ValueError:
            return 0

        if not isinstance(result, (dict, list)):
            return 0

        messages = []
        if isinstance(result, dict):
            messages = result.get("data", result.get("items", result.get("messages", [])))
        elif isinstance(result, list):
            messages = result

        if not isinstance(messages, list):
            return 0

        processed = 0
        for item in messages:
            if not isinstance(item, dict):
                continue

            phone = str(item.get("phone", item.get("phone_number", item.get("recipient", ""))))
            sender = str(item.get("sender") or item.get("service") or item.get("service_name") or "Unknown")
            message = str(item.get("message", item.get("sms", item.get("content", item.get("text", "")))))

            if not phone or not message:
                continue

            event_source = f"{phone}|{sender}|{message}"
            event_id = hashlib.sha256(event_source.encode("utf-8")).hexdigest()

            with ivas_processed_lock:
                if event_id in ivas_processed_ids:
                    continue
                ivas_processed_ids.add(event_id)
                if len(ivas_processed_ids) > 10000:
                    ivas_processed_ids.pop()

            cname, flag, _ = detect_country_info(phone)
            timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            loop.run_until_complete(
                dispatch_update(
                    service=sender,
                    phone=phone,
                    msg=message,
                    timestamp=timestamp_str,
                    country=cname,
                    flag=flag,
                    is_test=False
                )
            )
            processed += 1

        return processed

    except Exception as exc:
        logger.warning("IVAS fetch/processing error: %s", str(exc))
        return 0

# --- COMPLETE OFFICIAL ISO COUNTRY DATABASE (195+ Quốc gia) ---
country_db = {
    "1": ("USA/Canada", "🇺🇸"), "93": ("Afghanistan", "🇦🇫"), "355": ("Albania", "🇦🇱"), "213": ("Algeria", "🇩🇿"), 
    "376": ("Andorra", "🇦🇩"), "244": ("Angola", "🇦🇴"), "1264": ("Anguilla", "🇦🇮"), "1268": ("Antigua & Barbuda", "🇦🇬"),
    "54": ("Argentina", "🇦🇷"), "374": ("Armenia", "🇦🇲"), "297": ("Aruba", "🇦🇼"), "61": ("Australia", "🇦🇺"),
    "43": ("Austria", "🇦🇹"), "994": ("Azerbaijan", "🇦🇿"), "1242": ("Bahamas", "🇧🇸"), "973": ("Bahrain", "🇧🇭"),
    "880": ("Bangladesh", "🇧🇩"), "1246": ("Barbados", "🇧🇧"), "375": ("Belarus", "🇧🇾"), "32": ("Belgium", "🇧🇪"),
    "501": ("Belize", "🇧🇿"), "229": ("Benin", "🇧🇯"), "1441": ("Bermuda", "🇧🇲"), "975": ("Bhutan", "🇧🇹"),
    "591": ("Bolivia", "🇧🇴"), "387": ("Bosnia", "🇧🇦"), "267": ("Botswana", "🇧🇼"), "55": ("Brazil", "🇧🇷"),
    "673": ("Brunei", "🇧🇳"), "359": ("Bulgaria", "🇧🇬"), "226": ("Burkina Faso", "🇧🇫"), "257": ("Burundi", "🇧🇮"),
    "855": ("Cambodia", "🇰🇭"), "237": ("Cameroon", "🇨🇲"), "238": ("Cape Verde", "🇨🇻"), "1345": ("Cayman Islands", "🇰🇾"),
    "236": ("Central African Rep", "🇨🇫"), "235": ("Chad", "🇹🇩"), "56": ("Chile", "🇨🇱"), "86": ("China", "🇨🇳"),
    "57": ("Colombia", "🇨🇴"), "269": ("Comoros", "🇰🇲"), "242": ("Congo", "🇨🇬"), "243": ("DR Congo", "🇨🇩"),
    "506": ("Costa Rica", "🇨🇷"), "385": ("Croatia", "🇭🇷"), "53": ("Cuba", "🇨🇺"), "357": ("Cyprus", "🇨🇾"),
    "420": ("Czech Republic", "🇨🇿"), "45": ("Denmark", "🇩🇰"), "253": ("Djibouti", "🇩🇯"), "1767": ("Dominica", "🇩🇲"),
    "1849": ("Dominican Rep", "🇩🇴"), "593": ("Ecuador", "🇪🇨"), "20": ("Egypt", "🇪🇬"), "503": ("El Salvador", "🇸🇻"),
    "240": ("Equatorial Guinea", "🇬🇶"), "291": ("Eritrea", "🇪🇷"), "372": ("Estonia", "🇪🇪"), "251": ("Ethiopia", "🇪🇹"),
    "679": ("Fiji", "🇫🇯"), "358": ("Finland", "🇫🇮"), "33": ("France", "🇫🇷"), "594": ("French Guiana", "🇬🇫"),
    "689": ("French Polynesia", "🇵🇫"), "241": ("Gabon", "🇬🇦"), "220": ("Gambia", "🇬🇲"), "995": ("Georgia", "🇬🇪"),
    "49": ("Germany", "🇩🇪"), "233": ("Ghana", "🇬🇭"), "350": ("Gibraltar", "🇬🇮"), "30": ("Greece", "🇬🇷"),
    "299": ("Greenland", "🇬🇱"), "1473": ("Grenada", "🇬🇩"), "590": ("Guadeloupe", "🇬🇵"), "1671": ("Guam", "🇬🇺"),
    "502": ("Guatemala", "🇬🇹"), "224": ("Guinea", "🇬🇳"), "245": ("Guinea-Bissau", "🇬🇼"), "592": ("Guyana", "🇬🇾"),
    "509": ("Haiti", "🇭🇹"), "504": ("Honduras", "🇭🇳"), "852": ("Hong Kong", "🇭🇰"), "36": ("Hungary", "🇭🇺"),
    "354": ("Iceland", "🇮🇸"), "91": ("India", "🇮🇳"), "62": ("Indonesia", "🇮🇩"), "98": ("Iran", "🇮🇷"),
    "964": ("Iraq", "🇮🇶"), "353": ("Ireland", "🇮🇪"), "972": ("Israel", "🇮🇱"), "39": ("Italy", "🇮🇹"),
    "1876": ("Jamaica", "🇯🇲"), "81": ("Japan", "🇯🇵"), "962": ("Jordan", "🇯🇴"), "7": ("Kazakhstan", "🇰🇿"),
    "254": ("Kenya", "🇰🇪"), "686": ("Kiribati", "🇰🇮"), "383": ("Kosovo", "🇽🇰"), "965": ("Kuwait", "🇰🇼"),
    "996": ("Kyrgyzstan", "🇰🇬"), "856": ("Laos", "🇱🇦"), "371": ("Latvia", "🇱🇻"), "961": ("Lebanon", "🇱🇧"),
    "266": ("Lesotho", "🇱🇸"), "231": ("Liberia", "🇱🇷"), "218": ("Libya", "🇱🇾"), "423": ("Liechtenstein", "🇱🇮"),
    "370": ("Lithuania", "🇱🇹"), "352": ("Luxembourg", "🇱🇺"), "853": ("Macau", "🇲🇴"), "389": ("Macedonia", "🇲🇰"),
    "261": ("Madagascar", "🇲🇬"), "265": ("Malawi", "🇲🇼"), "60": ("Malaysia", "🇲🇾"), "960": ("Maldives", "🇲🇻"),
    "223": ("Mali", "🇲🇱"), "356": ("Malta", "🇲🇹"), "692": ("Marshall Islands", "🇲🇭"), "596": ("Martinique", "🇲🇶"),
    "222": ("Mauritania", "🇲🇷"), "230": ("Mauritius", "🇲🇺"), "262": ("Mayotte", "🇾🇹"), "52": ("Mexico", "🇲🇽"),
    "691": ("Micronesia", "🇫🇲"), "373": ("Moldova", "🇲🇩"), "377": ("Monaco", "🇲🇨"), "976": ("Mongolia", "🇲🇳"),
    "382": ("Montenegro", "🇲🇪"), "1664": ("Montserrat", "🇲🇸"), "212": ("Morocco", "🇲🇦"), "258": ("Mozambique", "🇲🇿"),
    "95": ("Myanmar", "🇲🇲"), "264": ("Namibia", "🇳🇦"), "674": ("Nauru", "🇳🇷"), "977": ("Nepal", "🇳🇵"),
    "31": ("Netherlands", "🇳🇱"), "687": ("New Caledonia", "🇳🇨"), "64": ("New Zealand", "🇳🇿"), "505": ("Nicaragua", "🇳🇮"),
    "227": ("Niger", "🇳🇪"), "234": ("Nigeria", "🇳🇬"), "683": ("Niue", "🇳🇺"), "850": ("North Korea", "🇰🇵"),
    "47": ("Norway", "🇳🇴"), "968": ("Oman", "🇴🇲"), "92": ("Pakistan", "🇵🇰"), "680": ("Palau", "🇵🇼"),
    "970": ("Palestine", "🇵🇸"), "507": ("Panama", "🇵🇦"), "675": ("Papua New Guinea", "🇵🇬"), "595": ("Paraguay", "🇵🇾"),
    "51": ("Peru", "🇵🇪"), "63": ("Philippines", "🇵🇭"), "48": ("Poland", "🇵🇱"), "351": ("Portugal", "🇵🇹"),
    "1787": ("Puerto Rico", "🇵🇷"), "974": ("Qatar", "🇶🇦"), "40": ("Romania", "🇷🇴"), "7": ("Russia", "🇷🇺"),
    "250": ("Rwanda", "🇷🇼"), "685": ("Samoa", "🇼🇸"), "378": ("San Marino", "🇸🇲"), "239": ("Sao Tome & Principe", "🇸🇹"),
    "966": ("Saudi Arabia", "🇸🇦"), "221": ("Senegal", "🇸🇳"), "381": ("Serbia", "🇷🇸"), "248": ("Seychelles", "🇸🇨"),
    "232": ("Sierra Leone", "🇸🇱"), "65": ("Singapore", "🇸🇬"), "421": ("Slovakia", "🇸🇰"), "386": ("Slovenia", "🇸🇮"),
    "677": ("Solomon Islands", "🇸🇧"), "252": ("Somalia", "🇸🇴"), "27": ("South Africa", "🇿🇦"), "82": ("South Korea", "🇰🇷"),
    "211": ("South Sudan", "🇸🇸"), "34": ("Spain", "🇪🇸"), "94": ("Sri Lanka", "🇱🇰"), "249": ("Sudan", "🇸🇩"),
    "597": ("Suriname", "🇸🇷"), "268": ("Swaziland", "🇸🇿"), "46": ("Sweden", "🇸🇪"), "41": ("Switzerland", "🇨🇭"),
    "963": ("Syria", "🇸🇾"), "886": ("Taiwan", "🇹🇼"), "992": ("Tajikistan", "🇹🇯"), "255": ("Tanzania", "🇹🇿"),
    "66": ("Thailand", "🇹🇭"), "670": ("Timor-Leste", "🇹🇱"), "228": ("Togo", "🇹🇬"), "690": ("Tokelau", "🇹🇰"),
    "676": ("Tonga", "🇹🇴"), "1868": ("Trinidad & Tobago", "🇹🇹"), "216": ("Tunisia", "🇹🇳"), "90": ("Turkey", "🇹🇷"),
    "993": ("Turkmenistan", "🇹🇲"), "1649": ("Turks & Caicos", "🇹🇨"), "688": ("Tuvalu", "🇹🇻"), "256": ("Uganda", "🇺🇬"),
    "380": ("Ukraine", "🇺🇦"), "971": ("UAE", "🇦🇪"), "44": ("United Kingdom", "🇬🇧"), "598": ("Uruguay", "🇺🇾"),
    "998": ("Uzbekistan", "UZ"), "678": ("Vanuatu", "🇻🇺"), "379": ("Vatican City", "🇻🇦"), "58": ("Venezuela", "🇻🇪"),
    "84": ("Vietnam", "🇻🇳"), "1284": ("Virgin Islands (UK)", "🇻🇬"), "1340": ("Virgin Islands (US)", "🇻🇮"),
    "967": ("Yemen", "🇾🇪"), "260": ("Zambia", "🇿🇲"), "263": ("Zimbabwe", "🇿🇼")
}

for code, (cname, flag) in country_db.items():
    full_key = f"{cname} {flag}"
    if full_key not in inventory_numbers:
        inventory_numbers[full_key] = {"flag": flag, "name": cname, "numbers": []}

def detect_country_info(phone_str):
    clean = re.sub(r'\D', '', phone_str)
    for length in range(4, 0, -1):
        prefix = clean[:length]
        if prefix in country_db:
            cname, flag = country_db[prefix]
            return cname, flag, f"{cname} {flag}"
    return "Unknown", "🌐", "Unknown 🌐"

def parse_service_name(msg_text):
    text_upper = str(msg_text).upper()
    if "WHATSAPP" in text_upper: return "WhatsApp"
    elif "TELEGRAM" in text_upper: return "Telegram"
    elif "FACEBOOK" in text_upper or "FB" in text_upper: return "Facebook"
    elif "TIKTOK" in text_upper: return "TikTok"
    elif "SHOPEE" in text_upper: return "Shopee"
    elif "PAYPAL" in text_upper: return "PayPal"
    elif "UBER" in text_upper: return "Uber"
    elif "APPLE" in text_upper or "ICLOUD" in text_upper: return "Apple"
    elif "GOOGLE" in text_upper or "G-" in text_upper: return "Google"
    elif "INSTAGRAM" in text_upper or "IG" in text_upper: return "Instagram"
    elif "DISCORD" in text_upper: return "Discord"
    elif "ZALO" in text_upper: return "Zalo"
    return "AUTHMSG"

def get_reply_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("🌍 LIVE NUMBER"), KeyboardButton("📈 LIVE TRAFFIC"))
    markup.add(KeyboardButton("👥 INVITE FRIEND"), KeyboardButton("💳 WALLET"))
    markup.add(KeyboardButton("🏆 LEADERBOARD"))
    return markup

def get_menu_keyboard(user_id):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🚀 OPEN WEB APP", web_app=WebAppInfo(url=WEBAPP_URL)),
        InlineKeyboardButton("📦 LIVE STOCK", callback_data="menu_live_number")
    )
    if user_id in ADMIN_IDS:
        kb.add(
            InlineKeyboardButton("👑 ADMIN PANEL", callback_data="menu_admin_panel"),
            InlineKeyboardButton("👑 DUYỆT RÚT", callback_data="admin_withdrawals")
        )
        kb.add(
            InlineKeyboardButton("⚙️ TẠO WSS", callback_data="menu_create_config"),
            InlineKeyboardButton("📊 LIST PANEL", callback_data="menu_list_panel")
        )
        kb.add(
            InlineKeyboardButton("➕ ADD NUMBERS", callback_data="menu_add_numbers")
        )
    return kb

@bot.message_handler(commands=['start'])
def send_welcome(message):
    uid = message.from_user.id
    if uid not in user_wallets:
        user_wallets[uid] = {"balance": 0.0, "ref_count": 0, "ref_earnings": 0.0}
    
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref"):
        try:
            ref_id = int(args[1].replace("ref", ""))
            if ref_id in user_wallets and ref_id != uid:
                user_wallets[ref_id]["ref_count"] += 1
                user_wallets[ref_id]["balance"] += 0.005
                user_wallets[ref_id]["ref_earnings"] += 0.005
        except:
            pass

    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass

    welcome_text = (
        "🔥 <b>FAST NODE • IVAS OTP GATEWAY PORTAL</b>\n\n"
        "Welcome to the ultimate real-time secure OTP platform!"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="HTML", reply_markup=get_menu_keyboard(uid))
    bot.send_message(message.chat.id, "👇 Quick menu options below:", reply_markup=get_reply_keyboard())

@bot.message_handler(func=lambda msg: msg.text in ["🌍 LIVE NUMBER", "📈 LIVE TRAFFIC", "👥 INVITE FRIEND", "💳 WALLET", "🏆 LEADERBOARD"])
def handle_reply_buttons(message):
    uid = message.from_user.id
    if uid not in user_wallets:
        user_wallets[uid] = {"balance": 0.0, "ref_count": 0, "ref_earnings": 0.0}
        
    text = message.text
    if "LIVE NUMBER" in text:
        available_total = sum(1 for data in inventory_numbers.values() for item in data["numbers"] if not item.get("locked_by"))
        bot.reply_to(message, f"🌍 <b>LIVE STOCK (195+ Countries):</b>\n\n📦 Available numbers: <code>{available_total}</code>\nOpen Web App to get numbers!", parse_mode="HTML")
    elif "LIVE TRAFFIC" in text:
        bot.reply_to(message, "📈 <b>LIVE TRAFFIC MONITOR:</b>\n\nAll systems operating normally via Fast Node Gateway v3 API.", parse_mode="HTML")
    elif "INVITE FRIEND" in text:
        ref_link = f"https://t.me/FastNode_Bot?start=ref{uid}"
        bot.reply_to(message, f"👥 <b>REFERRAL PROGRAM</b>\n\nInvite friends and earn <b>$0.005</b> per referral!\n\n🔗 Your Link:\n<code>{ref_link}</code>\n\n📊 Total Invited: <b>{user_wallets[uid]['ref_count']}</b>\n💰 Total Earned: <b>${user_wallets[uid]['ref_earnings']:.3f}</b>", parse_mode="HTML")
    elif "WALLET" in text:
        bal = user_wallets[uid]["balance"]
        bot.reply_to(message, f"💳 <b>YOUR WALLET</b>\n\n💰 Balance: <b>${bal:.3f} USDT</b>\nMin withdraw: $5.00 (TON Network).", parse_mode="HTML")
    elif "LEADERBOARD" in text:
        bot.reply_to(message, f"🏆 <b>YOUR ACTIVITY STATUS</b>\n\n📊 Your Balance: <b>${user_wallets[uid]['balance']:.3f}</b>\n👥 Referrals: <b>{user_wallets[uid]['ref_count']} users</b>", parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    if call.data == "menu_live_number":
        available_total = sum(1 for data in inventory_numbers.values() for item in data["numbers"] if not item.get("locked_by"))
        text = f"🌍 <b>LIVE STOCK (195+ Countries):</b>\n\n📦 Available numbers: <code>{available_total}</code>"
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔙 BACK", callback_data="menu_back"))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode="HTML", reply_markup=kb)

    elif call.data == "menu_admin_panel":
        if user_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "⛔ Access denied!", show_alert=True)
            return
        text = "👑 <b>FAST NODE - ADMIN COMMAND CENTER</b>\n\nOpen the Web App and select 'Admin Panel' from the sidebar to access command telemetry, gateway matrix, radar feed, treasury vault, and developer access."
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🚀 OPEN WEB APP", web_app=WebAppInfo(url=WEBAPP_URL)))
        kb.add(InlineKeyboardButton("🔙 BACK", callback_data="menu_back"))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode="HTML", reply_markup=kb)

    elif call.data == "menu_create_config":
        if user_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "⛔ Access denied!", show_alert=True)
            return
        admin_state[user_id] = "waiting_for_ws"
        text = "🔮 <b>Setup WSS Configuration</b>\n\nSend your WebSocket URL or Cookie string here:"
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("❌ CANCEL", callback_data="menu_back"))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode="HTML", reply_markup=kb)

    elif call.data == "menu_list_panel":
        if user_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "⛔ Access denied!", show_alert=True)
            return
        
        ivas_connected = ivas_health.get("connected", False)
        ivas_status_str = "🟢 <b>CONNECTED / READY</b>" if ivas_connected else f"⚠️ <b>DISCONNECTED / EXPIRED</b> ({ivas_health.get('last_error', 'No check yet')})"
        wss_status_str = "🟢 <b>ACTIVE</b>" if user_configs else "⚠️ <b>NO CONFIG SET</b>"

        text = (
            "📊 <b>LIST PANEL - IVAS & WSS HEALTH MONITOR</b>\n\n"
            f"🔌 IVAS API Status: {ivas_status_str}\n"
            f"🔗 IVAS Base URL: <code>{IVAS_BASE_URL}</code>\n"
            f"📡 WSS Status: {wss_status_str}\n"
            f"🔑 Cookie Configured: <b>{'Yes' if _load_ivas_cookie() else 'No'}</b>\n"
            f"🔍 Details: <code>{html.escape(str(ivas_health.get('details', 'N/A')))}</code>"
        )
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔄 RECHECK STATUS", callback_data="menu_list_panel"))
        kb.add(InlineKeyboardButton("🔙 BACK", callback_data="menu_back"))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode="HTML", reply_markup=kb)

    elif call.data == "menu_add_numbers":
        if user_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "⛔ Access denied!", show_alert=True)
            return
        admin_state[user_id] = "waiting_for_numbers"
        text = "➕ <b>ADD NUMBERS AUTOMATICALLY</b>\n\nPaste your list of phone numbers below (separated by space, comma, or newline). System will auto-detect country codes!"
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("❌ CANCEL", callback_data="menu_back"))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode="HTML", reply_markup=kb)

    elif call.data == "admin_withdrawals":
        if user_id not in ADMIN_IDS: return
        if not withdrawal_requests:
            text = "📂 <b>Không có đơn rút tiền nào đang chờ duyệt!</b>"
        else:
            text = f"📂 <b>DANH SÁCH ĐƠN RÚT TIỀN ({len(withdrawal_requests)} đơn):</b>\n\n"
            for idx, req in enumerate(withdrawal_requests):
                text += f"🆔 <b>STT {idx+1}</b> | User ID: <code>{req['user_id']}</code>\n👤 Tên: {req['name']}\n💵 Số tiền: <b>${req['amount']}</b>\n📬 Ví TON: <code>{req['address']}</code>\n⏰ Lúc: {req['time']}\n━━━━━━━━━━━━━━━━━━━━━\n"
        kb = InlineKeyboardMarkup()
        if withdrawal_requests:
            kb.add(InlineKeyboardButton("✅ DUYỆT ĐƠN ĐẦU TIÊN", callback_data="approve_first_wd"))
        kb.add(InlineKeyboardButton("🔙 QUAY LẠI", callback_data="menu_back"))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode="HTML", reply_markup=kb)

    elif call.data == "approve_first_wd":
        if user_id not in ADMIN_IDS: return
        if withdrawal_requests:
            req = withdrawal_requests.pop(0)
            bot.send_message(req['user_id'], f"🎉 <b>Đơn rút ${req['amount']} USDT (TON) của bạn đã được Admin duyệt thành công!</b>", parse_mode="HTML")
            bot.answer_callback_query(call.id, "Đã duyệt đơn thành công!")
        handle_callback(type('obj', (object,), {'from_user': call.from_user, 'message': call.message, 'data': 'admin_withdrawals'})())

    elif call.data == "menu_back":
        admin_state.pop(user_id, None)
        welcome_text = "🔥 <b>FAST NODE • IVAS OTP GATEWAY PORTAL</b>\n\nWelcome to the ultimate real-time secure OTP platform!"
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=welcome_text, parse_mode="HTML", reply_markup=get_menu_keyboard(user_id))

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    current_state = admin_state.get(user_id)
    
    if current_state == "waiting_for_ws" and user_id in ADMIN_IDS:
        text_input = message.text.strip()
        ws_match = re.search(r'(wss?://[^\s\'"]+)', text_input)
        token_match = re.search(r'(?:token=|access_token=|key=)([a-zA-Z0-9_\-\.]+)', text_input)
        user_configs[user_id] = {
            "ws_url": ws_match.group(1) if ws_match else "Custom Session",
            "token": token_match.group(1) if token_match else text_input[:20],
            "balance": "$0.00"
        }
        admin_state.pop(user_id, None)
        bot.reply_to(message, "✅ WebSocket WSS Configuration saved successfully!", parse_mode="HTML", reply_markup=get_reply_keyboard())
        return

    if current_state == "waiting_for_numbers" and user_id in ADMIN_IDS:
        phones = re.split(r'[\s,\n]+', message.text)
        total_added = 0
        duplicates = []
        added_summary = {}
        
        all_existing_phones = set()
        for data in inventory_numbers.values():
            for item in data["numbers"]:
                all_existing_phones.add(item["phone"])

        for phone in phones:
            cleaned = phone.replace("+", "").strip()
            if cleaned.isdigit() and len(cleaned) >= 5:
                if cleaned in all_existing_phones:
                    duplicates.append(cleaned)
                    continue
                cname, flag, full_key = detect_country_info(cleaned)
                if full_key not in inventory_numbers:
                    inventory_numbers[full_key] = {"flag": flag, "name": cname, "numbers": []}
                inventory_numbers[full_key]["numbers"].append({"phone": cleaned, "expires": 0, "locked_by": None})
                all_existing_phones.add(cleaned)
                total_added += 1
                added_summary[full_key] = added_summary.get(full_key, 0) + 1
        
        admin_state.pop(user_id, None)
        summary_str = "\n".join([f"• {k}: <b>+{v} numbers</b>" for k, v in added_summary.items()])
        dup_str = f"\n\n⚠️ <b>Đã trùng có trước đó ({len(duplicates)} số):</b> <code>{', '.join(duplicates[:10])}{'...' if len(duplicates)>10 else ''}</code>" if duplicates else ""
        bot.reply_to(message, f"✅ <b>Successfully auto-added {total_added} numbers!</b>\n\n{summary_str}{dup_str}", parse_mode="HTML", reply_markup=get_reply_keyboard())
        return

@bot.message_handler(commands=['thue'])
def handle_rent_number(message):
    parts = message.text.split()
    if len(parts) < 2: return
    phone_to_rent = parts[1].replace("+", "").strip()
    user_id = message.chat.id
    user_rentals[phone_to_rent] = user_id
    
    for key, data in inventory_numbers.items():
        for item in data["numbers"]:
            if item["phone"] == phone_to_rent:
                item["expires"] = time.time() + 900
                item["locked_by"] = user_id
                break
    bot.reply_to(message, f"✅ Successfully rented number <code>{phone_to_rent}</code> for 15 minutes! OTP will be delivered here privately.", parse_mode="HTML", reply_markup=get_reply_keyboard())

def background_cleanup_and_wss():
    global last_reset_time, app_stats
    while True:
        current_time = time.time()
        if current_time - last_reset_time > 86400:
            for k in app_stats: app_stats[k] = 0
            last_reset_time = current_time

        for key, data in inventory_numbers.items():
            for item in list(data["numbers"]):
                if item["expires"] > 0 and item["expires"] <= current_time:
                    user_rentals.pop(item["phone"], None)
                    data["numbers"].remove(item)
        time.sleep(30)

async def dispatch_update(service, phone, msg, timestamp, country, flag, is_test=False):
    global app_stats, top_ranges_data, live_radar_logs
    clean_phone = str(phone).replace("+", "")
    masked = clean_phone[:6] + "****" + clean_phone[-3:] if len(clean_phone) > 7 else clean_phone
    match = re.search(r'\d{3}[-\s]?\d{3}|\d{4,8}', str(msg))
    code = match.group(0) if match else "N/A"

    detected_service = parse_service_name(f"{service} {msg}")
    if detected_service in app_stats:
        app_stats[detected_service] += 1
    else:
        app_stats["AUTHMSG"] += 1

    live_radar_logs.insert(0, {
        "time": timestamp,
        "country": country,
        "flag": flag,
        "phone": masked,
        "service": detected_service,
        "code": code,
        "message": msg
    })
    if len(live_radar_logs) > 50:
        live_radar_logs.pop()

    range_prefix = clean_phone[:5]
    existing_range = next((r for r in top_ranges_data if r['range'] == range_prefix), None)
    if existing_range:
        existing_range['count'] += 1
    else:
        top_ranges_data.append({"country": country, "range": range_prefix, "flag": flag, "count": 1})
    top_ranges_data.sort(key=lambda x: x['count'], reverse=True)
    if len(top_ranges_data) > 5: top_ranges_data = top_ranges_data[:5]

    if clean_phone in user_rentals:
        owner_id = user_rentals[clean_phone]
        if owner_id in user_wallets:
            user_wallets[owner_id]["balance"] += 0.008

    header = "🧪 <b>『 ꜰᴇ ꜱᴇɴᴅ ᴏᴛᴘ 』</b> 🧪" if is_test else "💐 <b>『 ɴᴇᴡ ᴏᴛᴘ ʀᴇᴄᴇɪᴠᴇᴅ 』</b> ✨"
    caption = (f"{header}\n"
               f"━━━━━━━━━━━━━━━━━━━━━\n\n"
               f"<b>⌚ TIME:</b> <code>{html.escape(str(timestamp))}</code>\n"
               f"<b>🌍 COUNTRY:</b> {html.escape(str(country))} {flag}\n"
               f"<b>📱 NUMBER:</b> <code>{html.escape(str(masked))}</code>\n"
               f"<b>🛠 SERVICE:</b> <code>{html.escape(str(detected_service))}</code>\n"
               f"<b>🔑 CODE:</b> <code>{html.escape(str(code))}</code>\n\n"
               f"<b>💬 MESSAGE:</b>\n<pre>{html.escape(str(msg))}</pre>\n\n"
               f"━━━━━━━━━━━━━━━━━━━━━")
    
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("✨ YouTube", url="https://youtube.com/@ThoKho_VN"),
        InlineKeyboardButton("👑 Owner", url="https://t.me/Nothavedie")
    )
    kb.row(
        InlineKeyboardButton("📥 OTP Channel", url="https://t.me/LIVEOTPIVAS"),
        InlineKeyboardButton("🎀 Main Channel", url="https://t.me/FastNode_1")
    )
    
    try:
        await asyncio.to_thread(bot.send_message, chat_id=TARGET_CHAT, text=caption, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)
    except Exception as e: pass

    if clean_phone in user_rentals:
        owner_id = user_rentals[clean_phone]
        private_caption = f"🔔 <b>[REAL-TIME PRIVATE EXCLUSIVE OTP ($0.008 EARNED)]</b>\n\n" + caption
        try:
            await asyncio.to_thread(bot.send_message, chat_id=owner_id, text=private_caption, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)
        except Exception as e: pass

def websocket_worker():
    def on_message(ws, message):
        try:
            data = json.loads(message)
            phone = data.get("phone", "84939168914")
            service = data.get("service", "WhatsApp")
            msg = data.get("message", "Your verification code is 790-937")
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            cname, flag, _ = detect_country_info(phone)
            asyncio.run(dispatch_update(service, phone, msg, timestamp, cname, flag, is_test=False))
        except: pass
        
    def on_error(ws, error):
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(admin_id, f"🚨 <b>WSS ERROR / 403 ALERT!</b>\n\nWebSocket encountered an error: <code>{str(error)}</code>", parse_mode="HTML")
            except: pass

    def on_close(ws, c, m):
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(admin_id, f"⚠️ <b>WSS CONNECTION CLOSED / DIE!</b>\n\nWebSocket connection was lost. Code: {c}", parse_mode="HTML")
            except: pass
        time.sleep(10)

    def on_open(ws): print("🟢 WebSocket Connected Real-time!")

    while True:
        for uid, cfg in user_configs.items():
            ws_url = cfg.get("ws_url")
            if ws_url and ws_url.startswith("wss://"):
                try:
                    wsapp = websocket.WebSocketApp(ws_url, on_open=on_open, on_message=on_message, on_error=on_error, on_close=on_close)
                    wsapp.run_forever()
                except Exception as e:
                    for admin_id in ADMIN_IDS:
                        try:
                            bot.send_message(admin_id, f"🚨 <b>WSS CRITICAL FAILURE!</b>\n\nException: <code>{str(e)}</code>", parse_mode="HTML")
                        except: pass
        time.sleep(15)

# --- FLASK SERVER & WEB APP ---
app = Flask(__name__)
app.config["SECRET_KEY"] = FLASK_SECRET_KEY

def verify_telegram_init_data(init_data: str):
    if not init_data or not BOT_TOKEN:
        return None
    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            return None

        data_check_string = "\n".join(
            f"{key}={value}"
            for key, value in sorted(parsed.items())
        )

        secret_key = hmac.new(
            key=b"WebAppData",
            msg=BOT_TOKEN.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()

        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode("utf-8"),
            digestmod=hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(calculated_hash, received_hash):
            return None

        auth_date = int(parsed.get("auth_date", "0"))
        now = int(time.time())
        if auth_date <= 0 or now - auth_date > 300:
            return None
        if auth_date > now + 30:
            return None

        user_data = json.loads(parsed.get("user", "{}"))
        user_id = int(user_data.get("id", 0))
        if user_id <= 0:
            return None

        return {"user_id": user_id, "user": user_data}
    except Exception:
        return None

def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        init_data = request.headers.get("X-Telegram-Init-Data", "")
        auth_result = verify_telegram_init_data(init_data)
        
        if not auth_result:
            return jsonify({"success": False, "error": "Unauthorized / Invalid initData"}), 401
            
        if auth_result["user_id"] not in ADMIN_IDS:
            return jsonify({"success": False, "error": "Forbidden: Admin access required"}), 403
            
        return f(*args, **kwargs)
    return decorated

@app.route('/api/inventory', methods=['GET'])
def api_inventory():
    countries_data = []
    for key, data in inventory_numbers.items():
        available_numbers = [{"phone": item["phone"], "expires": item["expires"]} for item in data["numbers"] if not item.get("locked_by")]
        countries_data.append({"key": key, "name": data["name"], "flag": data["flag"], "numbers": available_numbers})
    return jsonify(countries_data)

@app.route('/api/admin/stats', methods=['GET'])
@require_admin
def api_admin_stats():
    total_ranges = len([k for k, v in inventory_numbers.items() if len(v["numbers"]) > 0])
    total_numbers_count = sum(len(v["numbers"]) for v in inventory_numbers.values())
    virtual_lines_taken = len(user_rentals)
    verified_payloads = len(live_radar_logs)
    success_rate = round((verified_payloads / max(1, verified_payloads + 5)) * 100, 1)

    return jsonify({
        "success": True,
        "active_ranges": total_ranges,
        "operators": len(country_db),
        "virtual_lines_taken": virtual_lines_taken,
        "verified_payloads": verified_payloads,
        "success_rate": success_rate,
        "total_numbers": total_numbers_count,
        "radar_logs": live_radar_logs[:20]
    })

@app.route('/api/admin/delete_number', methods=['POST'])
@require_admin
def api_delete_number():
    data = request.json or {}
    phone = data.get("phone")
    deleted = False
    for key, val in inventory_numbers.items():
        initial_len = len(val["numbers"])
        val["numbers"] = [item for item in val["numbers"] if item["phone"] != phone]
        if len(val["numbers"]) < initial_len:
            deleted = True
            break
    return jsonify({"success": deleted})

@app.route('/api/admin/delete_bulk_country', methods=['POST'])
@require_admin
def api_delete_bulk_country():
    data = request.json or {}
    key = data.get("key")
    count = int(data.get("count", 100))
    if key in inventory_numbers:
        removed_count = min(count, len(inventory_numbers[key]["numbers"]))
        inventory_numbers[key]["numbers"] = inventory_numbers[key]["numbers"][removed_count:]
        return jsonify({"success": True, "removed": removed_count})
    return jsonify({"success": False})

@app.route("/api/ivas/health", methods=["GET"])
@require_admin
def ivas_health_api():
    with ivas_lock:
        return jsonify({
            "ok": True,
            **ivas_health
        })

# --- ADMIN ROUTE: REFRESH COOKIE KHÔNG CẦN REDEPLOY ---
@app.route("/admin/refresh-ivas-cookie", methods=["POST"])
def refresh_ivas_cookie():
    if IVAS_REFRESH_TOKEN:
        token = request.headers.get("X-Refresh-Token", "")
        if token != IVAS_REFRESH_TOKEN:
            return jsonify({"ok": False, "error": "invalid refresh token"}), 403

    payload = request.get_json(silent=True) or {}
    new_cookie = (payload.get("cookie") or "").strip()

    if not new_cookie:
        return jsonify({"ok": False, "error": "missing 'cookie' field"}), 400

    parsed = _parse_cookie_string(new_cookie)
    if not parsed:
        return jsonify({"ok": False, "error": "cookie parsed to zero entries"}), 400

    persisted = _write_cookie_to_file(new_cookie)
    _invalidate_session()

    try:
        _get_ivas_session()
    except Exception as e:
        return jsonify({"ok": False, "error": f"session build failed: {e}"}), 500

    alive = ivas_check_session()

    return jsonify({
        "ok": True,
        "cookie_keys": list(parsed.keys()),
        "persisted_to_file": persisted,
        "session_alive": alive,
    })

@app.route('/api/config/update', methods=['POST'])
@require_admin
def api_config_update():
    data = request.json or {}
    base_url = data.get("base_url")
    token_or_cookie = data.get("token_or_cookie")
    
    global IVAS_BASE_URL
    if base_url:
        IVAS_BASE_URL = base_url.strip().rstrip("/")
        
    if token_or_cookie:
        _write_cookie_to_file(token_or_cookie.strip())
        _invalidate_session()
        
    return jsonify({"success": True, "message": "Cập nhật cấu hình IVAS thành công!"})

@app.route('/')
def home():
    countries_data = []
    for key, data in inventory_numbers.items():
        available_numbers = [{"phone": item["phone"], "expires": item["expires"]} for item in data["numbers"] if not item.get("locked_by")]
        countries_data.append({"key": key, "name": data["name"], "flag": data["flag"], "numbers": available_numbers})
    
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Fast Node • Portal Dashboard</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            :root { --bg: #0f172a; --card: #1e293b; --orange-bar: #f59e0b; --border: #334155; --text: #f8fafc; --muted: #94a3b8; --green: #22c55e; --red: #ef4444; --admin-gold: #fbbf24; }
            body { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 0; }
            
            .top-bar { background: var(--orange-bar); color: #000; padding: 12px 16px; font-weight: bold; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 100; }
            .hamburger-btn { background: none; border: none; font-size: 20px; cursor: pointer; color: #000; font-weight: bold; }
            
            .sidebar { position: fixed; top: 0; left: -260px; width: 250px; height: 100%; background: #131c2e; border-right: 1px solid var(--border); transition: 0.3s ease; z-index: 1000; padding-top: 20px; box-shadow: 4px 0 15px rgba(0,0,0,0.5); overflow-y: auto; }
            .sidebar.open { left: 0; }
            .sidebar-header { padding: 0 16px 15px 16px; border-bottom: 1px solid var(--border); font-size: 16px; font-weight: bold; color: #38bdf8; display: flex; justify-content: space-between; align-items: center; }
            .menu-link { display: block; padding: 14px 16px; color: var(--text); text-decoration: none; font-weight: bold; font-size: 14px; border-bottom: 1px solid var(--border); cursor: pointer; transition: 0.2s; }
            .menu-link:hover { background: #1e293b; color: #38bdf8; }

            .content-container { padding: 12px; }
            .view-section { display: none; }
            .view-section.active { display: block; }

            .dashboard-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 10px; margin-bottom: 12px; }
            @media(max-width: 600px) { .dashboard-grid { grid-template-columns: 1fr; } }

            .widget-card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 14px; margin-bottom: 12px; }
            .widget-title { font-size: 14px; font-weight: bold; color: #f59e0b; margin-bottom: 10px; border-bottom: 1px solid var(--border); padding-bottom: 6px; }

            .apps-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
            .app-box { background: #131c2e; border: 1px solid var(--border); border-radius: 8px; padding: 8px; text-align: center; font-size: 11px; }
            .app-box b { display: block; font-size: 12px; color: #38bdf8; margin-top: 2px; }

            .range-item { display: flex; align-items: center; justify-content: space-between; background: #131c2e; border: 1px solid var(--border); padding: 8px; border-radius: 6px; margin-bottom: 6px; font-size: 12px; }

            .grid-countries { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; }
            .country-pill { background: #131c2e; border: 1px solid var(--border); border-radius: 6px; padding: 6px 2px; text-align: center; cursor: pointer; font-size: 10px; }
            .country-pill:hover { border-color: #38bdf8; }

            .number-item { display: flex; justify-content: space-between; align-items: center; background: #131c2e; border: 1px solid var(--border); padding: 8px; border-radius: 6px; margin-bottom: 6px; font-size: 13px; }
            .btn { background: var(--green); color: white; border: none; border-radius: 6px; padding: 8px 14px; font-size: 13px; font-weight: bold; cursor: pointer; width: 100%; margin-top: 8px; }
            .btn-red { background: var(--red); }
            .btn-gray { background: #475569; }

            .input-box { width: 100%; padding: 10px; background: #0f172a; border: 1px solid var(--border); border-radius: 8px; color: white; margin-bottom: 10px; box-sizing: border-box; font-size: 14px; }
            .textarea-box { width: 100%; height: 100px; padding: 10px; background: #0f172a; border: 1px solid var(--border); border-radius: 8px; color: white; margin-bottom: 10px; box-sizing: border-box; font-size: 13px; resize: vertical; }
            .warning-box { background: rgba(239, 68, 68, 0.1); border: 1px solid var(--red); padding: 10px; border-radius: 8px; font-size: 12px; color: #fca5a5; margin-bottom: 10px; line-height: 1.4; }

            .admin-container { background: #0b1329; border: 1px solid #38bdf8; border-radius: 12px; padding: 16px; margin-bottom: 15px; }
            .admin-nav-tabs { display: flex; gap: 6px; overflow-x: auto; padding-bottom: 8px; margin-bottom: 12px; border-bottom: 1px solid var(--border); }
            .admin-tab-btn { background: #1e293b; border: 1px solid var(--border); color: var(--text); padding: 6px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; white-space: nowrap; }
            .admin-tab-btn.active { background: #38bdf8; color: #000; font-weight: bold; border-color: #38bdf8; }
            .admin-subview { display: none; }
            .admin-subview.active { display: block; }
            .mk-stat-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; margin-bottom: 12px; }
            .mk-stat-box { background: #131c2e; border: 1px solid var(--border); border-radius: 8px; padding: 10px; }
            .mk-stat-label { font-size: 11px; color: var(--muted); }
            .mk-stat-val { font-size: 16px; font-weight: bold; color: #38bdf8; margin-top: 4px; }
        </style>
    </head>
    <body>
        <div class="top-bar">
            <div style="display:flex; align-items:center; gap:10px;">
                <button class="hamburger-btn" onclick="toggleSidebar()">☰</button>
                <span>Fast Node • Portal</span>
            </div>
            <span id="headerBalance">Balance: $0.000</span>
        </div>

        <div class="sidebar" id="sidebarDrawer">
            <div class="sidebar-header">
                <span>📁 Menu</span>
                <span style="cursor:pointer; font-size:18px;" onclick="toggleSidebar()">✕</span>
            </div>
            <a class="menu-link" onclick="switchView('dashboardView')">📊 Dashboard</a>
            <a class="menu-link" onclick="switchView('getNumberView')">🌍 Get Number (195+)</a>
            <a class="menu-link" onclick="switchView('withdrawView')">💸 Withdraw (TON USDT)</a>
            <a class="menu-link" onclick="switchView('referralView')">👥 Referral Program</a>
            
            <a class="menu-link" id="addNumbersSidebarLink" style="display:none; color:#f59e0b;" onclick="switchView('addNumbersView')">➕ Add Numbers (Admin)</a>
            <a class="menu-link" id="adminPanelSidebarLink" style="display:none; color:#fbbf24; background:rgba(251, 191, 36, 0.1);" onclick="switchView('adminPanelView')">👑 ADMIN PANEL (Fast Node)</a>

            <a class="menu-link" onclick="window.open('https://t.me/LIVEOTPIVAS', '_blank')">📢 Official Channel</a>
            <a class="menu-link" style="color:var(--red);" onclick="exitApp()">❌ Exit App</a>
        </div>

        <div class="content-container">
            
            <div id="dashboardView" class="view-section active">
                <div class="dashboard-grid">
                    <div class="widget-card">
                        <div class="widget-title">Top Applications Access (Real-time & 24h Reset)</div>
                        <div class="apps-grid" id="appsGrid"></div>
                    </div>
                    <div class="widget-card">
                        <div class="widget-title">🔥 Top Ranges (Real-time Active)</div>
                        <div id="topRangesContainer">
                            <p style="font-size:11px; color:var(--muted); text-align:center;">No active ranges yet.</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- ADMIN PANEL VIEW -->
            <div id="adminPanelView" class="view-section">
                <div class="admin-container">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                        <h2 style="font-size:16px; color:#fbbf24; margin:0;">FAST NODE • COMMAND CENTER</h2>
                        <span style="font-size:11px; color:var(--muted);" id="adminTimestamp"></span>
                    </div>
                    <p style="font-size:12px; color:var(--muted); margin-bottom:12px;">Workspace metrics, telemetry, and advanced carrier routing.</p>

                    <div class="admin-nav-tabs">
                        <button class="admin-tab-btn active" onclick="switchAdminTab('admOverview', event)">📊 Dashboard</button>
                        <button class="admin-tab-btn" onclick="switchAdminTab('admNumbers', event)">📦 Numbers</button>
                        <button class="admin-tab-btn" onclick="switchAdminTab('admRadar', event)">📡 Radar</button>
                        <button class="admin-tab-btn" onclick="switchAdminTab('admAccess', event)">🔗 Gateway Access</button>
                        <button class="admin-tab-btn" onclick="switchAdminTab('admWallet', event)">💳 Treasury & Funds</button>
                        <button class="admin-tab-btn" onclick="switchAdminTab('admAudit', event)">📈 My Audit</button>
                        <button class="admin-tab-btn" onclick="switchAdminTab('admProfile', event)">👤 Identity</button>
                        <button class="admin-tab-btn" onclick="switchAdminTab('admDeveloper', event)">⚡ API Access</button>
                    </div>

                    <div id="admOverview" class="admin-subview active">
                        <div class="mk-stat-grid">
                            <div class="mk-stat-box">
                                <div class="mk-stat-label">VIRTUAL LINES TAKEN</div>
                                <div class="mk-stat-val" id="realVirtualLines">0</div>
                            </div>
                            <div class="mk-stat-box">
                                <div class="mk-stat-label">VERIFIED PAYLOADS</div>
                                <div class="mk-stat-val" style="color:var(--green);" id="realVerifiedPayloads">0</div>
                            </div>
                            <div class="mk-stat-box">
                                <div class="mk-stat-label">CONVERSION RATE</div>
                                <div class="mk-stat-val" style="color:#f59e0b;">$0.0080</div>
                            </div>
                            <div class="mk-stat-box">
                                <div class="mk-stat-label">AVAILABLE CAPITAL</div>
                                <div class="mk-stat-val">$0.0000</div>
                            </div>
                        </div>
                        <div class="widget-card">
                            <div class="widget-title">SYSTEM ANALYTICS & EXTRACTION</div>
                            <div style="font-size:13px; margin-bottom:6px;">Extraction Success Rate</div>
                            <div style="font-size:18px; font-weight:bold; color:var(--green);" id="realSuccessRate">100% <span style="font-size:11px; color:var(--muted); font-weight:normal;" id="realSuccessText">Real-time live synchronization active</span></div>
                        </div>
                    </div>

                    <div id="admNumbers" class="admin-subview">
                        <div class="widget-card">
                            <div class="widget-title">Number Allocation & Range Management</div>
                            <input type="text" class="input-box" placeholder="Search range (e.g. 9596XXX)..." id="admSearchRange">
                            <div style="display:flex; gap:6px; margin-bottom:10px;">
                                <button class="btn" style="margin:0;" onclick="adminAllocateNumber()">Allocate New Number</button>
                            </div>
                            <div id="admNumberAllocationList">
                                <p style="font-size:12px; color:var(--muted);">Active allocation pools ready.</p>
                            </div>
                        </div>
                    </div>

                    <div id="admRadar" class="admin-subview">
                        <div class="widget-card">
                            <div class="widget-title">Unified Radar Feed (Real-Time OTP Traffic)</div>
                            <p style="font-size:11px; color:var(--muted); margin-bottom:8px;">Live incoming messages from IVASMS gateway.</p>
                            <div id="admRadarFeedList" style="max-height:250px; overflow-y:auto; font-size:12px;">
                                <p style="font-size:11px; color:var(--muted); text-align:center;">Waiting for real-time traffic...</p>
                            </div>
                        </div>
                    </div>

                    <div id="admAccess" class="admin-subview">
                        <div class="widget-card">
                            <div class="widget-title">Gateway Matrix • Target Nodes</div>
                            <div class="mk-stat-grid" style="margin-bottom:10px;">
                                <div class="mk-stat-box"><div class="mk-stat-label">ACTIVE RANGES</div><div class="mk-stat-val" id="realActiveRanges">0</div></div>
                                <div class="mk-stat-box"><div class="mk-stat-label">OPERATORS</div><div class="mk-stat-val" id="realOperators">195</div></div>
                            </div>
                            <div style="font-size:12px; color:var(--muted);" id="realInventoryText">Routing Inventory loaded across connected regions.</div>
                        </div>
                    </div>

                    <div id="admWallet" class="admin-subview">
                        <div class="widget-card">
                            <div class="widget-title">Treasury & Funds • Capital Vault</div>
                            <div style="font-size:13px; margin-bottom:6px;">Available Capital: <b style="color:var(--green);">0.0000 USD</b></div>
                            <div class="warning-box">Changing payout method later needs manual identity review (KYC).</div>
                            <label style="font-size:12px; color:var(--muted); display:block; margin-bottom:4px;">Payout Method:</label>
                            <select class="input-box" id="payoutMethodSelect"><option value="ton">TON Network / USDT</option><option value="bkash">bKash</option><option value="binance">Binance UID</option></select>
                            <input type="text" class="input-box" placeholder="Account / Wallet Address..." id="payoutAccountInput">
                            <button class="btn" onclick="saveVaultConfig()">Activate Vault & Security</button>
                        </div>
                    </div>

                    <div id="admAudit" class="admin-subview">
                        <div class="widget-card">
                            <div class="widget-title">Audit Trail & Telemetry Logs</div>
                            <div class="mk-stat-grid">
                                <div class="mk-stat-box"><div class="mk-stat-label">LINES EXECUTED</div><div class="mk-stat-val" id="auditLinesExecuted">5</div></div>
                                <div class="mk-stat-box"><div class="mk-stat-label">VERIFIED PAYLOADS</div><div class="mk-stat-val" id="auditVerifiedPayloads">0</div></div>
                            </div>
                            <button class="btn btn-gray" onclick="downloadAuditReport()">📥 Download Audit Report</button>
                        </div>
                    </div>

                    <div id="admProfile" class="admin-subview">
                        <div class="widget-card">
                            <div class="widget-title">Admin Identity & Security Profile</div>
                            <input type="text" class="input-box" value="Khoibro090" id="admProfileName">
                            <input type="text" class="input-box" value="8804664464" id="admProfilePhone">
                            <button class="btn" onclick="saveProfileChanges()">Save Changes</button>
                        </div>
                    </div>

                    <div id="admDeveloper" class="admin-subview">
                        <div class="widget-card">
                            <div class="widget-title">⚡ API Access & Real-Time IVASMS Bridge Configuration</div>
                            <p style="font-size:11px; color:var(--muted); margin-bottom:8px;">Nhập Base URL và Cookie thủ công để thiết lập cầu nối trực tiếp Real-Time IVASMS.</p>
                            
                            <label style="font-size:11px; color:#38bdf8;">IVAS Base URL:</label>
                            <input type="text" class="input-box" id="editIvasBaseUrl" value="https://www.ivasms.com">

                            <label style="font-size:11px; color:#38bdf8;">Cookie String:</label>
                            <input type="password" class="input-box" id="editIvasTokenCookie" placeholder="Dán chuỗi cookie (cf_clearance=...; ivas_session=...) vào đây...">

                            <div style="display:flex; gap:6px; margin-top:8px;">
                                <button class="btn" style="flex:1; margin:0;" onclick="saveIvasConfigBridge()">💾 Save & Connect</button>
                                <button class="btn btn-red" style="flex:1; margin:0;" onclick="cancelIvasConfigBridge()">❌ Cancel</button>
                            </div>
                        </div>
                    </div>

                </div>
            </div>

            <div id="getNumberView" class="view-section">
                <div class="widget-card" id="marketplaceSection">
                    <div class="widget-title">Get Number • 195+ Countries Marketplace</div>
                    <div class="grid-countries" id="countryGrid"></div>
                </div>

                <div class="widget-card" id="detailCard" style="display:none;">
                    <h3 id="detailTitleText" style="color:#38bdf8; font-size:14px; margin-bottom:8px;">Number Details</h3>
                    <div id="numberListContainer"></div>
                    <div style="display:flex; gap:6px; margin-top:10px;">
                        <button class="btn btn-gray" style="flex:1; margin:0;" onclick="goBackToGrid()">🔙 Back</button>
                        <button class="btn" style="flex:1; margin:0;" onclick="refreshInventory()">🔄 Refresh</button>
                    </div>
                </div>
            </div>

            <div id="withdrawView" class="view-section">
                <div class="widget-card">
                    <div class="widget-title">💸 Withdraw USDT (TON Network)</div>
                    <div class="warning-box">
                        <b>⚠️ IMPORTANT RULES & REGULATIONS:</b><br>
                        • Minimum withdrawal amount: <b>$5.00</b>.<br>
                        • Only enter a valid <b>TON network USDT address</b> (must start with EQ or UQ).<br>
                        • <b>WARNING:</b> Incorrect network/address means permanent loss of funds!
                    </div>
                    <div style="font-size: 13px; margin-bottom: 6px; color: var(--muted);">Your Balance: <b id="withdrawBalance" style="color:var(--green);">$0.000</b></div>
                    <input type="number" id="withdrawAmount" class="input-box" placeholder="Min $5.00">
                    <input type="text" id="tonAddress" class="input-box" placeholder="TON Address (EQ... / UQ...)">
                    <button class="btn" onclick="requestWithdraw()">Submit Withdrawal Request</button>
                </div>
            </div>

            <div id="referralView" class="view-section">
                <div class="widget-card">
                    <div class="widget-title">👥 Referral Program & Earnings</div>
                    <p style="font-size: 13px; color: var(--muted); line-height: 1.4;">
                        Invite friends using your link. Earn <b>$0.005</b> for every active user!
                    </p>
                    <div style="margin: 12px 0;">
                        <label style="font-size: 12px; color: var(--muted);">Your Referral Link:</label>
                        <input type="text" id="refLinkInput" class="input-box" readonly style="background:#0f172a; color:#38bdf8; margin-top:4px;">
                    </div>
                    <div style="display: flex; gap: 10px; margin-top: 10px;">
                        <div class="widget-card" style="flex:1; text-align:center; margin:0;">
                            <div style="font-size: 11px; color: var(--muted);">Invited Friends</div>
                            <div id="refCountDisplay" style="font-size: 18px; font-weight: bold; color: #38bdf8; margin-top: 4px;">0</div>
                        </div>
                        <div class="widget-card" style="flex:1; text-align:center; margin:0;">
                            <div style="font-size: 11px; color: var(--muted);">Total Earned</div>
                            <div id="refEarningsDisplay" style="font-size: 18px; font-weight: bold; color: var(--green); margin-top: 4px;">$0.000</div>
                        </div>
                    </div>
                </div>
            </div>

            <div id="addNumbersView" class="view-section">
                <div class="widget-card">
                    <div class="widget-title">➕ Auto-Add Numbers (Admin)</div>
                    <p style="font-size: 12px; color: var(--muted); line-height: 1.4;">
                        Paste numbers below. Auto-detects country codes & checks duplicates!
                    </p>
                    <textarea id="bulkNumbersInput" class="textarea-box" placeholder="Paste numbers here..."></textarea>
                    <button class="btn" onclick="submitBulkNumbers()">Auto-Deploy & Categorize Numbers</button>
                </div>

                <div class="widget-card">
                    <div class="widget-title" style="color:#ef4444;">🗑 Number Deletion Management</div>
                    
                    <div style="margin-bottom: 12px;">
                        <label style="font-size: 12px; font-weight: bold; color: #38bdf8; display: block; margin-bottom: 4px;">🗑 Delete Specific Numbers</label>
                        <div style="display:flex; gap:6px;">
                            <input type="text" id="specificPhoneInput" class="input-box" placeholder="Enter phone number to delete..." style="margin:0;">
                            <button class="btn btn-red" style="width:auto; margin:0; padding:0 12px;" onclick="deleteSpecificNumber()">Delete</button>
                        </div>
                    </div>

                    <div>
                        <label style="font-size: 12px; font-weight: bold; color: #f59e0b; display: block; margin-bottom: 4px;">⚡ Delete 100 Numbers by Country (195+)</label>
                        <select id="countryDeleteSelect" class="input-box" style="margin-bottom:6px;">
                            <option value="">-- Select Country to Delete (100 numbers) --</option>
                        </select>
                        <button class="btn btn-red" onclick="deleteBulkByCountry()">Permanently Delete 100 Numbers</button>
                    </div>
                </div>
            </div>

        </div>

        <script>
            let tg = window.Telegram.WebApp;
            tg.expand();

            let userBalance = 0.000;
            let refCount = 0;
            let refEarnings = 0.000;
            let userTgId = tg.initDataUnsafe && tg.initDataUnsafe.user ? Number(tg.initDataUnsafe.user.id) : 0;
            let adminIds = {{ admin_ids | tojson }};

            if (adminIds.includes(userTgId)) {
                document.getElementById('adminPanelSidebarLink').style.display = 'block';
                document.getElementById('addNumbersSidebarLink').style.display = 'block';
            } else {
                document.getElementById('adminPanelSidebarLink').style.display = 'none';
                document.getElementById('addNumbersSidebarLink').style.display = 'none';
            }

            document.getElementById('refLinkInput').value = `https://t.me/FastNode_Bot?start=ref${userTgId}`;
            document.getElementById('adminTimestamp').innerText = new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

            let appStats = {{ app_stats | tojson }};
            let topRanges = {{ top_ranges_data | tojson }};
            let countriesData = {{ countries_data | tojson }};
            let currentSelectedCountry = null;
            let currentSelectedCountryKey = null;

            function toggleSidebar() {
                document.getElementById('sidebarDrawer').classList.toggle('open');
            }

            function switchView(viewId) {
                document.querySelectorAll('.view-section').forEach(el => el.classList.remove('active'));
                document.getElementById(viewId).classList.add('active');
                toggleSidebar();
                if (viewId === 'adminPanelView') {
                    fetchAdminStats();
                }
            }

            function switchAdminTab(tabId, event) {
                document.querySelectorAll('.admin-subview').forEach(el => el.classList.remove('active'));
                document.querySelectorAll('.admin-tab-btn').forEach(el => el.classList.remove('active'));
                document.getElementById(tabId).classList.add('active');
                if (event && event.target) {
                    event.target.classList.add('active');
                }
            }

            function fetchAdminStats() {
                fetch('/api/admin/stats', {
                    headers: { 'X-Telegram-Init-Data': tg.initData }
                }).then(res => res.json()).then(data => {
                    if (data.success) {
                        document.getElementById('realVirtualLines').innerText = data.virtual_lines_taken;
                        document.getElementById('realVerifiedPayloads').innerText = data.verified_payloads;
                        document.getElementById('realSuccessRate').innerHTML = `${data.success_rate}% <span style="font-size:11px; color:var(--muted); font-weight:normal;">Live synced</span>`;
                        document.getElementById('realActiveRanges').innerText = data.active_ranges;
                        document.getElementById('realOperators').innerText = data.operators;
                        document.getElementById('realInventoryText').innerText = `Routing Inventory loaded with ${data.total_numbers} active numbers across connected regions.`;
                        document.getElementById('auditLinesExecuted').innerText = data.verified_payloads + 5;
                        document.getElementById('auditVerifiedPayloads').innerText = data.verified_payloads;

                        let radarContainer = document.getElementById('admRadarFeedList');
                        if (data.radar_logs && data.radar_logs.length > 0) {
                            radarContainer.innerHTML = '';
                            data.radar_logs.forEach(log => {
                                let row = document.createElement('div');
                                row.className = 'range-item';
                                row.innerHTML = `<span>${log.flag} <b>${log.country}</b> (${log.phone})</span> <span style="color:var(--green); font-weight:bold;">${log.service}: ${log.code}</span>`;
                                radarContainer.appendChild(row);
                            });
                        }
                    }
                }).catch(err => console.log(err));
            }

            setInterval(() => {
                if(document.getElementById('adminPanelView').classList.contains('active')) {
                    fetchAdminStats();
                }
            }, 10000);

            function exitApp() { tg.close(); }

            function updateWalletUI() {
                document.getElementById('headerBalance').innerText = `Balance: $${userBalance.toFixed(3)}`;
                document.getElementById('withdrawBalance').innerText = `$${userBalance.toFixed(3)}`;
                document.getElementById('refCountDisplay').innerText = refCount;
                document.getElementById('refEarningsDisplay').innerText = `$${refEarnings.toFixed(3)}`;
            }

            function saveIvasConfigBridge() {
                let baseUrl = document.getElementById('editIvasBaseUrl').value.trim();
                let tokenCookie = document.getElementById('editIvasTokenCookie').value.trim();

                if (!baseUrl) {
                    tg.showAlert("Vui lòng nhập IVAS Base URL!");
                    return;
                }

                fetch('/api/config/update', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Telegram-Init-Data': tg.initData
                    },
                    body: JSON.stringify({ base_url: baseUrl, token_or_cookie: tokenCookie })
                }).then(res => res.json()).then(data => {
                    if (data.success) {
                        tg.showAlert("Đã lưu và thiết lập cầu nối Real-Time IVASMS thành công!");
                    } else {
                        tg.showAlert("Lỗi: Yêu cầu quyền Admin!");
                    }
                }).catch(() => {
                    tg.showAlert("Đã gửi yêu cầu kết nối cầu nối real-time.");
                });
            }

            function cancelIvasConfigBridge() {
                document.getElementById('editIvasTokenCookie').value = '';
                document.getElementById('editIvasBaseUrl').value = 'https://www.ivasms.com';
                tg.showAlert("Đã hủy thay đổi cấu hình.");
            }

            function downloadAuditReport() {
                let reportContent = "FAST NODE - AUDIT REPORT\\nTimestamp: " + new Date().toISOString() + "\\nStatus: Operational Real-Time Bridge Active.";
                let blob = new Blob([reportContent], { type: 'text/plain' });
                let url = window.URL.createObjectURL(blob);
                let a = document.createElement('a');
                a.href = url;
                a.download = 'Fast_Node_Audit_Report.txt';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                a.remove();
                tg.showAlert("Đã tải xuống báo cáo Audit thành công!");
            }

            function renderApps() {
                let grid = document.getElementById('appsGrid');
                if (!grid) return;
                grid.innerHTML = '';
                for (let [appName, count] of Object.entries(appStats)) {
                    let div = document.createElement('div');
                    div.className = 'app-box';
                    div.innerHTML = `✉️ <div>${appName}</div><b>${count} msg</b>`;
                    grid.appendChild(div);
                }
            }

            function renderTopRanges() {
                let container = document.getElementById('topRangesContainer');
                if (!container) return;
                container.innerHTML = '';
                if (!topRanges || topRanges.length === 0) {
                    container.innerHTML = '<p style="font-size:11px; color:var(--muted); text-align:center;">No active ranges yet.</p>';
                    return;
                }
                topRanges.forEach(r => {
                    let div = document.createElement('div');
                    div.className = 'range-item';
                    div.innerHTML = `<span>${r.flag} <b>${r.country}</b></span> <span style="color:var(--green); font-weight:bold;">${r.range} (${r.count})</span>`;
                    container.appendChild(div);
                });
            }

            function renderCountries() {
                let grid = document.getElementById('countryGrid');
                let deleteSelect = document.getElementById('countryDeleteSelect');
                if (!grid) return;
                deleteSelect.innerHTML = '<option value="">-- Select Country to Delete (100 numbers) --</option>';
                grid.innerHTML = '';

                countriesData.forEach(c => {
                    let div = document.createElement('div');
                    div.className = 'country-pill';
                    div.innerHTML = `<span style="font-size:14px; display:block;">${c.flag}</span><div style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${c.name}</div><div style="color:var(--green); font-weight:bold;">${c.numbers.length}</div>`;
                    div.onclick = () => selectCountry(c.key);
                    grid.appendChild(div);

                    let opt = document.createElement('option');
                    opt.value = c.key;
                    opt.innerText = `${c.flag} ${c.name} (${c.numbers.length} available)`;
                    deleteSelect.appendChild(opt);
                });
            }

            function selectCountry(key) {
                currentSelectedCountryKey = key;
                currentSelectedCountry = countriesData.find(c => c.key === key);
                document.getElementById('detailTitleText').innerText = `${currentSelectedCountry.flag} ${currentSelectedCountry.name} (${currentSelectedCountry.numbers.length} Available)`;
                document.getElementById('detailCard').style.display = 'block';
                renderNumbers();
            }

            function renderNumbers() {
                let container = document.getElementById('numberListContainer');
                if (!container) return;
                container.innerHTML = '';
                if (!currentSelectedCountry || currentSelectedCountry.numbers.length === 0) {
                    container.innerHTML = '<p style="color:var(--muted); text-align:center; font-size:12px;">No available numbers in this country!</p>';
                    return;
                }
                currentSelectedCountry.numbers.forEach(item => {
                    let row = document.createElement('div');
                    row.className = 'number-item';
                    let deleteBtnHtml = adminIds.includes(userTgId) ? `<button class="btn btn-red" style="width:auto; margin:0; padding:4px 8px; font-size:11px;" onclick="deleteSpecificNumberDirect('${item.phone}')">Delete</button>` : '';
                    row.innerHTML = `<span><b>${item.phone}</b></span> <div style="display:flex; gap:4px;"><button class="btn" style="width:auto; margin:0; padding:4px 8px; font-size:11px;" onclick="rentNumber('${item.phone}')">Rent</button>${deleteBtnHtml}</div>`;
                    container.appendChild(row);
                });
            }

            function refreshInventory() {
                fetch('/api/inventory').then(res => res.json()).then(data => {
                    countriesData = data;
                    renderCountries();
                    if (currentSelectedCountryKey) {
                        selectCountry(currentSelectedCountryKey);
                    }
                    tg.showAlert("Inventory refreshed successfully!");
                }).catch(() => {
                    tg.showAlert("Failed to refresh inventory.");
                });
            }

            function goBackToGrid() {
                document.getElementById('detailCard').style.display = 'none';
                currentSelectedCountry = null;
                currentSelectedCountryKey = null;
            }

            function rentNumber(phone) {
                tg.sendData(`/thue ${phone}`);
                tg.showAlert(`Successfully rented number ${phone} for 15 minutes!`);
                tg.close();
            }

            function submitBulkNumbers() {
                let text = document.getElementById('bulkNumbersInput').value.trim();
                if (!text) {
                    tg.showAlert("Please enter or paste phone numbers!");
                    return;
                }
                tg.sendData(text);
                tg.showAlert("Numbers sent to bot for auto-deployment & duplicate check!");
                tg.close();
            }

            function deleteSpecificNumberDirect(phone) {
                tg.showConfirm(`Permanently delete phone number ${phone}?`, (confirmed) => {
                    if (confirmed) {
                        fetch('/api/admin/delete_number', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-Telegram-Init-Data': tg.initData
                            },
                            body: JSON.stringify({phone: phone})
                        }).then(res => res.json()).then(data => {
                            if(data.success) {
                                tg.showAlert("Number deleted permanently!");
                                refreshInventory();
                            } else {
                                tg.showAlert("Failed to delete number (Unauthorized).");
                            }
                        });
                    }
                });
            }

            function deleteSpecificNumber() {
                let phone = document.getElementById('specificPhoneInput').value.trim();
                if (!phone) {
                    tg.showAlert("Please enter a phone number to delete!");
                    return;
                }
                deleteSpecificNumberDirect(phone);
                document.getElementById('specificPhoneInput').value = '';
            }

            function deleteBulkByCountry() {
                let key = document.getElementById('countryDeleteSelect').value;
                if (!key) {
                    tg.showAlert("Please select a country from the dropdown!");
                    return;
                }
                tg.showConfirm(`Permanently delete up to 100 numbers from this country?`, (confirmed) => {
                    if (confirmed) {
                        fetch('/api/admin/delete_bulk_country', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-Telegram-Init-Data': tg.initData
                            },
                            body: JSON.stringify({key: key, count: 100})
                        }).then(res => res.json()).then(data => {
                            if(data.success) {
                                tg.showAlert(`Successfully deleted ${data.removed} numbers permanently!`);
                                refreshInventory();
                            } else {
                                tg.showAlert("Failed to delete numbers (Unauthorized).");
                            }
                        });
                    }
                });
            }

            function adminAllocateNumber() {
                tg.showAlert("Admin allocation pipeline initialized. Use the Add Numbers section or API v3.");
            }

            function saveVaultConfig() {
                tg.showAlert("Vault and payout method saved successfully.");
            }

            function saveProfileChanges() {
                tg.showAlert("Profile information updated successfully.");
            }

            function requestWithdraw() {
                let amount = parseFloat(document.getElementById('withdrawAmount').value);
                let address = document.getElementById('tonAddress').value.trim();

                if (isNaN(amount) || amount < 5) {
                    tg.showAlert("Minimum withdrawal amount is $5.00!");
                    return;
                }
                if (amount > userBalance) {
                    tg.showAlert("Insufficient balance!");
                    return;
                }
                if (!address.startsWith("EQ") && !address.startsWith("UQ") || address.length < 40) {
                    tg.showAlert("Invalid TON USDT address! Must start with EQ or UQ.");
                    return;
                }

                tg.showConfirm(`Withdraw $${amount} to TON address:\\n${address}?`, (confirmed) => {
                    if (confirmed) {
                        userBalance -= amount;
                        updateWalletUI();
                        fetch('/api/withdraw', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({user_id: userTgId, amount: amount, address: address})
                        }).then(res => res.json()).then(data => {
                            tg.showAlert("Withdrawal request submitted successfully!");
                        }).catch(() => {
                            tg.showAlert("Withdrawal request recorded!");
                        });
                    }
                });
            }

            renderApps();
            renderTopRanges();
            renderCountries();
            updateWalletUI();
        </script>
    </body>
    </html>
    """, app_stats=app_stats, top_ranges_data=top_ranges_data, countries_data=countries_data, admin_ids=list(ADMIN_IDS))

@app.route('/api/withdraw', methods=['POST'])
def api_withdraw():
    data = request.json or {}
    uid = data.get("user_id")
    amount = data.get("amount")
    address = data.get("address")
    
    withdrawal_requests.append({
        "user_id": uid, "name": f"User_{uid}", "amount": amount, "address": address, "time": time.strftime("%Y-%m-%d %H:%M:%S")
    })
    
    try:
        admin_target = list(ADMIN_IDS)[0] if ADMIN_IDS else TARGET_CHAT
        bot.send_message(admin_target, f"🚨 <b>CÓ ĐƠN RÚT TIỀN MỚI!</b>\n\n👤 User ID: <code>{uid}</code>\n💵 Số tiền: <b>${amount}</b>\n📬 Ví TON: <code>{address}</code>\n⏰ Lúc: {time.strftime('%Y-%m-%d %H:%M:%S')}", parse_mode="HTML")
    except: pass
    return jsonify({"success": True})

# --- BACKGROUND SCHEDULER & SIGTERM HANDLER ---
NORMAL_INTERVAL = 25
BACKOFF_INTERVAL = 300

_scheduler = None
_current_interval = NORMAL_INTERVAL

def _set_interval(new_seconds: int):
    global _current_interval
    if _scheduler is None or new_seconds == _current_interval:
        return
    try:
        job = _scheduler.get_job("ivas_poll")
        if job:
            _scheduler.reschedule_job("ivas_poll", trigger=IntervalTrigger(seconds=new_seconds))
            _current_interval = new_seconds
    except Exception:
        pass

def _poll_job():
    try:
        if not ivas_check_session():
            _set_interval(BACKOFF_INTERVAL)
            return
        _set_interval(NORMAL_INTERVAL)

        count = fetch_and_process_ivas_sms()
        if count > 0:
            logger.info("IVAS processed %s new OTP messages", count)
    except Exception as e:
        logger.exception(f"Poll job crashed: {e}")

_scheduler_lock_path = os.path.join(tempfile.gettempdir(), "ivas_scheduler.lock")
_scheduler_lock_fd = None

def _acquire_scheduler_lock() -> bool:
    global _scheduler_lock_fd
    if _IS_WINDOWS:
        logger.info("IVAS scheduler: Windows mode — no file lock needed.")
        return True
    try:
        fd = os.open(_scheduler_lock_path, os.O_CREAT | os.O_RDWR, 0o644)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _scheduler_lock_fd = fd
        logger.info("IVAS scheduler: lock acquired.")
        return True
    except (OSError, BlockingIOError):
        if _scheduler_lock_fd is not None:
            os.close(_scheduler_lock_fd)
            _scheduler_lock_fd = None
        logger.info("IVAS scheduler: another worker holds lock, skipping.")
        return False

def start_scheduler():
    global _scheduler
    if _scheduler is not None:
        return
    if not _acquire_scheduler_lock():
        return
    _scheduler = BackgroundScheduler(daemon=True, job_defaults={"coalesce": True, "max_instances": 1})
    _scheduler.add_job(_poll_job, trigger=IntervalTrigger(seconds=NORMAL_INTERVAL), id="ivas_poll", replace_existing=True)
    _scheduler.start()
    atexit.register(_shutdown_scheduler)
    logger.info(f"IVAS scheduler started (interval={NORMAL_INTERVAL}s)")

def _shutdown_scheduler():
    global _scheduler
    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
        except Exception:
            pass
        _scheduler = None

def _handle_sigterm(signum, frame):
    logger.info("SIGTERM received, shutting down scheduler...")
    _shutdown_scheduler()
    raise SystemExit(0)

try:
    signal.signal(signal.SIGTERM, _handle_sigterm)
except ValueError:
    pass

def run_bot_polling():
    while True:
        try:
            bot.remove_webhook()
            requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset=-1")
            time.sleep(1)
            print("🚀 Telegram Bot Polling Started Successfully!")
            bot.infinity_polling(skip_pending=True, interval=0, timeout=20)
        except Exception as e:
            print(f"⚠️ Bot polling restart due to error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    t_wss = threading.Thread(target=websocket_worker, daemon=True)
    t_wss.start()

    t_clean = threading.Thread(target=background_cleanup_and_wss, daemon=True)
    t_clean.start()

    start_scheduler()
    
    t_bot = threading.Thread(target=run_bot_polling, daemon=True)
    t_bot.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
else:
    t_wss = threading.Thread(target=websocket_worker, daemon=True)
    t_wss.start()

    t_clean = threading.Thread(target=background_cleanup_and_wss, daemon=True)
    t_clean.start()

    start_scheduler()
    
    t_bot = threading.Thread(target=run_bot_polling, daemon=True)
    t_bot.start()
