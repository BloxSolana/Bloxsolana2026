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
import sqlite3

_IS_WINDOWS = platform.system() == "Windows"
if not _IS_WINDOWS:
    import fcntl
else:
    fcntl = None
    
import signal
from datetime import datetime, timedelta, timezone
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
def get_env(name, default=""):
    return os.getenv(name, default)

BOT_TOKEN = get_env("BOT_TOKEN", "YOUR_BOT_TOKEN")
FLASK_SECRET_KEY = get_env("FLASK_SECRET_KEY", "default_secret_key_12345")

ADMIN_IDS = set()
raw_admins = get_env("ADMIN_IDS", "")
if raw_admins:
    ADMIN_IDS = {int(item.strip()) for item in raw_admins.split(",") if item.strip().isdigit()}
else:
    ADMIN_IDS = {123456789}

TARGET_CHAT = int(get_env("TARGET_CHAT", "-1004341368656"))
WEBAPP_URL = get_env("WEBAPP_URL", "https://bloxsolana2026.onrender.com")
IVAS_REFRESH_TOKEN = get_env("IVAS_REFRESH_TOKEN", "")

# MK Network API v3 Config
MK_BASE = get_env("MK_BASE_URL", "https://mknetworkbd.com/api/v3/public")
MK_KEY = get_env("MKNETWORK_KEY", get_env("API_2OO9_KEY_DEFAULT", "badacaa33d287233567a49db"))

bot = telebot.TeleBot(token=BOT_TOKEN)

# --- DATABASE QUẢN LÝ ---
user_rentals = {}          
inventory_numbers = {}     
admin_state = {}           
user_configs = {}          

user_wallets = {}          
withdrawal_requests = []   
live_radar_logs = []       
otp_history = []           

app_stats = {
    "WhatsApp": 0, "ClickBank": 0, "Apple": 0, "Shopee": 0, "Facebook": 0,
    "TikTok": 0, "AUTHMSG": 0, "TALAPH": 0, "Uber": 0, "SPayLaterPH": 0,
    "Telegram": 0, "Google": 0, "Instagram": 0, "Discord": 0, "Zalo": 0
}
top_ranges_data = []
last_reset_time = time.time()

IVAS_BASE_URL = get_env("IVAS_BASE_URL", "https://www.ivasms.com").rstrip("/")
IVAS_COOKIE_ENV = "IVAS_COOKIE"
IVAS_COOKIE_FILE = get_env("IVAS_COOKIE_FILE", "/data/ivas_cookie.txt")
DEFAULT_TIMEOUT = 20

_ivas_session = None
_ivas_session_cookie_hash = None
_ivas_lock = threading.Lock()

# --- MK NETWORK API V3 CLIENT ---
class MKClient:
    """Wrapper kết nối API v3 chuẩn của MK Network theo spec."""
    def __init__(self, api_key: str = None, timeout: int = 30):
        self.api_key = api_key or MK_KEY
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "mknetwork-key": self.api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "MKNetworkBot/3.0",
        })

    def _request(self, method: str, path: str, **kwargs):
        url = f"{MK_BASE}{path}"
        try:
            resp = self.session.request(method, url, timeout=self.timeout, **kwargs)
            body = resp.json()
        except Exception as e:
            logger.error(f"MK API {method} {path} error: {e}")
            return None

        meta = body.get("meta", {})
        code = meta.get("code") or resp.status_code
        if code in (200, 201):
            return body.get("data")
        logger.warning(f"MK API {path} returned code {code}: {body.get('message')}")
        return None

    def whoami(self):
        return self._request("GET", "/whoami")

    def access_list(self, limit: int = 100, offset: int = 0):
        return self._request("GET", "/access_list", params={"limit": limit, "offset": offset})

    def access_list_all(self):
        items = []
        offset = 0
        while True:
            data = self.access_list(limit=100, offset=offset)
            if not data: break
            page = data.get("items", [])
            items.extend(page)
            pag = data.get("pagination", {})
            total = pag.get("total", len(items))
            offset += len(page)
            if offset >= total or not page: break
        return items

    def get_number(self, range_code: str):
        return self._request("POST", "/getnum/number", json={"range": range_code})

    def check_status(self, request_ids: list):
        if not request_ids: return None
        # Batch tối đa 100 ID/lần
        return self._request("POST", "/check/status", json={"request_ids": request_ids[:100]})

    def radar(self, q: str = None, limit: int = 25):
        params = {"limit": limit, "charts": "true"}
        if q: params["q"] = q
        return self._request("GET", "/radar", params=params)

# --- COUNTRY STATE MACHINE & AUTOMATIC RANGE MANAGER ---
class CountryState:
    def __init__(self, country: str, operator: str, range_code: str):
        self.country = country
        self.operator = operator
        self.range = range_code
        self.numbers = []  # Các dict: {"request_id": int, "number": str, "acquired_at": float}

    def prune_expired(self):
        now = time.time()
        self.numbers = [n for n in self.numbers if now - n["acquired_at"] < 900]

    def active_count(self):
        self.prune_expired()
        return len(self.numbers)

    def is_full(self):
        return self.active_count() >= 100

class CountryManager:
    def __init__(self, client: MKClient):
        self.client = client
        self.ranges = {}
        self._lock = threading.Lock()
        self.reload_inventory()

    def reload_inventory(self):
        items = self.client.access_list_all()
        with self._lock:
            for item in items:
                rcode = item.get("range")
                if rcode and rcode not in self.ranges:
                    self.ranges[rcode] = CountryState(
                        country=item.get("country", "Unknown"),
                        operator=item.get("operator", "Other"),
                        range_code=rcode
                    )
        logger.info(f"CountryManager: {len(self.ranges)} active ranges loaded from MK API.")

    def fetch_batch_auto(self):
        with self._lock:
            candidates = [r for r in self.ranges.values() if not r.is_full()]
            if not candidates:
                logger.info("All ranges are currently full (100 slot cap).")
                return 0
            state = min(candidates, key=lambda r: r.active_count())

        fetched = 0
        current_time = time.time()
        cname, flag, full_key = detect_country_info(state.range)

        if full_key not in inventory_numbers:
            inventory_numbers[full_key] = {"flag": flag, "name": cname, "numbers": []}

        for _ in range(20):
            if state.is_full(): break
            data = self.client.get_number(state.range)
            if not data: break
            
            req_id = data.get("request_id")
            num = data.get("number") or data.get("full_number")
            if req_id and num:
                # Ép kiểu int cho request_id
                req_id_int = int(req_id)
                with self._lock:
                    state.numbers.append({
                        "request_id": req_id_int,
                        "number": num,
                        "acquired_at": current_time
                    })
                inventory_numbers[full_key]["numbers"].append({
                    "phone": num,
                    "expires": current_time + 900,
                    "locked_by": None
                })
                fetched += 1

        logger.info(f"Auto-scraped {fetched} numbers for {state.country} ({state.range}). Active={state.active_count()}/100")
        return fetched

    def get_all_pending_ids(self):
        with self._lock:
            pids = []
            for r in self.ranges.values():
                r.prune_expired()
                pids.extend(n["request_id"] for n in r.numbers)
            return pids

    def remove_request_id(self, req_id: int):
        with self._lock:
            for r in self.ranges.values():
                r.numbers = [n for n in r.numbers if n["request_id"] != req_id]

mk_client = MKClient()
country_manager = CountryManager(mk_client)

# --- IVAS SMS COOKIE & SESSION HELPERS ---
def _parse_cookie_string(cookie_str: str) -> dict:
    result = {}
    if not cookie_str: return result
    try:
        sc = SimpleCookie()
        sc.load(cookie_str)
        for k, morsel in sc.items(): result[k] = morsel.value
    except Exception:
        for part in cookie_str.split(";"):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                result[k.strip()] = v.strip()
    return result

def _load_ivas_cookie() -> str:
    if os.path.exists(IVAS_COOKIE_FILE):
        try:
            with open(IVAS_COOKIE_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content: return content
        except Exception: pass
    return get_env(IVAS_COOKIE_ENV, "").strip()

def _write_cookie_to_file(cookie_str: str) -> bool:
    try:
        os.makedirs(os.path.dirname(IVAS_COOKIE_FILE), exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(IVAS_COOKIE_FILE), prefix=".ivas_cookie_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(cookie_str)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, IVAS_COOKIE_FILE)
        return True
    except Exception as e:
        logger.warning(f"IVAS: cannot persist cookie: {e}")
        return False

def _build_session_from_cookie(cookie_str: str):
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": f"{IVAS_BASE_URL}/portal/sms/received",
        "X-Requested-With": "XMLHttpRequest"
    })
    cookies = _parse_cookie_string(cookie_str)
    for name, value in cookies.items():
        s.cookies.set(name, value, domain="www.ivasms.com", path="/")
    retry = Retry(total=2, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s

def _get_ivas_session():
    global _ivas_session, _ivas_session_cookie_hash
    cookie_str = _load_ivas_cookie()
    current_hash = hashlib.sha256(cookie_str.encode()).hexdigest()
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
    if old:
        try: old.close()
        except Exception: pass

ivas_processed_ids = set()
ivas_processed_lock = threading.Lock()
ivas_health = {"connected": False, "last_check": None, "last_error": None, "details": "Initializing..."}

def ivas_check_session() -> bool:
    try:
        s = _get_ivas_session()
        resp = s.get(f"{IVAS_BASE_URL}/portal/sms/received", timeout=DEFAULT_TIMEOUT, allow_redirects=False)
        if resp.status_code in (401, 403, 302):
            with _ivas_lock:
                ivas_health.update({"connected": False, "last_check": int(time.time()), "last_error": f"HTTP {resp.status_code}", "details": "Expired"})
            return False
        with _ivas_lock:
            ivas_health.update({"connected": True, "last_check": int(time.time()), "last_error": None, "details": "Active"})
        return True
    except Exception as exc:
        with _ivas_lock:
            ivas_health.update({"connected": False, "last_check": int(time.time()), "last_error": str(exc), "details": str(exc)})
        return False

def fetch_and_process_ivas_sms():
    if not IVAS_BASE_URL: return 0
    now = datetime.now()
    payload = {"start_date": (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"), "end_date": now.strftime("%Y-%m-%d %H:%M:%S")}
    try:
        s = _get_ivas_session()
        response = s.post(f"{IVAS_BASE_URL}/portal/sms/received/getsms", data=payload, timeout=DEFAULT_TIMEOUT)
        if response.status_code in (401, 403): return 0
        result = response.json()
        messages = result.get("data", result.get("items", [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        
        processed = 0
        for item in messages:
            if not isinstance(item, dict): continue
            phone = str(item.get("phone", item.get("phone_number", "")))
            sender = str(item.get("sender") or item.get("service") or "Unknown")
            message = str(item.get("message", item.get("sms", item.get("text", ""))))
            if not phone or not message: continue

            event_id = hashlib.sha256(f"{phone}|{sender}|{message}".encode()).hexdigest()
            with ivas_processed_lock:
                if event_id in ivas_processed_ids: continue
                ivas_processed_ids.add(event_id)
                if len(ivas_processed_ids) > 10000: ivas_processed_ids.pop()

            cname, flag, _ = detect_country_info(phone)
            timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            try: loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            loop.run_until_complete(dispatch_update(sender, phone, message, timestamp_str, cname, flag))
            processed += 1
        return processed
    except Exception as exc:
        logger.warning(f"IVAS fetch error: {exc}")
        return 0

# --- COUNTRY DATABASE (195+ ISO) ---
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
    "998": ("Uzbekistan", "🇺🇿"), "678": ("Vanuatu", "🇻🇺"), "379": ("Vatican City", "🇻🇦"), "58": ("Venezuela", "🇻🇪"),
    "84": ("Vietnam", "🇻🇳"), "1284": ("Virgin Islands (UK)", "🇻🇬"), "1340": ("Virgin Islands (US)", "🇻🇮"),
    "967": ("Yemen", "🇾🇪"), "260": ("Zambia", "🇿🇲"), "263": ("Zimbabwe", "🇿🇼")
}

for code, (cname, flag) in country_db.items():
    full_key = f"{cname} {flag}"
    if full_key not in inventory_numbers:
        inventory_numbers[full_key] = {"flag": flag, "name": cname, "numbers": []}

def detect_country_info(phone_str):
    clean = re.sub(r'\D', '', str(phone_str))
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
        except Exception: pass

    try: bot.delete_message(message.chat.id, message.message_id)
    except Exception: pass

    welcome_text = "🔥 <b>FAST NODE • IVAS OTP GATEWAY PORTAL</b>\n\nWelcome to the ultimate real-time secure OTP platform!"
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

        # Tự động dọn dẹp số quá hạn 15 phút
        for key, data in inventory_numbers.items():
            for item in list(data["numbers"]):
                if item["expires"] > 0 and item["expires"] <= current_time:
                    user_rentals.pop(item["phone"], None)
                    data["numbers"].remove(item)
                    
        # Tự động cào số cho các quốc gia chưa đủ slot 100 số
        country_manager.fetch_batch_auto()
        time.sleep(30)

async def dispatch_update(service, phone, msg, timestamp, country, flag, is_test=False):
    global app_stats, top_ranges_data, live_radar_logs
    clean_phone = str(phone).replace("+", "")
    masked = clean_phone[:6] + "****" + clean_phone[-3:] if len(clean_phone) > 7 else clean_phone
    match = re.search(r'\b(\d{3}[-\s]?\d{3}|\d{4,8})\b', str(msg))
    code = match.group(1) if match else "N/A"

    detected_service = parse_service_name(f"{service} {msg}")
    if detected_service in app_stats:
        app_stats[detected_service] += 1
    else:
        app_stats["AUTHMSG"] += 1

    entry = {
        "time": timestamp,
        "country": country,
        "flag": flag,
        "phone": masked,
        "service": detected_service,
        "code": code,
        "message": msg
    }
    live_radar_logs.insert(0, entry)
    otp_history.append(entry)
    if len(live_radar_logs) > 50: live_radar_logs.pop()
    if len(otp_history) > 200: otp_history.pop(0)

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
    except Exception: pass

    if clean_phone in user_rentals:
        owner_id = user_rentals[clean_phone]
        private_caption = f"🔔 <b>[REAL-TIME PRIVATE EXCLUSIVE OTP ($0.008 EARNED)]</b>\n\n" + caption
        try:
            await asyncio.to_thread(bot.send_message, chat_id=owner_id, text=private_caption, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)
        except Exception: pass

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
        except Exception: pass

    while True:
        for uid, cfg in user_configs.items():
            ws_url = cfg.get("ws_url")
            if ws_url and ws_url.startswith("wss://"):
                try:
                    wsapp = websocket.WebSocketApp(ws_url, on_message=on_message)
                    wsapp.run_forever()
                except Exception: pass
        time.sleep(15)

# --- FLASK SERVER & WEB APP ---
app = Flask(__name__)
app.config["SECRET_KEY"] = FLASK_SECRET_KEY

def verify_telegram_init_data(init_data: str):
    if not init_data or not BOT_TOKEN: return None
    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed.pop("hash", None)
        if not received_hash: return None
        data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(parsed.items()))
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode("utf-8"), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calculated_hash, received_hash): return None
        user_data = json.loads(parsed.get("user", "{}"))
        return {"user_id": int(user_data.get("id", 0)), "user": user_data}
    except Exception: return None

def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        init_data = request.headers.get("X-Telegram-Init-Data", "")
        auth_result = verify_telegram_init_data(init_data)
        if not auth_result or auth_result["user_id"] not in ADMIN_IDS:
            return jsonify({"success": False, "error": "Unauthorized Admin access required"}), 403
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

@app.route('/api/config/update', methods=['POST'])
@require_admin
def api_config_update():
    data = request.json or {}
    base_url = data.get("base_url")
    token_or_cookie = data.get("token_or_cookie")
    
    global IVAS_BASE_URL
    if base_url: IVAS_BASE_URL = base_url.strip().rstrip("/")
    if token_or_cookie:
        _write_cookie_to_file(token_or_cookie.strip())
        _invalidate_session()
        
    return jsonify({"success": True, "message": "Cập nhật cấu hình thành công!"})

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
        <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Fast Node • Portal Dashboard</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            :root { --bg: #0f172a; --card: #1e293b; --orange-bar: #f59e0b; --border: #334155; --text: #f8fafc; --muted: #94a3b8; --green: #22c55e; --red: #ef4444; }
            body { background: var(--bg); color: var(--text); font-family: sans-serif; margin: 0; padding: 0; }
            .top-bar { background: var(--orange-bar); color: #000; padding: 12px; font-weight: bold; display: flex; justify-content: space-between; }
            .sidebar { position: fixed; top: 0; left: -260px; width: 250px; height: 100%; background: #131c2e; border-right: 1px solid var(--border); transition: 0.3s; z-index: 1000; padding-top: 20px; }
            .sidebar.open { left: 0; }
            .menu-link { display: block; padding: 14px; color: var(--text); text-decoration: none; font-weight: bold; border-bottom: 1px solid var(--border); cursor: pointer; }
            .content-container { padding: 12px; }
            .view-section { display: none; }
            .view-section.active { display: block; }
            .widget-card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 14px; margin-bottom: 12px; }
            .widget-title { font-size: 14px; font-weight: bold; color: #f59e0b; margin-bottom: 10px; border-bottom: 1px solid var(--border); padding-bottom: 6px; }
            .btn { background: var(--green); color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: bold; cursor: pointer; width: 100%; }
        </style>
    </head>
    <body>
        <div class="top-bar">
            <div><button onclick="toggleSidebar()" style="background:none;border:none;font-size:18px;cursor:pointer;">☰</button> <span>Fast Node • Portal</span></div>
            <span id="headerBalance">Balance: $0.000</span>
        </div>

        <div class="sidebar" id="sidebarDrawer">
            <div style="padding:15px;font-weight:bold;color:#38bdf8;">📁 Menu</div>
            <a class="menu-link" onclick="switchView('dashboardView')">📊 Dashboard</a>
            <a class="menu-link" onclick="switchView('getNumberView')">🌍 Get Number (195+)</a>
            <a class="menu-link" id="adminPanelSidebarLink" style="display:none; color:#fbbf24;" onclick="switchView('adminPanelView')">👑 ADMIN PANEL</a>
        </div>

        <div class="content-container">
            <div id="dashboardView" class="view-section active">
                <div class="widget-card">
                    <div class="widget-title">Command Center Metrics</div>
                    <p>Live synchronized routing & telemetry connected to MK Network API v3.</p>
                </div>
            </div>
            <div id="adminPanelView" class="view-section">
                <div class="widget-card">
                    <div class="widget-title">👑 Admin Control Panel</div>
                    <p>Telemetric data synced with active worker processes.</p>
                </div>
            </div>
            <div id="getNumberView" class="view-section">
                <div class="widget-card">
                    <div class="widget-title">📦 Inventory Stock</div>
                    <div id="countryList"></div>
                </div>
            </div>
        </div>

        <script>
            let tg = window.Telegram.WebApp; tg.expand();
            let adminIds = {{ admin_ids | tojson }};
            let userTgId = tg.initDataUnsafe && tg.initDataUnsafe.user ? Number(tg.initDataUnsafe.user.id) : 0;
            if (adminIds.includes(userTgId)) document.getElementById('adminPanelSidebarLink').style.display = 'block';

            function toggleSidebar() { document.getElementById('sidebarDrawer').classList.toggle('open'); }
            function switchView(id) {
                document.querySelectorAll('.view-section').forEach(el => el.classList.remove('active'));
                document.getElementById(id).classList.add('active');
                toggleSidebar();
            }
        </script>
    </body>
    </html>
    """, admin_ids=list(ADMIN_IDS))

# --- BACKGROUND SCHEDULER ---
def _poll_job():
    try:
        # 1. Cào OTP từ MK Network API v3 (Post batch request_id)
        pids = country_manager.get_all_pending_ids()
        if pids:
            res = mk_client.check_status(pids)
            if res and "results" in res:
                for r in res["results"]:
                    if r.get("status") == "success":
                        req_id = r.get("request_id")
                        code = r.get("otp_code")
                        msg = r.get("full_sms", "")
                        num = r.get("number", "")
                        cname = r.get("country", "Unknown")
                        _, flag, _ = detect_country_info(num)
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        asyncio.run(dispatch_update("MKNetwork", num, msg or f"Code: {code}", timestamp, cname, flag))
                        country_manager.remove_request_id(req_id)
                    elif r.get("status") in ("expired", "not_found"):
                        country_manager.remove_request_id(r.get("request_id"))

        # 2. Quét OTP từ IVAS SMS Portal
        if ivas_check_session():
            fetch_and_process_ivas_sms()
    except Exception as e:
        logger.exception(f"Poll job error: {e}")

def start_scheduler():
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(_poll_job, trigger=IntervalTrigger(seconds=25), id="master_poll", replace_existing=True)
    scheduler.start()

def run_bot_polling():
    while True:
        try:
            bot.remove_webhook()
            bot.infinity_polling(skip_pending=True, interval=0, timeout=20)
        except Exception as e:
            time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=websocket_worker, daemon=True).start()
    threading.Thread(target=background_cleanup_and_wss, daemon=True).start()
    start_scheduler()
    threading.Thread(target=run_bot_polling, daemon=True).start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
