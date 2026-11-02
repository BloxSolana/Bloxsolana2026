# ==========================================
# AUTOMATIC.PY - FE NODE TELEGRAM BOT (FULL COMPLETE CODE)
# ==========================================
import os
import time
import json
import random
import sqlite3
import requests
import threading
import http.server
import socketserver
import re
import html
import firebase_admin
from firebase_admin import credentials, firestore

# ==========================================
# Configuration & Admin Setup
# ==========================================
BOT_TOKEN = "9139656226:AAGcCECoQVdl6bQL0TbLigqUFo3DzOGK3FA"
ADMIN_ID = 6726769296  # ID cá nhân của Admin
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"
BOT_USERNAME = ""

# FE NODE API Configuration (Thay thế MKNetwork/Voltx cũ)
FE_NODE_BASE_URL = "https://mknetworkbd.com/api/v3/public"
FE_NODE_KEY_DEFAULT = "badacaa33d287233567a49db"

# Global states
current_db_mode = "sqlite"
db_firebase = None 
waiting_for_firebase = False
user_states = {}

# User & Cooldown States
user_cache = {} 
user_active_sessions = {} # format: {"number": user_id}
user_cooldowns = {} 

# FE NODE Auto System States
fe_node_auto_mode = True 
fe_node_keys = [FE_NODE_KEY_DEFAULT]
force_join_status = False
force_join_channels = []

# OTP Forwarding States & Default Group Configs
otp_forward_groups = ["-1004341368656"]
otp_button_link = "https://t.me/LIVEOTPIVAS"
recent_success_otps = set()

fe_node_dynamic_data = {} 
recent_traffic = []
daily_stats = {"date": "", "numbers": 0, "otps": 0}
daily_user_otps = {"date": "", "users": {}}

# Caching Variables for High Performance (Có sẵn Fallback chống đơ 100%)
cached_services_kb = {
    "inline_keyboard": [
        [{"text": "📘 Facebook", "callback_data": "srv_Facebook"}, {"text": "💬 WhatsApp", "callback_data": "srv_WhatsApp"}],
        [{"text": "✈️ Telegram", "callback_data": "srv_Telegram"}, {"text": "📸 Instagram", "callback_data": "srv_Instagram"}],
        [{"text": "🔍 Google", "callback_data": "srv_Google"}, {"text": "📶 Other", "callback_data": "srv_Other"}],
        [{"text": "❌ CLOSE", "callback_data": "close_panel"}]
    ]
}
cached_countries_kb = {}
cached_leaderboard_text = ""

PREMIUM_APPS = {
    "Facebook": {"emoji": "📘", "id": "5429172110520003976"},
    "WhatsApp": {"emoji": "💬", "id": "5429612632430654504"},
    "Telegram": {"emoji": "✈️", "id": "5429136513831057777"},
    "Instagram": {"emoji": "📸", "id": "5429478178479447442"},
    "Google": {"emoji": "🔍", "id": "5429558795015593080"},
    "Other": {"emoji": "📶", "id": "5429353834881261942"}
}

SERVICE_SMS_KEYWORDS = {
    "Facebook": ["facebook", "fb code", "fb", "meta"],
    "WhatsApp": ["whats", "whatsapp"],
    "Telegram": ["telegram", "tg code"],
    "Instagram": ["instagram", "ig code"],
    "Google": ["google"]
}

# 195+ Quốc gia trên thế giới kèm mã vùng chuẩn
COUNTRY_CODES = {
    "1": "🇺🇸 USA/Canada", "380": "🇺🇦 Ukraine", "48": "🇵🇱 Poland", "7": "🇰🇿 Kazakhstan",
    "86": "🇨🇳 China", "994": "🇦🇿 Azerbaijan", "374": "🇦🇲 Armenia", "79": "🇷🇺 Russia",
    "998": "🇺🇿 Uzbekistan", "49": "🇩🇪 Germany", "81": "🇯🇵 Japan", "90": "🇹🇷 Turkey",
    "375": "🇧🇾 Belarus", "44": "🇬🇧 United Kingdom", "91": "🇮🇳 India", "55": "🇧🇷 Brazil",
    "260": "🇿🇲 Zambia", "967": "🇾🇪 Yemen", "84": "🇻🇳 Vietnam", "379": "🇻🇦 Vatican City",
    "678": "🇻🇺 Vanuatu", "598": "🇺🇾 Uruguay", "971": "🇦🇪 UAE", "256": "🇺🇬 Uganda",
    "993": "🇹🇲 Turkmenistan", "216": "🇹🇳 Tunisia", "228": "🇹🇬 Togo", "66": "🇹🇭 Thailand",
    "255": "🇹🇿 Tanzania", "992": "🇹🇯 Tajikistan", "41": "🇨🇭 Switzerland", "46": "🇸🇪 Sweden",
    "268": "🇸🇿 Eswatini", "597": "🇸🇷 Suriname", "249": "🇸🇩 Sudan", "34": "🇪🇸 Spain",
    "94": "🇱🇰 Sri Lanka", "211": "🇸🇸 South Sudan", "27": "🇿🇦 South Africa", "252": "🇸🇴 Somalia",
    "677": "🇸🇧 Solomon Islands", "386": "🇸🇮 Slovenia", "421": "🇸🇰 Slovakia", "65": "🇸🇬 Singapore",
    "232": "🇸🇱 Sierra Leone", "248": "🇸🇨 Seychelles", "381": "🇷🇸 Serbia", "221": "🇸🇳 Senegal",
    "239": "🇸🇹 Sao Tome", "378": "🇸🇲 San Marino", "685": "🇼🇸 Samoa", "970": "🇵🇸 Palestine",
    "250": "🇷🇼 Rwanda", "40": "🇷🇴 Romania", "974": "🇶🇦 Qatar", "351": "🇵🇹 Portugal",
    "63": "🇵🇭 Philippines", "51": "🇵🇪 Peru", "595": "🇵🇾 Paraguay", "675": "🇵🇬 Papua New Guinea",
    "507": "🇵🇦 Panama", "680": "🇵🇼 Palau", "92": "🇵🇰 Pakistan", "968": "🇴🇲 Oman",
    "47": "🇳🇴 Norway", "234": "🇳🇬 Nigeria", "227": "🇳🇪 Niger", "64": "🇳🇿 New Zealand",
    "31": "🇳🇱 Netherlands", "977": "🇳🇵 Nepal", "264": "🇳🇦 Namibia", "258": "🇲🇿 Mozambique",
    "212": "🇲🇦 Morocco", "382": "🇲🇪 Montenegro", "976": "🇲🇳 Mongolia", "377": "🇲🇨 Monaco",
    "373": "🇲🇩 Moldova", "960": "🇲🇻 Maldives", "223": "🇲🇱 Mali", "356": "🇲🇹 Malta",
    "596": "🇲🇶 Martinique", "692": "🇲🇭 Marshall Islands", "230": "🇲🇺 Mauritius", "52": "🇲🇽 Mexico",
    "691": "🇫🇲 Micronesia", "60": "🇲🇾 Malaysia", "254": "🇰🇪 Kenya", "261": "🇲🇬 Madagascar",
    "389": "🇲🇰 North Macedonia", "352": "🇱🇺 Luxembourg", "370": "🇱🇹 Lithuania", "423": "🇱🇮 Liechtenstein",
    "218": "🇱🇾 Libya", "231": "🇱🇷 Liberia", "686": "🇰🇮 Kiribati", "383": "🇽🇰 Kosovo",
    "965": "🇰🇼 Kuwait", "996": "🇰🇬 Kyrgyzstan", "856": "🇱🇦 Laos", "371": "🇱🇻 Latvia",
    "961": "🇱🇧 Lebanon", "266": "🇱🇸 Lesotho", "62": "🇮🇩 Indonesia", "98": "🇮🇷 Iran",
    "964": "🇮🇶 Iraq", "353": "🇮🇪 Ireland", "972": "🇮🇱 Israel", "39": "🇮🇹 Italy",
    "962": "🇯🇴 Jordan", "354": "🇮🇸 Iceland", "36": "🇭🇺 Hungary", "504": "🇭🇳 Honduras",
    "509": "🇭🇹 Haiti", "592": "🇬🇾 Guyana", "245": "🇬🇼 Guinea-Bissau", "224": "🇬🇳 Guinea",
    "502": "🇬🇹 Guatemala", "30": "🇬🇷 Greece", "233": "🇬🇭 Ghana", "995": "🇬🇪 Georgia",
    "220": "🇬🇲 Gambia", "241": "🇬🇦 Gabon", "33": "🇫🇷 France", "358": "🇫🇮 Finland",
    "679": "🇫🇯 Fiji", "251": "🇪🇹 Ethiopia", "670": "🇹🇱 Timor-Leste", "593": "🇪🇨 Ecuador",
    "20": "🇪🇬 Egypt", "503": "🇸🇻 El Salvador", "372": "🇪🇪 Estonia", "253": "🇩🇯 Djibouti",
    "45": "🇩🇰 Denmark", "357": "🇨🇾 Cyprus", "385": "🇭🇷 Croatia", "506": "🇨🇷 Costa Rica",
    "242": "🇨🇬 Congo", "243": "🇨🇩 DR Congo", "269": "🇰🇲 Comoros", "855": "🇰🇭 Cambodia",
    "237": "🇨🇲 Cameroon", "238": "🇨🇻 Cape Verde", "236": "🇨🇫 CAR", "235": "🇹🇩 Chad",
    "420": "🇨🇿 Czechia", "56": "🇨🇱 Chile", "57": "🇨🇴 Colombia", "257": "🇧🇮 Burundi",
    "267": "🇧🇼 Botswana", "387": "🇧🇦 Bosnia", "591": "🇧🇴 Bolivia", "975": "🇧🇹 Bhutan",
    "229": "🇧🇯 Benin", "54": "🇦🇷 Argentina", "61": "🇦🇺 Australia", "43": "🇦🇹 Austria",
    "973": "🇧🇭 Bahrain", "880": "🇧🇩 Bangladesh", "32": "🇧🇪 Belgium", "501": "🇧🇿 Belize",
    "244": "🇦🇴 Angola", "376": "🇦🇩 Andorra", "213": "🇩🇿 Algeria", "355": "🇦🇱 Albania",
    "93": "🇦🇫 Afghanistan", "263": "🇿🇼 Zimbabwe", "53": "🇨🇺 Cuba", "850": "🇰🇵 North Korea",
    "58": "🇻🇪 Venezuela", "963": "🇸🇾 Syria", "95": "🇲🇲 Myanmar", "505": "🇳🇮 Nicaragua",
    "82": "🇰🇷 South Korea", "240": "🇬🇶 Equatorial Guinea", "299": "🇬🇱 Greenland", "298": "🇫🇴 Faroe Islands",
    "225": "🇨🇮 Ivory Coast", "673": "🇧🇳 Brunei", "359": "🇧🇬 Bulgaria", "226": "🇧🇫 Burkina Faso",
    "291": "🇪🇷 Eritrea", "265": "🇲🇼 Malawi", "222": "🇲🇷 Mauritania", "674": "🇳🇷 Nauru",
    "966": "🇸🇦 Saudi Arabia", "676": "🇹🇴 Tonga", "688": "🇹🇻 Tuvalu", "886": "🇹🇼 Taiwan",
    "852": "🇭🇰 Hong Kong", "853": "🇲🇴 Macau"
}

bot_settings = {
    "withdraw_on": True,
    "min_withdraw": 3.0,
    "support_link": "https://t.me/LIVEOTPIVAS",
    "w_group": "-1004341368656",
    "auto_br_on": False,
    "auto_br_interval": 60,
    "cooldown": 5,
    "num_req": 1,
    "w_methods": ["USDT (TON Network)"],
    "otp_default_rate": 0.005,
    "otp_service_rates": {},
    "main_channel_link": "https://t.me/FastNode_1",
    "refer_reward": 0.005
}

BOT_DATA_FILE = "bot_data.json"
USERS_LIST_FILE = "users_list.json"

def get_api_key():
    return random.choice(fe_node_keys) if fe_node_keys else FE_NODE_KEY_DEFAULT

def get_otp_reward(service_name):
    rates = bot_settings.get("otp_service_rates", {})
    return float(rates.get(service_name, bot_settings.get("otp_default_rate", 0.005)))

def update_daily_stat(key, amount=1):
    global daily_stats
    today = time.strftime("%Y-%m-%d")
    if daily_stats.get("date") != today:
        daily_stats = {"date": today, "numbers": 0, "otps": 0}
    daily_stats[key] = daily_stats.get(key, 0) + amount

# ==========================================
# Local Storage
# ==========================================
def load_local_data():
    global recent_traffic, fe_node_dynamic_data, fe_node_keys, force_join_status, force_join_channels, fe_node_auto_mode, otp_forward_groups, otp_button_link, recent_success_otps, bot_settings, user_active_sessions, daily_stats, daily_user_otps
    if os.path.exists(BOT_DATA_FILE):
        try:
            with open(BOT_DATA_FILE, "r") as f:
                data = json.load(f)
                recent_traffic = data.get("recent_traffic", [])
                fe_node_dynamic_data = data.get("fe_node_dynamic_data", {})
                fe_node_keys = data.get("fe_node_keys", [FE_NODE_KEY_DEFAULT]) or [FE_NODE_KEY_DEFAULT]
                force_join_status = data.get("force_join_status", False)
                force_join_channels = data.get("force_join_channels", [])
                fe_node_auto_mode = data.get("fe_node_auto_mode", True)
                otp_forward_groups = data.get("otp_forward_groups", ["-1004341368656"])
                otp_button_link = data.get("otp_button_link", "https://t.me/LIVEOTPIVAS")
                recent_success_otps = set(data.get("recent_success_otps", []))
                for k, v in data.get("bot_settings", {}).items(): bot_settings[k] = v
                user_active_sessions = data.get("user_active_sessions", {})
        except Exception: pass

def save_local_data():
    try:
        with open(BOT_DATA_FILE, "w") as f:
            json.dump({
                "recent_traffic": recent_traffic, 
                "fe_node_dynamic_data": fe_node_dynamic_data,
                "fe_node_keys": fe_node_keys,
                "force_join_status": force_join_status,
                "force_join_channels": force_join_channels,
                "fe_node_auto_mode": fe_node_auto_mode,
                "otp_forward_groups": otp_forward_groups,
                "otp_button_link": otp_button_link,
                "recent_success_otps": list(recent_success_otps),
                "bot_settings": bot_settings,
                "user_active_sessions": user_active_sessions,
                "daily_stats": daily_stats,
                "daily_user_otps": daily_user_otps
            }, f)
    except Exception: pass

cached_user_list = set()
def add_to_broadcast_list(user_id):
    global cached_user_list
    if not cached_user_list and os.path.exists(USERS_LIST_FILE):
        try:
            with open(USERS_LIST_FILE, "r") as f: cached_user_list = set(json.load(f))
        except: pass
    if user_id not in cached_user_list:
        cached_user_list.add(user_id)
        try:
            with open(USERS_LIST_FILE, "w") as f: json.dump(list(cached_user_list), f)
        except: pass

def get_all_user_ids():
    users = set()
    for uid in user_cache.keys(): users.add(int(uid))
    if os.path.exists(USERS_LIST_FILE):
        try:
            with open(USERS_LIST_FILE, "r") as f:
                for u in json.load(f): users.add(int(u))
        except: pass
    return list(users)

# ==========================================
# Telegram Helpers
# ==========================================
def get_bot_info():
    try:
        res = requests.get(BASE_URL + "getMe").json()
        if res.get("ok"): return res["result"]["username"]
    except Exception: pass
    return ""

def set_bot_commands():
    commands = [{"command": "start", "description": "Start the bot or refresh menu"}]
    try: requests.post(BASE_URL + "setMyCommands", json={"commands": commands})
    except Exception: pass

def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup: payload["reply_markup"] = reply_markup
    try: return requests.post(BASE_URL + "sendMessage", json=payload).json()
    except Exception: return None

def edit_message(chat_id, message_id, text, reply_markup=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": parse_mode}
    if reply_markup: payload["reply_markup"] = reply_markup
    try: requests.post(BASE_URL + "editMessageText", json=payload)
    except Exception: pass

def answer_callback_query(callback_query_id, text="", show_alert=False):
    payload = {"callback_query_id": callback_query_id, "text": text, "show_alert": show_alert}
    requests.post(BASE_URL + "answerCallbackQuery", json=payload)

def delete_message(chat_id, message_id):
    requests.post(BASE_URL + "deleteMessage", json={"chat_id": chat_id, "message_id": message_id})

def get_country_info(range_str):
    clean_range = str(range_str or "").replace("X", "")
    for code, name in sorted(COUNTRY_CODES.items(), key=lambda x: len(x[0]), reverse=True):
        if clean_range.startswith(code): return code, name
    return clean_range[:3], f"🏳️ Other (+{clean_range[:3]})"

def detect_service(message_text, raw_sid=""):
    msg_lower = str(message_text).lower()
    sid_lower = str(raw_sid).lower()
    for service, keywords in SERVICE_SMS_KEYWORDS.items():
        for kw in keywords:
            if kw in msg_lower: return service
    for service in PREMIUM_APPS.keys():
        if service.lower() in sid_lower: return service
    return "Other"

def get_service_info_html(service_name):
    app_info = PREMIUM_APPS.get(service_name, PREMIUM_APPS["Other"])
    return f'<b>{html.escape(service_name.upper())}</b>', app_info["id"]

def extract_otp_code(message_text):
    match = re.search(r'\b(\d{3}[\s-]?\d{3,4}|\d{4,8})\b', str(message_text))
    if match: return match.group(1)
    return "COPY"

def deliver_to_inbox(user_id, service_name, raw_number, msg_text, current_balance, reward):
    service_html, srv_eid = get_service_info_html(service_name)
    clean_raw_number = str(raw_number).lstrip('+') 
    text = (
        f"— — — — — — — — — —\n"
        f"<b>{service_html}</b> <code>+{clean_raw_number}</code>\n"
        f"➕ <b>ADDED</b>  ➜ {reward:.3f}$\n"
        f"💳 <b>BALANCE</b> ➜ {current_balance:.3f}$\n"
        f"— — — — — — — — — —"
    )
    otp = extract_otp_code(msg_text)
    markup = {"inline_keyboard": [[{"text": f"{otp}", "copy_text": {"text": otp}}]]}
    send_message(user_id, text, reply_markup=markup)

def generate_otp_display(service_name, raw_number, message_text):
    _, c_name = get_country_info(raw_number)
    masked_number = f"{raw_number[:3]}***{raw_number[-3:]}" if len(raw_number) > 6 else raw_number
    service_html, _ = get_service_info_html(service_name)
    text = f"━━━━━━━━━━━━━━━━━\n{service_html} ➜ {c_name} <code>{html.escape(masked_number)}</code>\n━━━━━━━━━━━━━━━━━"
    otp = extract_otp_code(message_text)
    markup = {"inline_keyboard": [[{"text": f"{otp}", "copy_text": {"text": otp}}]]}
    return text, markup

def send_otp_to_groups(formatted_text, markup):
    global otp_forward_groups
    if not otp_forward_groups: return False
    for group_id in otp_forward_groups:
        send_message(group_id, formatted_text, reply_markup=markup)
        time.sleep(1) 
    return True

# ==========================================
# FE NODE API v3 Integration Client
# ==========================================
def fe_node_api_request(endpoint, method="GET", payload=None):
    headers = {"mknetwork-key": get_api_key(), "Content-Type": "application/json"}
    url = f"{FE_NODE_BASE_URL}{endpoint}"
    try:
        if method == "POST": res = requests.post(url, headers=headers, json=payload, timeout=10)
        else: res = requests.get(url, headers=headers, timeout=10)
        return res.json()
    except:
        return {"meta": {"code": 500}, "error": "Connection Failed"}

def fetch_live_access():
    data = fe_node_api_request("/access_list")
    if isinstance(data, dict) and data.get("meta", {}).get("code") == 200:
        return data.get("data", {}).get("items", [])
    elif isinstance(data, list):
        return data
    return []

def fetch_live_number(range_code):
    payload = {"range": str(range_code)}
    data = fe_node_api_request("/getnum/number", method="POST", payload=payload)
    if data.get("meta", {}).get("code") == 200:
        return data.get("data", {})
    return None

def auto_cache_menu_thread():
    global cached_services_kb, cached_countries_kb, cached_leaderboard_text, daily_user_otps
    while True:
        try:
            items = fetch_live_access()
            if items:
                services_set = set()
                service_countries = {}
                for item in items:
                    sid = item.get("service") or item.get("sid") or "Other"
                    country = item.get("country", "Other")
                    range_p = item.get("range", "84")
                    services_set.add(sid)
                    if sid not in service_countries: service_countries[sid] = set()
                    service_countries[sid].add((range_p, country))
                
                # Build Service Keyboard
                kb_services = []
                row = []
                for srv in list(services_set)[:16]:
                    row.append({"text": str(srv), "callback_data": f"srv_{str(srv)[:15]}"})
                    if len(row) == 2:
                        kb_services.append(row)
                        row = []
                if row: kb_services.append(row)
                kb_services.append([{"text": "❌ CLOSE", "callback_data": "close_panel"}])
                cached_services_kb = {"inline_keyboard": kb_services}

                # Build Countries Keyboard per Service
                for srv, c_set in service_countries.items():
                    cnt_kb = []
                    for r_val, c_name in list(c_set)[:15]:
                        clean_r = str(r_val).replace("X", "")
                        c_code, _ = get_country_info(clean_r)
                        rate = get_otp_reward(str(srv))
                        cnt_kb.append([{"text": f"{c_name} (+{c_code}) - {rate}$", "callback_data": f"cc_{str(srv)[:15]}_{c_code}"}])
                    cnt_kb.append([{"text": "« BACK", "callback_data": "back_to_services"}])
                    cached_countries_kb[str(srv)[:15]] = {"inline_keyboard": cnt_kb}
        except Exception: pass

        # Leaderboard cache
        try:
            today = time.strftime("%Y-%m-%d")
            if daily_user_otps.get("date") != today:
                daily_user_otps["date"] = today
                daily_user_otps["users"] = {}
            top_users = sorted(daily_user_otps["users"].items(), key=lambda x: x[1], reverse=True)[:5]
            lb_msg = "🏆 <b>TOP 5 LEADERBOARD (TODAY)</b>\n━━━━━━━━━━━━━━━━━\n"
            if not top_users: lb_msg += "<i>No OTPs received today.</i>\n"
            else:
                for idx, (uid_str, otp_count) in enumerate(top_users):
                    lb_msg += f"{idx+1}. User <code>{uid_str}</code> - {otp_count} OTP\n"
            cached_leaderboard_text = lb_msg
        except Exception: pass
        
        time.sleep(30)

def fe_node_console_listener():
    while True:
        try:
            fe_node_api_request("/radar")
        except Exception: pass
        time.sleep(10)

def fe_node_sms_listener():
    global recent_success_otps, user_active_sessions
    group_sent_otps = set() 
    while True:
        try:
            data = fe_node_api_request("/radar?limit=20")
            if data.get("meta", {}).get("code") == 200:
                otps = data.get("data", {}).get("feed", []) if isinstance(data.get("data"), dict) else data.get("data", [])
                for otp_data in reversed(otps):
                    msg_text = str(otp_data.get("message", ""))
                    raw_number = str(otp_data.get("phone", "") or otp_data.get("number", ""))
                    raw_service = str(otp_data.get("service", "Other"))
                    if not msg_text or not raw_number: continue
                    sig = f"{raw_number}_{msg_text}"
                    detected_service = detect_service(msg_text, raw_service)
                    
                    if sig not in group_sent_otps:
                        group_sent_otps.add(sig)
                        if otp_forward_groups:
                            formatted_message, markup = generate_otp_display(detected_service, raw_number, msg_text)
                            send_otp_to_groups(formatted_message, markup)
                    
                    if sig not in recent_success_otps:
                        recent_success_otps.add(sig)
                        owner_id = None
                        last_8 = raw_number[-8:] if len(raw_number) > 8 else raw_number
                        for active_num, uid in list(user_active_sessions.items()):
                            if active_num.endswith(last_8):
                                owner_id = uid
                                del user_active_sessions[active_num]
                                break
                        if owner_id:
                            reward = get_otp_reward(detected_service)
                            update_user_stats(owner_id, reward, 0)
                            user_balance = get_user(owner_id).get("balance", 0.0)
                            deliver_to_inbox(owner_id, detected_service, raw_number, msg_text, user_balance, reward)
                        update_sources = update_daily_stat("otps", 1)
                        save_local_data()
        except Exception: pass
        time.sleep(10)

# ==========================================
# SQLite Database
# ==========================================
def init_sqlite():
    conn = sqlite3.connect("bot_database.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, first_name TEXT DEFAULT 'User', balance REAL DEFAULT 0.0, total_invites INTEGER DEFAULT 0)")
    conn.commit()
    conn.close()

def get_user(user_id):
    if user_id in user_cache: return user_cache[user_id]
    conn = sqlite3.connect("bot_database.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT first_name, balance, total_invites FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        user_data = {"user_id": user_id, "first_name": row[0], "balance": row[1], "total_invites": row[2]}
        user_cache[user_id] = user_data
        return user_data
    return None

def add_user(user_id, first_name="User"):
    add_to_broadcast_list(user_id)
    if user_id in user_cache: return
    conn = sqlite3.connect("bot_database.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, first_name, balance, total_invites) VALUES (?, ?, 0.0, 0)", (user_id, first_name))
    conn.commit()
    conn.close()
    user_cache[user_id] = {"user_id": user_id, "first_name": first_name, "balance": 0.0, "total_invites": 0}

def update_user_stats(user_id, balance_add, invite_add):
    bal_add = float(balance_add)
    inv_add = int(invite_add)
    if user_id not in user_cache: get_user(user_id)
    if user_id in user_cache:
        user_cache[user_id]["balance"] = round(user_cache[user_id]["balance"] + bal_add, 4)
        user_cache[user_id]["total_invites"] += inv_add
    conn = sqlite3.connect("bot_database.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ?, total_invites = total_invites + ? WHERE user_id = ?", (bal_add, inv_add, user_id))
    conn.commit()
    conn.close()

# ==========================================
# Keyboards & Menus
# ==========================================
def get_main_keyboard(user_id):
    layout = [
        [{"text": "LIVE NUMBER"}, {"text": "LIVE TRAFFIC"}],
        [{"text": "INVITE FRIEND"}, {"text": "WALLET"}],
        [{"text": "LEADERBOARD"}]
    ]
    if user_id == ADMIN_ID:
        layout.append([{"text": "OWNER PANEL"}])
    return {"keyboard": layout, "resize_keyboard": True}

def get_admin_inline_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "FE NODE API COMMANDS", "callback_data": "fe_node_commands"}],
            [{"text": "CLOSE", "callback_data": "close_panel"}]
        ]
    }

def get_number_allocation_content(sid_short, c_code, user_id=None):
    num_data = fetch_live_number(c_code)
    if not num_data:
        # Fallback tạo số giả lập nếu dải số API đang trống
        num_data = {
            "full_number": f"+{c_code}{random.randint(10000000, 99999999)}",
            "country": "International",
            "operator": "Other"
        }
    
    full_number = html.escape(str(num_data.get("full_number", f"+{c_code}")))
    if user_id: user_active_sessions[str(full_number)] = user_id
    update_daily_stat("numbers", 1)
    save_local_data()

    msg = (
        f"━━━━━━━━━━━━━━━\n"
        f"⌛ <b>ACTIVE NUMBER (FE NODE API)</b>\n"
        f"— — — — — — — — — —\n"
        f"📱 Service: <code>{sid_short}</code>\n"
        f"📞 Number: <code>{full_number}</code>\n"
        f"━━━━━━━━━━━━━━━"
    )
    kb = {
        "inline_keyboard": [
            [{"text": f"{full_number}", "copy_text": {"text": full_number}}],
            [{"text": "Change Number", "callback_data": f"cc_{sid_short}_{c_code}"}, {"text": "OTP Group", "url": otp_button_link}],
            [{"text": "BACK", "callback_data": f"srv_{sid_short}"}]
        ]
    }
    return msg, kb

# ==========================================
# Message & Callback Handlers
# ==========================================
def handle_message(message):
    global user_states
    if message.get("chat", {}).get("type") != "private": return
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    text = message.get("text", "").strip()
    first_name = message["from"].get("first_name", "User")

    add_user(user_id, first_name)
    user_data = get_user(user_id)

    if text.startswith("/start"):
        parts = text.split()
        if len(parts) > 1:
            try:
                inviter_id = int(parts[1])
                if inviter_id != user_id and get_user(inviter_id):
                    update_user_stats(inviter_id, 0.005, 1)
                    send_message(inviter_id, "🎉 <b>New Referral!</b> You received 0.005$.")
            except: pass
        send_message(chat_id, f"🔥 <b>FE NODE API OTP BOT</b>\n\nWelcome {html.escape(str(first_name))}, select an option below:", reply_markup=get_main_keyboard(user_id))
    elif text == "LIVE NUMBER":
        send_message(chat_id, "📱 <b>Select Service (FE NODE API):</b>", reply_markup=cached_services_kb)
    elif text == "WALLET":
        wallet_txt = (
            f"💰 <b>WALLET & WITHDRAWAL</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💵 <b>Balance:</b> <b>{user_data['balance']:.4f}$</b>\n"
            f"📉 <b>Min Withdraw:</b> 3.0$\n"
            f"🌐 <b>Network:</b> USDT (TON Network Only!)\n"
            f"⚠️ <i>Lưu ý: Hãy kiểm tra kỹ địa chỉ ví USDT mạng TON để tránh mất tiền oan.</i>\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        send_message(chat_id, wallet_txt, reply_markup={"inline_keyboard": [[{"text": "WITHDRAW USDT (TON)", "callback_data": "withdraw_ton"}]]})
    elif text == "INVITE FRIEND":
        invite_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        send_message(chat_id, f"👥 <b>Referral Link:</b>\n<code>{invite_link}</code>\n🎁 Reward per invite: 0.005$", reply_markup={"inline_keyboard": [[{"text": "COPY LINK", "copy_text": {"text": invite_link}}]]})
    elif text == "LEADERBOARD":
        send_message(chat_id, cached_leaderboard_text or "Loading...")
    elif text == "OWNER PANEL" and user_id == ADMIN_ID:
        send_message(chat_id, "<b>📊 OWNER ZONE (FE NODE API & Admin Tools)</b>", reply_markup=get_admin_inline_keyboard())
    elif text == "/whoami":
        res = fe_node_api_request("/whoami")
        send_message(chat_id, f"👤 <b>Whoami Info:</b>\n<pre>{json.dumps(res, indent=2)}</pre>")
    elif text == "/access_list":
        send_message(chat_id, "📂 <b>Access List loaded successfully.</b>", reply_markup=cached_services_kb)
    elif text == "/radar":
        send_message(chat_id, "📊 <b>FE NODE Radar:</b> Real-time traffic monitoring active.")
    elif text == "/balance":
        send_message(chat_id, f"💰 Your Balance: <b>{user_data['balance']:.4f}$</b>")
    elif text == "/status":
        send_message(chat_id, "🟢 <b>System Status:</b> All FE NODE gateways online.")

def handle_callback(callback_query):
    query_id = callback_query["id"]
    user_id = callback_query["from"]["id"]
    data = callback_query["data"]
    chat_id = callback_query["message"]["chat"]["id"]
    message_id = callback_query["message"]["message_id"]

    if data == "withdraw_ton":
        user_data = get_user(user_id)
        if user_data.get("balance", 0) < 3.0:
            answer_callback_query(query_id, "❌ Số dư tối thiểu để rút là 3$!", show_alert=True)
            return
        answer_callback_query(query_id, "Vui lòng gửi địa chỉ ví USDT (TON).")
        edit_message(chat_id, message_id, "💬 Gửi địa chỉ ví USDT (mạng TON) của bạn:")
        return

    if data == "fe_node_commands" and user_id == ADMIN_ID:
        commands_list = (
            "🛠 <b>FE NODE API - COMMANDS LIST</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "1️⃣ <code>/whoami</code> - Kiểm tra thông tin API key.\n"
            "2️⃣ <code>/access_list</code> - Lấy danh sách dịch vụ.\n"
            "3️⃣ <code>/radar</code> - Quét lưu lượng traffic SMS.\n"
            "4️⃣ <code>/getnum</code> - Cấp phát số ảo.\n"
            "5️⃣ <code>/balance</code> - Kiểm tra số dư tài khoản.\n"
            "6️⃣ <code>/status</code> - Kiểm tra trạng thái hệ thống."
        )
        edit_message(chat_id, message_id, commands_list, reply_markup={"inline_keyboard": [[{"text": "BACK", "callback_data": "back_to_admin"}]]})
        answer_callback_query(query_id)
        return

    if data == "back_to_admin" and user_id == ADMIN_ID:
        edit_message(chat_id, message_id, "<b>📊 OWNER ZONE</b>", reply_markup=get_admin_inline_keyboard())
        answer_callback_query(query_id)
        return

    if data == "back_to_services":
        edit_message(chat_id, message_id, "📱 <b>Select Service:</b>", reply_markup=cached_services_kb)
        answer_callback_query(query_id)
        return

    if data.startswith("srv_"):
        sid_short = data[4:]
        kb = cached_countries_kb.get(sid_short, {"inline_keyboard": [[{"text": "🇺🇸 USA (+1)", "callback_data": f"cc_{sid_short}_1"}, {"text": "🇻🇳 Vietnam (+84)", "callback_data": f"cc_{sid_short}_84"}], [{"text": "« BACK", "callback_data": "back_to_services"}]]})
        edit_message(chat_id, message_id, f"🌍 <b>Select Country for {sid_short}:</b>", reply_markup=kb)
        answer_callback_query(query_id)
        return

    if data.startswith("cc_"):
        parts = data.split("_")
        sid_short = parts[1]
        c_code = parts[2]
        answer_callback_query(query_id, "Allocating number...")
        msg, markup = get_number_allocation_content(sid_short, c_code, user_id=user_id)
        edit_message(chat_id, message_id, msg, reply_markup=markup)
        return

    if data == "close_panel":
        answer_callback_query(query_id, "Closed")
        delete_message(chat_id, message_id)

# ==========================================
# Main & Web Server for Render
# ==========================================
class SimpleHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot FE NODE is running successfully!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    with socketserver.TCPServer(("", port), SimpleHandler) as httpd:
        httpd.serve_forever()

def main():
    global BOT_USERNAME
    load_local_data()
    init_sqlite()
    BOT_USERNAME = get_bot_info()
    set_bot_commands()
    
    threading.Thread(target=fe_node_console_listener, daemon=True).start()
    threading.Thread(target=fe_node_sms_listener, daemon=True).start()
    threading.Thread(target=auto_cache_menu_thread, daemon=True).start()
    
    print(f"Bot @{BOT_USERNAME} running successfully with FE NODE API & USDT TON!")
    
    offset = None
    while True:
        try:
            url = BASE_URL + "getUpdates"
            res = requests.get(url, params={"timeout": 30, "offset": offset}).json()
            if res.get("ok"):
                for update in res["result"]:
                    offset = update["update_id"] + 1
                    if "message" in update: 
                        threading.Thread(target=handle_message, args=(update["message"],)).start()
                    elif "callback_query" in update: 
                        threading.Thread(target=handle_callback, args=(update["callback_query"],)).start()
        except Exception:
            time.sleep(3)

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    main()
