# ==========================================
# AUTOMATIC.PY - FE NODE v3 FIXED & OPTIMIZED
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

# FE NODE API Configuration (Chuẩn v3 public)
FE_NODE_BASE_URL = "https://mknetworkbd.com/api/v3/public"
FE_NODE_KEY_DEFAULT = "badacaa33d287233567a49db"

# Global states
current_db_mode = "sqlite"
db_firebase = None 
waiting_for_firebase = False
user_states = {}

user_cache = {} 
user_active_sessions = {} 
user_cooldowns = {} 

fe_node_auto_mode = True 
fe_node_keys = [FE_NODE_KEY_DEFAULT]
force_join_status = False
force_join_channels = []

otp_forward_groups = ["-1004341368656"]
otp_button_link = "https://t.me/LIVEOTPIVAS"
recent_success_otps = set()

fe_node_dynamic_data = {} 
recent_traffic = []
daily_stats = {"date": "", "numbers": 0, "otps": 0}
daily_user_otps = {"date": "", "users": {}}

cached_services_kb = None
cached_countries_kb = {}
cached_leaderboard_text = ""

# ==========================================
# Admin Settings
# ==========================================
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
                loaded_keys = data.get("fe_node_keys", [])
                if loaded_keys: fe_node_keys = loaded_keys
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
                "recent_traffic": recent_traffic, "fe_node_dynamic_data": fe_node_dynamic_data,
                "fe_node_keys": fe_node_keys, "force_join_status": force_join_status,
                "force_join_channels": force_join_channels, "fe_node_auto_mode": fe_node_auto_mode,
                "otp_forward_groups": otp_forward_groups, "otp_button_link": otp_button_link,
                "recent_success_otps": list(recent_success_otps), "bot_settings": bot_settings,
                "user_active_sessions": user_active_sessions, "daily_stats": daily_stats,
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
# Telegram API Helpers
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
    payload = {"chat_id": chat_id, "text": apply_emojis(text), "parse_mode": parse_mode}
    if reply_markup: payload["reply_markup"] = reply_markup
    try: return requests.post(BASE_URL + "sendMessage", json=payload).json()
    except Exception: return None

def edit_message(chat_id, message_id, text, reply_markup=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": apply_emojis(text), "parse_mode": parse_mode}
    if reply_markup: payload["reply_markup"] = reply_markup
    try: requests.post(BASE_URL + "editMessageText", json=payload)
    except Exception: pass

def answer_callback_query(callback_query_id, text="", show_alert=False):
    payload = {"callback_query_id": callback_query_id, "text": text, "show_alert": show_alert}
    requests.post(BASE_URL + "answerCallbackQuery", json=payload)

def delete_message(chat_id, message_id):
    requests.post(BASE_URL + "deleteMessage", json={"chat_id": chat_id, "message_id": message_id})

# ==========================================
# Emojis & 195+ Countries Full Dataset
# ==========================================
GLOBAL_BODY_EMOJIS = {
    "➖": "5870818207383686839", "🚫": "5334807341109908955", "😒": "5334763399299506604",
    "🖥": "5334880948259427772", "🌐": "5334590977837403844", "🌟": "5337102391244263212",
    "🕓": "5336983442125001376", "⌛": "5337172996211648018", "💬": "5337302974806922068",
    "🔐": "5337255927735163754", "🍏": "5337132498965010628", "❔": "5336850036145823599",
    "⚠️": "5336944168944047463", "🔥": "5337267511261960341", "💸": "5429612421977253466",
    "📊": "5353032893096567467", "🔢": "5226929552319594190", "👤": "5352861489541714456",
    "📁": "5352721946054268944", "🚀": "5352597830089347330", "💎": "5352838545826420397",
    "📍": "5352922460897452503", "👋": "5353027129250453493", "✅": "5352694861990501856",
    "1️⃣": "5352651766288652742", "2️⃣": "5355186458418257716", "3️⃣": "5352867219028091093",
    "4️⃣": "5352566657216714037", "5️⃣": "5353086880835474989", "🇺🇸": "5913463998522592692", 
    "🇻🇳": "5913428887164949581", "🇬🇧": "5913443365499703513"
}

def apply_emojis(text):
    hidden = []
    def hide(match):
        hidden.append(match.group(0))
        return f"__TG_EMOJI_{len(hidden)-1}__"
    text = re.sub(r'<tg-emoji[^>]*>.*?</tg-emoji>', hide, text)
    for char, eid in GLOBAL_BODY_EMOJIS.items():
        text = text.replace(char, f'<tg-emoji emoji-id="{eid}">{char}</tg-emoji>')
    for i, h in enumerate(hidden):
        text = text.replace(f"__TG_EMOJI_{i}__", h)
    return text

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

def get_country_info(range_str):
    clean_range = str(range_str or "").replace("X", "").strip()
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
    return f'<tg-emoji emoji-id="{app_info["id"]}">{app_info["emoji"]}</tg-emoji> <b>{html.escape(service_name.upper())}</b>', app_info["id"]

def extract_otp_code(message_text):
    match = re.search(r'\b(\d{3}[\s-]?\d{3,4}|\d{4,8})\b', str(message_text))
    if match: return match.group(1)
    return "COPY"

def deliver_to_inbox(user_id, service_name, raw_number, msg_text, current_balance, reward):
    service_html, srv_eid = get_service_info_html(service_name)
    clean_raw_number = str(raw_number).lstrip('+') 
    text = (
        f"— — — — — — — — — —\n"
        f"<blockquote>{service_html} <code>+{clean_raw_number}</code></blockquote>\n"
        f"<blockquote><tg-emoji emoji-id=\"5420323438508155202\">➕</tg-emoji> <b>ADDED</b>  ➜ {reward:.3f}$</blockquote>\n"
        f"<blockquote><tg-emoji emoji-id=\"5190899075968441286\">💳</tg-emoji> <b>BALANCE</b> ➜ {current_balance:.3f}$</blockquote>\n"
        f"— — — — — — — — — —"
    )
    otp = extract_otp_code(msg_text)
    markup = {"inline_keyboard": [[{"text": f"{otp}", "icon_custom_emoji_id": srv_eid, "copy_text": {"text": otp}, "style": "success"}]]}
    send_message(user_id, text, reply_markup=markup)

def generate_otp_display(service_name, raw_number, message_text):
    c_code, c_name = get_country_info(raw_number)
    parts = c_name.split(" ", 1)
    country_emoji = parts[0]
    masked_number = f"{raw_number[:3]}DXA{raw_number[-3:]}" if len(raw_number) > 6 else raw_number
    service_html, srv_eid = get_service_info_html(service_name)
    
    text = (
        f"━━━━━━━━━━━━━━━━━\n"
        f"{service_html} ➜ {country_emoji} <code>{html.escape(masked_number)}</code>\n"
        f"━━━━━━━━━━━━━━━━━"
    )
    otp = extract_otp_code(message_text)
    clean_range = str(raw_number)[:5] if len(str(raw_number)) >= 5 else str(raw_number)
    deep_link = f"https://t.me/{BOT_USERNAME}?start=alloc_{clean_range}_{service_name.lower()}"
    
    markup = {"inline_keyboard": []}
    row1 = []
    main_channel_link = bot_settings.get("main_channel_link", "https://t.me/FastNode_1")
    if main_channel_link:
        row1.append({"text": "𝗖𝗛𝗔𝗡𝗡𝗘𝗟", "url": main_channel_link, "icon_custom_emoji_id": "5429353834881261942", "style": "primary"})
    row1.append({"text": f"{otp}", "icon_custom_emoji_id": srv_eid, "copy_text": {"text": otp}, "style": "success"})
    markup["inline_keyboard"].append(row1)
    markup["inline_keyboard"].append([
        {"text": "GET NUMBER", "url": deep_link, "icon_custom_emoji_id": "5429167978761461870", "style": "danger"}
    ])
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

def fetch_realtime_balance_from_web():
    """Lấy số dư chuẩn Real-Time 100% trực tiếp từ web qua /whoami của API v3"""
    try:
        data = fe_node_api_request("/whoami")
        if isinstance(data, dict) and data.get("meta", {}).get("code") == 200:
            user_info = data.get("data", {}).get("user", {})
            return float(user_info.get("balance", 0.0))
    except Exception: pass
    return None

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
    if isinstance(data, dict) and data.get("meta", {}).get("code") == 200:
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
                    country_raw = item.get("country", "International")
                    range_p = str(item.get("range", "84"))
                    
                    # Tự động nhận diện chuẩn mã vùng từ range thực tế
                    c_code, c_name = get_country_info(range_p)
                    services_set.add(sid)
                    if sid not in service_countries: service_countries[sid] = set()
                    service_countries[sid].add((range_p, c_name, c_code))
                
                kb_services = {"inline_keyboard": []}
                row = []
                styles = ["primary", "success", "danger"]
                style_idx = 0
                for srv in list(services_set)[:16]:
                    safe_srv = html.escape(str(srv))
                    row.append({"text": safe_srv, "callback_data": f"srv_{safe_srv[:15]}", "style": styles[style_idx % 3]})
                    style_idx += 1
                    if len(row) == 2:
                        kb_services["inline_keyboard"].append(row)
                        row = []
                if row: kb_services["inline_keyboard"].append(row)
                kb_services["inline_keyboard"].append([{"text": "CLOSE", "callback_data": "close_panel", "style": "danger"}])
                cached_services_kb = kb_services

                for srv, c_set in service_countries.items():
                    cnt_kb = {"inline_keyboard": []}
                    styles_c = ["primary", "success", "danger"]
                    style_idx_c = 0
                    rate = get_otp_reward(str(srv))
                    for r_val, c_name_full, c_code in list(c_set)[:15]:
                        cnt_kb["inline_keyboard"].append([{
                            "text": f"{c_name_full} (+{c_code}) - {rate}$",
                            "callback_data": f"cc_{str(srv)[:15]}_{r_val}",
                            "style": styles_c[style_idx_c % 3]
                        }])
                        style_idx_c += 1
                    cnt_kb["inline_keyboard"].append([{"text": "BACK", "callback_data": "back_to_services", "style": "danger"}])
                    cached_countries_kb[str(srv)[:15]] = cnt_kb
        except Exception: pass

        # Leaderboard cache real-time
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

        time.sleep(15)

def fe_node_console_listener():
    while True:
        try: fe_node_api_request("/radar")
        except Exception: pass
        time.sleep(10)

def fe_node_sms_listener():
    global recent_success_otps, user_active_sessions
    group_sent_otps = set() 
    while True:
        try:
            data = fe_node_api_request("/radar?limit=20")
            if isinstance(data, dict) and data.get("meta", {}).get("code") == 200:
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
                        update_daily_stat("otps", 1)
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
        [{"text": "LIVE NUMBER", "style": "danger"}, {"text": "LIVE TRAFFIC", "style": "primary"}],
        [{"text": "INVITE FRIEND", "style": "success"}, {"text": "WALLET", "style": "danger"}],
        [{"text": "LEADERBOARD", "style": "primary"}]
    ]
    if user_id == ADMIN_ID:
        layout.append([{"text": "OWNER PANEL", "style": "success"}])
    return {"keyboard": layout, "resize_keyboard": True}

def get_admin_inline_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "FE NODE API COMMANDS", "callback_data": "fe_node_commands", "style": "danger"}],
            [{"text": "CLOSE", "callback_data": "close_panel", "style": "danger"}]
        ]
    }

def get_number_allocation_content(sid_short, range_code, user_id=None):
    num_data = fetch_live_number(range_code)
    if not num_data:
        num_data = {
            "full_number": f"+{range_code}{random.randint(10000000, 99999999)}",
            "country": "International",
            "operator": "Other"
        }
    
    full_number = html.escape(str(num_data.get("full_number", f"+{range_code}")))
    if user_id: user_active_sessions[str(full_number)] = user_id
    update_daily_stat("numbers", 1)
    save_local_data()

    msg = (
        f"━━━━━━━━━━━━━━━\n"
        f"⌛ <b>ACTIVE NUMBER (FE NODE API v3)</b>\n"
        f"— — — — — — — — — —\n"
        f"📱 Service: <code>{sid_short}</code>\n"
        f"📞 Number: <code>{full_number}</code>\n"
        f"━━━━━━━━━━━━━━━"
    )
    kb = {
        "inline_keyboard": [
            [{"text": f"{full_number}", "copy_text": {"text": full_number}, "style": "primary"}],
            [{"text": "Change Number", "callback_data": f"cc_{sid_short}_{range_code}", "style": "danger"},
             {"text": "OTP Group", "url": otp_button_link, "style": "success"}],
            [{"text": "BACK", "callback_data": f"srv_{sid_short}", "style": "danger"}]
        ]
    }
    return msg, kb

# ==========================================
# Message & Callback Handlers
# ==========================================
def handle_message(message):
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
        kb = cached_services_kb or {"inline_keyboard": [[{"text": "📱 Telegram", "callback_data": "srv_Telegram"}, {"text": "📘 Facebook", "callback_data": "srv_Facebook"}], [{"text": "❌ CLOSE", "callback_data": "close_panel", "style": "danger"}]]}
        send_message(chat_id, "📱 <b>Select Service (FE NODE API v3):</b>", reply_markup=kb)
    elif text == "LIVE TRAFFIC":
        send_message(chat_id, "📊 <b>LIVE TRAFFIC (FE NODE Radar v3):</b>\n📡 Real-time monitoring active across active gateways.")
    elif text == "WALLET":
        # Lấy trực tiếp chuẩn Real-Time 100% từ Web qua endpoint /whoami
        real_balance = fetch_realtime_balance_from_web()
        display_bal = real_balance if real_balance is not None else user_data['balance']
        
        wallet_txt = (
            f"💰 <b>WALLET & WITHDRAWAL</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💵 <b>Balance:</b> <b>{display_bal:.4f}$</b>\n"
            f"📉 <b>Min Withdraw:</b> 3.0$\n"
            f"🌐 <b>Network:</b> USDT (TON Network Only!)\n"
            f"⚠️ <i>Lưu ý: Hãy kiểm tra kỹ địa chỉ ví USDT mạng TON để tránh mất tiền oan.</i>\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        send_message(chat_id, wallet_txt, reply_markup={"inline_keyboard": [[{"text": "WITHDRAW USDT (TON)", "callback_data": "withdraw_ton", "style": "success"}]]})
    elif text == "INVITE FRIEND":
        invite_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        send_message(chat_id, f"👥 <b>Referral Link:</b>\n<code>{invite_link}</code>\n🎁 Reward per invite: 0.005$", reply_markup={"inline_keyboard": [[{"text": "COPY LINK", "copy_text": {"text": invite_link}, "style": "success"}]]})
    elif text == "LEADERBOARD":
        send_message(chat_id, cached_leaderboard_text or "🏆 <b>TOP 5 LEADERBOARD</b>\n━━━━━━━━━━━━━━━━━\n<i>No OTPs received yet.</i>")
    elif text == "OWNER PANEL" and user_id == ADMIN_ID:
        send_message(chat_id, "<b>📊 OWNER ZONE (FE NODE API & Admin Tools)</b>", reply_markup=get_admin_inline_keyboard())
    elif text == "/whoami":
        res = fe_node_api_request("/whoami")
        send_message(chat_id, f"👤 <b>Whoami Info (Real-Time Web):</b>\n<pre>{json.dumps(res, indent=2)}</pre>")
    elif text == "/access_list":
        kb = cached_services_kb or {"inline_keyboard": [[{"text": "Telegram", "callback_data": "srv_Telegram"}]]}
        send_message(chat_id, "📂 <b>Access List loaded successfully.</b>", reply_markup=kb)
    elif text == "/radar":
        send_message(chat_id, "📊 <b>FE NODE Radar v3:</b> Real-time traffic monitoring active.")
    elif text == "/balance":
        real_balance = fetch_realtime_balance_from_web()
        display_bal = real_balance if real_balance is not None else user_data['balance']
        send_message(chat_id, f"💰 Real-Time Balance (Web API): <b>{display_bal:.4f}$</b>")
    elif text == "/status":
        send_message(chat_id, "🟢 <b>System Status:</b> All FE NODE gateways online and operational.")

def handle_callback(callback_query):
    query_id = callback_query["id"]
    user_id = callback_query["from"]["id"]
    data = callback_query["data"]
    chat_id = callback_query["message"]["chat"]["id"]
    message_id = callback_query["message"]["message_id"]

    if data == "withdraw_ton":
        real_balance = fetch_realtime_balance_from_web()
        user_data = get_user(user_id)
        bal = real_balance if real_balance is not None else user_data.get("balance", 0)
        if bal < 3.0:
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
        edit_message(chat_id, message_id, commands_list, reply_markup={"inline_keyboard": [[{"text": "BACK", "callback_data": "back_to_admin", "style": "danger"}]]})
        answer_callback_query(query_id)
        return

    if data == "back_to_admin" and user_id == ADMIN_ID:
        edit_message(chat_id, message_id, "<b>📊 OWNER ZONE</b>", reply_markup=get_admin_inline_keyboard())
        answer_callback_query(query_id)
        return

    if data == "back_to_services":
        kb = cached_services_kb or {"inline_keyboard": [[{"text": "📱 Telegram", "callback_data": "srv_Telegram"}], [{"text": "❌ CLOSE", "callback_data": "close_panel", "style": "danger"}]]}
        edit_message(chat_id, message_id, "📱 <b>Select Service:</b>", reply_markup=kb)
        answer_callback_query(query_id)
        return

    if data.startswith("srv_"):
        sid_short = data[4:]
        kb = cached_countries_kb.get(sid_short, {
            "inline_keyboard": [
                [{"text": "🇺🇸 USA (+1) - 0.005$", "callback_data": f"cc_{sid_short}_1", "style": "primary"},
                 {"text": "🇻🇳 Vietnam (+84) - 0.005$", "callback_data": f"cc_{sid_short}_84", "style": "success"}],
                [{"text": "« BACK", "callback_data": "back_to_services", "style": "danger"}]
            ]
        })
        edit_message(chat_id, message_id, f"🌍 <b>Select Country for {sid_short} (Dynamic Ranges):</b>", reply_markup=kb)
        answer_callback_query(query_id)
        return

    if data.startswith("cc_"):
        parts = data.split("_", 2)
        sid_short = parts[1]
        range_code = parts[2]
        answer_callback_query(query_id, "Allocating number...")
        msg, markup = get_number_allocation_content(sid_short, range_code, user_id=user_id)
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
        self.wfile.write(b"Bot FE NODE v3 is running successfully!")

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
    
    print(f"Bot @{BOT_USERNAME} running successfully with FE NODE API v3 & USDT TON!")
    
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
