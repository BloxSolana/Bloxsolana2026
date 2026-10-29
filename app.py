import requests
import time
import json
import random
import sqlite3
import os
import re
import html
import threading
import firebase_admin
from firebase_admin import credentials, firestore

# ==========================================
# Configuration (Fast Node • MK Network OTP)
# ==========================================
BOT_TOKEN = "9139656226:AAF3G3Kll7E0DipP80mnXGWvex4BMdEVCzc"
ADMIN_ID = 6726769296
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"
BOT_USERNAME = ""

# MK Network API v3 Configuration
MK_BASE_URL = "https://mknetworkbd.com/api/v3/public"
MK_API_KEY = "badacaa33d287233567a49db"

# Global states
current_db_mode = "sqlite"
db_firebase = None 
waiting_for_firebase = False
user_states = {}

# User & Cooldown States
user_cache = {} 
user_active_sessions = {} # format: {request_id: user_id} or {"number": user_id}
user_cooldowns = {} 

# Force Join States
force_join_status = False
force_join_channels = []

# OTP Forwarding States
otp_forward_groups = []
otp_button_link = "https://t.me/FastNodeOTP_bot"
recent_success_otps = set()

mk_dynamic_data = {} 
recent_traffic = []
daily_stats = {"date": "", "numbers": 0, "otps": 0} 
daily_user_otps = {"date": "", "users": {}}

cached_services_kb = None
cached_countries_kb = {}
cached_leaderboard_text = ""

# Admin Settings
bot_settings = {
    "withdraw_on": True,
    "min_withdraw": 10.0,
    "support_link": "",
    "w_group": "",
    "cooldown": 5,
    "num_req": 1,
    "w_methods": ["Crypto", "Binance ID"],
    "otp_default_rate": 0.5,
    "otp_service_rates": {},
    "main_channel_link": ""
}

BOT_DATA_FILE = "bot_data.json"
USERS_LIST_FILE = "users_list.json"

def get_mk_headers():
    return {
        "mknetwork-key": MK_API_KEY,
        "Content-Type": "application/json"
    }

def get_otp_reward(service_name):
    rates = bot_settings.get("otp_service_rates", {})
    val = rates.get(service_name, bot_settings.get("otp_default_rate", 0.5))
    return float(val)

def update_daily_stat(key, amount=1):
    global daily_stats
    today = time.strftime("%Y-%m-%d")
    if daily_stats.get("date") != today:
        daily_stats = {"date": today, "numbers": 0, "otps": 0}
    daily_stats[key] = daily_stats.get(key, 0) + amount

def load_local_data():
    global recent_traffic, mk_dynamic_data, force_join_status, force_join_channels, otp_forward_groups, otp_button_link, recent_success_otps, bot_settings, user_active_sessions, daily_stats, daily_user_otps
    if os.path.exists(BOT_DATA_FILE):
        try:
            with open(BOT_DATA_FILE, "r") as f:
                data = json.load(f)
                recent_traffic = data.get("recent_traffic", [])
                mk_dynamic_data = data.get("mk_dynamic_data", {})
                force_join_status = data.get("force_join_status", False)
                force_join_channels = data.get("force_join_channels", [])
                otp_forward_groups = data.get("otp_forward_groups", [])
                otp_button_link = data.get("otp_button_link", "https://t.me/FastNodeOTP_bot")
                recent_success_otps = set(data.get("recent_success_otps", []))
                
                loaded_settings = data.get("bot_settings", {})
                for k, v in loaded_settings.items(): bot_settings[k] = v
                
                daily_stats = data.get("daily_stats", {"date": "", "numbers": 0, "otps": 0})
                daily_user_otps = data.get("daily_user_otps", {"date": "", "users": {}})
                user_active_sessions = data.get("user_active_sessions", {})
        except Exception as e:
            print(f"Error loading local data: {e}")

def save_local_data():
    global recent_traffic, mk_dynamic_data, force_join_status, force_join_channels, otp_forward_groups, otp_button_link, recent_success_otps, bot_settings, user_active_sessions, daily_stats
    try:
        with open(BOT_DATA_FILE, "w") as f:
            json.dump({
                "recent_traffic": recent_traffic, 
                "mk_dynamic_data": mk_dynamic_data,
                "force_join_status": force_join_status,
                "force_join_channels": force_join_channels,
                "otp_forward_groups": otp_forward_groups,
                "otp_button_link": otp_button_link,
                "recent_success_otps": list(recent_success_otps),
                "bot_settings": bot_settings,
                "user_active_sessions": user_active_sessions,
                "daily_stats": daily_stats,
                "daily_user_otps": daily_user_otps
            }, f)
    except Exception as e:
        print(f"Error saving local data: {e}")

cached_user_list = set()

def add_to_broadcast_list(user_id):
    global cached_user_list
    if not cached_user_list and os.path.exists(USERS_LIST_FILE):
        try:
            with open(USERS_LIST_FILE, "r") as f:
                cached_user_list = set(json.load(f))
        except: pass
    if user_id not in cached_user_list:
        cached_user_list.add(user_id)
        try:
            with open(USERS_LIST_FILE, "w") as f:
                json.dump(list(cached_user_list), f)
        except: pass

def get_all_user_ids():
    global user_cache
    users = set()
    for uid in user_cache.keys():
        users.add(int(uid))
    if os.path.exists(USERS_LIST_FILE):
        try:
            with open(USERS_LIST_FILE, "r") as f:
                for u in json.load(f): users.add(int(u))
        except: pass
    return list(users)

def get_bot_info():
    try:
        res = requests.get(BASE_URL + "getMe").json()
        if res.get("ok"): return res["result"]["username"]
    except Exception: pass
    return ""

def set_bot_commands():
    commands = [{"command": "start", "description": "Start the gateway or refresh menu"}]
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
    payload = {"chat_id": chat_id, "message_id": message_id}
    requests.post(BASE_URL + "deleteMessage", json=payload)

def is_user_joined(user_id):
    if not force_join_status or not force_join_channels: return True
    if user_id == ADMIN_ID: return True
    for ch in force_join_channels:
        try:
            res = requests.get(BASE_URL + "getChatMember", params={"chat_id": ch["id"], "user_id": user_id}).json()
            if res.get("ok"):
                if res["result"]["status"] in ["left", "kicked"]: return False
            else: return False
        except: return False
    return True

GLOBAL_BODY_EMOJIS = {
    "➖": "5870818207383686839", "🚫": "5334807341109908955", "🌐": "5334590977837403844", 
    "🌟": "5337102391244263212", "⌛": "5337172996211648018", "🔥": "5337267511261960341", 
    "📊": "5353032893096567467", "👤": "5352861489541714456", "🚀": "5352597830089347330", 
    "✅": "5352694861990501856", "🆔": "5226929552319594190", "💳": "5190899075968441286"
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

def detect_service(message_text, raw_sid=""):
    msg_lower = str(message_text).lower()
    for srv in ["facebook", "whatsapp", "telegram", "instagram", "google"]:
        if srv in msg_lower:
            return srv.title()
    return "Other"

def get_service_info_html(service_name):
    app_info = PREMIUM_APPS.get(service_name, PREMIUM_APPS["Other"])
    return f'<tg-emoji emoji-id="{app_info["id"]}">{app_info["emoji"]}</tg-emoji> <b>{html.escape(service_name.upper())}</b>', app_info["id"]

def extract_otp_code(message_text):
    match = re.search(r'\b(\d{3}[\s-]?\d{3,4}|\d{4,8})\b', str(message_text))
    if match: return match.group(1)
    return "COPY"

# ==========================================
# MK Network API Integration (v3)
# ==========================================
def fetch_access_list():
    """Lấy danh sách các quốc gia, operator và range khả dụng từ MK Network v3"""
    try:
        res = requests.get(f"{MK_BASE_URL}/access_list", headers=get_mk_headers(), timeout=10)
        data = res.json()
        if data.get("meta", {}).get("code") == 200:
            return data.get("data", {}).get("items", [])
    except Exception as e:
        print(f"Error fetching access list: {e}")
    return []

def allocate_mk_number(range_prefix):
    """Gọi API v3 /getnum/number để cấp phát số điện thoại mới"""
    payload = {"range": str(range_prefix)}
    try:
        res = requests.post(f"{MK_BASE_URL}/getnum/number", headers=get_mk_headers(), json=payload, timeout=10)
        data = res.json()
        if data.get("meta", {}).get("code") == 200:
            return data.get("data", {})
    except Exception as e:
        print(f"Error allocating number: {e}")
    return None

def check_mk_otp_batch(request_ids_list):
    """Kiểm tra trạng thái OTP hàng loạt qua API v3 /check/status"""
    if not request_ids_list:
        return []
    payload = {"request_ids": [int(rid) for rid in request_ids_list]}
    try:
        res = requests.post(f"{MK_BASE_URL}/check/status", headers=get_mk_headers(), json=payload, timeout=10)
        data = res.json()
        if data.get("meta", {}).get("code") == 200:
            return data.get("data", {}).get("results", [])
    except Exception as e:
        print(f"Error checking OTP batch: {e}")
    return []

def fetch_radar_feed():
    """Lấy luồng OTP trực tiếp từ /radar endpoint"""
    try:
        res = requests.get(f"{MK_BASE_URL}/radar?charts=true&limit=25", headers=get_mk_headers(), timeout=10)
        data = res.json()
        if data.get("meta", {}).get("code") == 200:
            return data.get("data", {})
    except: pass
    return {}

# ==========================================
# Background Listeners (MK Network)
# ==========================================
def mk_radar_listener():
    global recent_traffic, mk_dynamic_data
    while True:
        try:
            radar_data = fetch_radar_feed()
            feed = radar_data.get("feed", [])
            current_time = int(time.time())
            new_traffic = []
            for h in feed:
                h['local_receive_time'] = current_time
                new_traffic.append(h)
                
                country = h.get("country", "Unknown")
                range_key = country
                if range_key not in mk_dynamic_data:
                    mk_dynamic_data[range_key] = {"ranges": {}}
            recent_traffic = new_traffic
        except: pass
        time.sleep(15)

def mk_otp_checker_listener():
    global user_active_sessions, recent_success_otps
    while True:
        try:
            if user_active_sessions:
                # Lấy danh sách request_id đang chờ xử lý
                req_ids = list(user_active_sessions.keys())
                results = check_mk_otp_batch(req_ids)
                
                for res in results:
                    r_id = res.get("request_id")
                    status = res.get("status")
                    
                    if status == "success":
                        otp_code = res.get("otp_code")
                        full_sms = res.get("full_sms", "")
                        number = res.get("number", "")
                        
                        sig = f"{number}_{otp_code}"
                        if sig not in recent_success_otps and r_id in user_active_sessions:
                            recent_success_otps.add(sig)
                            owner_id = user_active_sessions[r_id]
                            
                            # Thưởng điểm cho user
                            detected_service = detect_service(full_sms)
                            reward = get_otp_reward(detected_service)
                            update_user_stats(owner_id, reward, 0)
                            
                            # Gửi tin nhắn OTP về inbox người dùng
                            user_balance = get_user(owner_id).get("balance", 0.0)
                            service_html, srv_eid = get_service_info_html(detected_service)
                            
                            inbox_text = (
                                f"— — — — — — — — — —\n"
                                f"<blockquote>{service_html} <code>{number}</code></blockquote>\n"
                                f"<blockquote><tg-emoji emoji-id=\"5420323438508155202\">➕</tg-emoji> <b>REWARD</b>  ➜ {reward:.2f} PTS</blockquote>\n"
                                f"<blockquote><tg-emoji emoji-id=\"5190899075968441286\">💳</tg-emoji> <b>BALANCE</b> ➜ {user_balance:.2f} PTS</blockquote>\n"
                                f"— — — — — — — — — —"
                            )
                            markup = {"inline_keyboard": [[{"text": f"{otp_code}", "icon_custom_emoji_id": srv_eid, "copy_text": {"text": otp_code}, "style": "success"}]]}
                            send_message(owner_id, inbox_text, reply_markup=markup)
                            
                            # Xóa khỏi danh sách chờ активных session
                            del user_active_sessions[r_id]
                            update_daily_stat("otps", 1)
                            save_local_data()
                            
                    elif status in ["expired", "not_found"]:
                        if r_id in user_active_sessions:
                            del user_active_sessions[r_id]
                            save_local_data()
        except Exception as e:
            print(f"OTP Checker Error: {e}")
        time.sleep(10)

# ==========================================
# Database Setup (SQLite)
# ==========================================
def init_sqlite():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, first_name TEXT DEFAULT 'User', balance REAL DEFAULT 0.0, total_invites INTEGER DEFAULT 0)")
    conn.commit()
    conn.close()

def get_user(user_id):
    if user_id in user_cache: return user_cache[user_id]
    conn = sqlite3.connect("bot_database.db")
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
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, first_name, balance, total_invites) VALUES (?, ?, 0.0, 0)", (user_id, first_name))
    conn.commit()
    conn.close()
    if user_id not in user_cache:
        user_cache[user_id] = {"user_id": user_id, "first_name": first_name, "balance": 0.0, "total_invites": 0}

def update_user_stats(user_id, balance_add, invite_add):
    if user_id not in user_cache: get_user(user_id)
    if user_id in user_cache:
        user_cache[user_id]["balance"] = round(user_cache[user_id]["balance"] + float(balance_add), 2)
        user_cache[user_id]["total_invites"] += int(invite_add)
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ?, total_invites = total_invites + ? WHERE user_id = ?", (float(balance_add), int(invite_add), user_id))
    conn.commit()
    conn.close()

def get_total_users(): return len(get_all_user_ids())

# ==========================================
# Keyboards & Menus
# ==========================================
def get_main_keyboard(user_id):
    keyboard_layout = [
        [{"text": "LIVE NUMBER", "icon_custom_emoji_id": "5456259593082522998", "style": "danger"},
         {"text": "LIVE TRAFFIC", "icon_custom_emoji_id": "5429571662737611814", "style": "primary"}],
        [{"text": "INVITE FRIEND", "icon_custom_emoji_id": "5384394344859974865", "style": "success"},
         {"text": "WALLET", "icon_custom_emoji_id": "5429105001655999635", "style": "danger"}],
        [{"text": "LEADERBOARD", "icon_custom_emoji_id": "5240021484516185513", "style": "primary"}]
    ]
    if user_id == ADMIN_ID:
        keyboard_layout.append([{"text": "OWNER PANEL", "icon_custom_emoji_id": "5429427051188756948", "style": "success"}])
    return {"keyboard": keyboard_layout, "resize_keyboard": True}

def get_admin_inline_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "BROADCAST", "callback_data": "broadcast_menu", "style": "primary"}],
            [{"text": "CLOSE", "callback_data": "close_panel", "style": "danger"}]
        ]
    }

def get_owner_panel_text():
    return (
        "<b>📊 OWNER ZONE (MK NETWORK) 📊</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"<blockquote><b>👤 TOTAL USERS » {get_total_users()}</b></blockquote>\n"
        f"<blockquote><b>📱 TODAY NUM » {daily_stats['numbers']}</b></blockquote>\n"
        f"<blockquote><b>💬 TODAY OTP » {daily_stats['otps']}</b></blockquote>\n"
        "━━━━━━━━━━━━━━━━━━"
    )

def get_services_content():
    items = fetch_access_list()
    if not items:
        return "❌ <b>No active countries/ranges available on MK Network right now.</b>", None
    
    kb = {"inline_keyboard": []}
    row = []
    seen_countries = set()
    
    for item in items[:12]:
        country = item.get("country")
        range_prefix = item.get("range")
        if country not in seen_countries:
            seen_countries.add(country)
            row.append({"text": country, "callback_data": f"cnt_{range_prefix[:10]}", "style": "primary"})
            if len(row) == 2:
                kb["inline_keyboard"].append(row)
                row = []
    if row:
        kb["inline_keyboard"].append(row)
    kb["inline_keyboard"].append([{"text": "CLOSE", "callback_data": "close_panel", "style": "danger"}])
    return "🌍 <b>Select Country / Range from MK Network:</b>", kb

def get_number_allocation_content(range_prefix, user_id=None):
    global user_active_sessions, bot_settings, otp_button_link
    num_data = allocate_mk_number(range_prefix)
    
    if num_data:
        req_id = num_data.get("request_id")
        full_number = num_data.get("full_number", "")
        country = num_data.get("country", "Unknown")
        
        if user_id and req_id:
            user_active_sessions[req_id] = user_id
            save_local_data()
            
        update_daily_stat("numbers", 1)
        clean_num = str(full_number).lstrip('+')
        
        msg = (
            f"━━━━━━━━━━━━━━━\n"
            f"⌛ <b>ACTIVE NUMBER (15M)</b>\n"
            f"— — — — — — — — — —\n"
            f"🌐 <b>Country:</b> {country}\n"
            f"━━━━━━━━━━━━━━━"
        )
        kb = {
            "inline_keyboard": [
                [{"text": f"+{clean_num}", "copy_text": {"text": f"+{clean_num}"}, "style": "primary"}],
                [{"text": "OTP Group", "url": otp_button_link, "style": "success"}],
                [{"text": "BACK", "callback_data": "live_number_back", "style": "danger"}]
            ]
        }
        return msg, kb
    return "❌ <b>Out of stock or range error. Try another option.</b>", {"inline_keyboard": [[{"text": "BACK", "callback_data": "live_number_back", "style": "danger"}]]}

# ==========================================
# Handlers
# ==========================================
def handle_message(message):
    if message.get("chat", {}).get("type") != "private": return
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    text = message.get("text", "")
    first_name = message["from"].get("first_name", "User")
    
    add_user(user_id, first_name)
    user_data = get_user(user_id)
    
    if text.startswith("/start"):
        send_message(chat_id, f"🔥 <b>FAST NODE (MK NETWORK GATEWAY)</b>\n\nWelcome {html.escape(str(first_name))}, choose an option below:", reply_markup=get_main_keyboard(user_id))
    elif text == "LIVE NUMBER":
        msg, markup = get_services_content()
        send_message(chat_id, msg, reply_markup=markup)
    elif text == "WALLET":
        wallet_txt = (
            f"💰 <b>YOUR WALLET</b>\n"
            f"— — — — — — — — — —\n"
            f"👤 <b>NAME:</b> {html.escape(str(first_name))}\n"
            f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
            f"💵 <b>BALANCE: {user_data['balance']:.2f} PTS</b>\n"
        )
        send_message(chat_id, wallet_txt)
    elif text == "OWNER PANEL" and user_id == ADMIN_ID:
        send_message(chat_id, get_owner_panel_text(), reply_markup=get_admin_inline_keyboard())

def handle_callback(callback_query):
    query_id = callback_query["id"]
    user_id = callback_query["from"]["id"]
    data = callback_query["data"]
    chat_id = callback_query["message"]["chat"]["id"]
    message_id = callback_query["message"]["message_id"]
    
    if data == "live_number_back":
        msg, markup = get_services_content()
        edit_message(chat_id, message_id, msg, reply_markup=markup)
        answer_callback_query(query_id)
    elif data.startswith("cnt_"):
        range_prefix = data[4:]
        msg, markup = get_number_allocation_content(range_prefix, user_id=user_id)
        edit_message(chat_id, message_id, msg, reply_markup=markup)
        answer_callback_query(query_id, "Number allocated!")
    elif data == "close_panel":
        delete_message(chat_id, message_id)
        answer_callback_query(query_id, "Closed")

def main():
    global BOT_USERNAME
    load_local_data()
    init_sqlite()
    BOT_USERNAME = get_bot_info()
    set_bot_commands()
    
    threading.Thread(target=mk_radar_listener, daemon=True).start()
    threading.Thread(target=mk_otp_checker_listener, daemon=True).start()
    
    print(f"🚀 Bot @{BOT_USERNAME} is running securely with MK Network v3 API!")
    
    offset = None
    while True:
        try:
            res = requests.get(BASE_URL + "getUpdates", params={"timeout": 30, "offset": offset}).json()
            if res.get("ok"):
                for update in res["result"]:
                    offset = update["update_id"] + 1
                    if "message" in update: threading.Thread(target=handle_message, args=(update["message"],)).start()
                    elif "callback_query" in update: threading.Thread(target=handle_callback, args=(update["callback_query"],)).start()
        except: time.sleep(3)

if __name__ == "__main__":
    main()
