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
# Configuration (Fast Node • MK Network Gateway)
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
user_active_sessions = {} 
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

# Admin Settings
bot_settings = {
    "withdraw_on": True,
    "min_withdraw": 5.0, 
    "support_link": "",
    "cooldown": 5,
    "num_req": 1,
    "w_methods": ["USDT (TON Network)"],
    "otp_default_rate": 0.005, 
    "otp_service_rates": {},
    "main_channel_link": "",
    "refer_reward": 0.001
}

pending_withdrawals = []

BOT_DATA_FILE = "bot_data.json"
USERS_LIST_FILE = "users_list.json"

# ==========================================
# Global Emojis Map
# ==========================================
GLOBAL_BODY_EMOJIS = {
    "➖": "5870818207383686839", "🚫": "5334807341109908955", "😒": "5334763399299506604",
    "🖥": "5334880948259427772", "🌐": "5334590977837403844", "🌟": "5337102391244263212",
    "🕓": "5336983442125001376", "⌛": "5337172996211648018", "💬": "5337302974806922068",
    "🔐": "5337255927735163754", "🍏": "5337132498965010628", "❔": "5336850036145823599",
    "⚠️": "5336944168944047463", "🔥": "5337267511261960341", "💸": "5429612421977253466",
    "📊": "5353032893096567467", "🔢": "5226929552319594190", "👤": "5352861489541714456",
    "🚀": "5352597830089347330", "✅": "5352694861990501856", "🆔": "5226929552319594190",
    "💳": "5190899075968441286", "🏆": "5240021484516185513", "👑": "5352838545826420397"
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
    "Microsoft": {"emoji": "🪟", "id": "5979047775470358891"},
    "TikTok": {"emoji": "🎵", "id": "5429132656950419591"},
    "Bkash": {"emoji": "🏦", "id": "5431552076452766597"},
    "Binance": {"emoji": "💱", "id": "5429438106434575354"},
    "Snapchat": {"emoji": "👻", "id": "5429398137468919845"},
    "Uber": {"emoji": "🚗", "id": "5298715455316303708"},
    "Discord": {"emoji": "🎬", "id": "5429594374524676604"},
    "Amazon": {"emoji": "🌟", "id": "5431358656895568355"},
    "Viber": {"emoji": "💜", "id": "5429470576387335368"},
    "Twitter": {"emoji": "🐦", "id": "5431899135580087595"},
    "Netflix": {"emoji": "🎥", "id": "5431641055290235797"},
    "Spotify": {"emoji": "🎵", "id": "5429235839244739644"},
    "Foodpanda": {"emoji": "🐼", "id": "5336879280578138635"},
    "Pathao": {"emoji": "🛵", "id": "5336879280578138635"},
    "ChatGPT": {"emoji": "🤖", "id": "5429503209548847635"},
    "Imo": {"emoji": "💭", "id": "5431378937731129128"},
    "Other": {"emoji": "📶", "id": "5429353834881261942"}
}

SERVICE_SMS_KEYWORDS = {
    "Facebook": ["facebook", "fb code", "fb", "meta"],
    "WhatsApp": ["whats", "whatsapp", "whatsapp code"],
    "Telegram": ["telegram", "tg code"],
    "Instagram": ["instagram", "ig code"],
    "Google": ["google", "Googl"],
    "Microsoft": ["microsoft", "micro", "Microsof", "xbox"],
    "TikTok": ["tiktok", "tik tok"],
    "Bkash": ["bkash"],
    "Binance": ["binance", "bnb"],
    "Snapchat": ["snapchat", "snap"],
    "Uber": ["uber"],
    "Discord": ["discord"],
    "Amazon": ["amazon", "aws"],
    "Viber": ["viber"],
    "Twitter": ["twitter", "x.com"],
    "Netflix": ["netflix"],
    "Spotify": ["spotify"],
    "Foodpanda": ["foodpanda", "panda"],
    "Pathao": ["pathao"],
    "ChatGPT": ["openai", "chatgpt"],
    "Imo": ["imo code", "imo"]
}

def detect_service(message_text, raw_sid=""):
    msg_lower = str(message_text).lower()
    for service, keywords in SERVICE_SMS_KEYWORDS.items():
        for kw in keywords:
            if re.search(rf'\b{re.escape(kw)}\b', msg_lower) or kw in msg_lower:
                return service
    for service in PREMIUM_APPS.keys():
        if service.lower() in str(raw_sid).lower(): return service
    return "Other"

def get_service_info_html(service_name):
    app_info = PREMIUM_APPS.get(service_name, PREMIUM_APPS["Other"])
    return f'<tg-emoji emoji-id="{app_info["id"]}">{app_info["emoji"]}</tg-emoji> <b>{html.escape(service_name.upper())}</b>', app_info["id"]

def get_mk_headers():
    return {
        "mknetwork-key": MK_API_KEY,
        "Content-Type": "application/json"
    }

def get_otp_reward(service_name):
    rates = bot_settings.get("otp_service_rates", {})
    val = rates.get(service_name, bot_settings.get("otp_default_rate", 0.005))
    return float(val)

def update_daily_stat(key, amount=1):
    global daily_stats
    today = time.strftime("%Y-%m-%d")
    if daily_stats.get("date") != today:
        daily_stats = {"date": today, "numbers": 0, "otps": 0}
    daily_stats[key] = daily_stats.get(key, 0) + amount

def load_local_data():
    global recent_traffic, mk_dynamic_data, force_join_status, force_join_channels, otp_forward_groups, otp_button_link, recent_success_otps, bot_settings, user_active_sessions, daily_stats, daily_user_otps, pending_withdrawals
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
                pending_withdrawals = data.get("pending_withdrawals", [])
        except Exception as e: print(f"Error loading local data: {e}")

def save_local_data():
    global recent_traffic, mk_dynamic_data, force_join_status, force_join_channels, otp_forward_groups, otp_button_link, recent_success_otps, bot_settings, user_active_sessions, daily_stats, pending_withdrawals
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
                "daily_user_otps": daily_user_otps,
                "pending_withdrawals": pending_withdrawals
            }, f)
    except Exception as e: print(f"Error saving local data: {e}")

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
    for uid in user_cache.keys(): users.add(int(uid))
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
    commands = [{"command": "start", "description": "Start or refresh the bot"}]
    try: requests.post(BASE_URL + "setMyCommands", json={"commands": commands})
    except Exception: pass

def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "text": apply_emojis(text), "parse_mode": parse_mode}
    if reply_markup: payload["reply_markup"] = reply_markup
    try: return requests.post(BASE_URL + "sendMessage", json=payload).json()
    except Exception as e:
        print(f"Send message error: {e}")
        return None

def edit_message(chat_id, message_id, text, reply_markup=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": apply_emojis(text), "parse_mode": parse_mode}
    if reply_markup: payload["reply_markup"] = reply_markup
    try: requests.post(BASE_URL + "editMessageText", json=payload)
    except Exception as e: print(f"Edit message error: {e}")

def answer_callback_query(callback_query_id, text="", show_alert=False):
    payload = {"callback_query_id": callback_query_id, "text": text, "show_alert": show_alert}
    requests.post(BASE_URL + "answerCallbackQuery", json=payload)

def delete_message(chat_id, message_id):
    payload = {"chat_id": chat_id, "message_id": message_id}
    requests.post(BASE_URL + "deleteMessage", json=payload)

def copy_message(chat_id, from_chat_id, message_id, reply_markup=None):
    payload = {"chat_id": chat_id, "from_chat_id": from_chat_id, "message_id": message_id}
    if reply_markup: payload["reply_markup"] = reply_markup
    try: return requests.post(BASE_URL + "copyMessage", json=payload).json()
    except Exception: return None

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

# ==========================================
# Database Setup (SQLite)
# ==========================================
def init_sqlite():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, 
            first_name TEXT DEFAULT 'User', 
            balance REAL DEFAULT 0.0, 
            total_invites INTEGER DEFAULT 0,
            ton_address TEXT DEFAULT ''
        )
    """)
    try: cursor.execute("ALTER TABLE users ADD COLUMN ton_address TEXT DEFAULT ''")
    except: pass
    conn.commit()
    conn.close()

def get_user(user_id):
    if user_id in user_cache: return user_cache[user_id]
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT first_name, balance, total_invites, ton_address FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        user_data = {"user_id": user_id, "first_name": row[0], "balance": row[1], "total_invites": row[2], "ton_address": row[3] or ""}
        user_cache[user_id] = user_data
        return user_data
    return None

def add_user(user_id, first_name="User"):
    add_to_broadcast_list(user_id)
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, first_name, balance, total_invites, ton_address) VALUES (?, ?, 0.0, 0, '')", (user_id, first_name))
    conn.commit()
    conn.close()
    if user_id not in user_cache:
        user_cache[user_id] = {"user_id": user_id, "first_name": first_name, "balance": 0.0, "total_invites": 0, "ton_address": ""}

def update_user_stats(user_id, balance_add, invite_add):
    if user_id not in user_cache: get_user(user_id)
    if user_id in user_cache:
        user_cache[user_id]["balance"] = round(user_cache[user_id]["balance"] + float(balance_add), 4)
        user_cache[user_id]["total_invites"] += int(invite_add)
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ?, total_invites = total_invites + ? WHERE user_id = ?", (float(balance_add), int(invite_add), user_id))
    conn.commit()
    conn.close()

def update_user_ton_address(user_id, address):
    if user_id in user_cache: user_cache[user_id]["ton_address"] = address
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET ton_address = ? WHERE user_id = ?", (address, user_id))
    conn.commit()
    conn.close()

def get_total_users(): return len(get_all_user_ids())

# ==========================================
# MK Network API Integration (v3) - BULLETPROOF
# ==========================================
def fetch_access_list():
    try:
        res = requests.get(f"{MK_BASE_URL}/access_list", headers=get_mk_headers(), timeout=10)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, dict):
                # Hỗ trợ cả 2 định dạng trả về phổ biến của API v3
                items = data.get("data", {}).get("items") or data.get("data") or data.get("items")
                if isinstance(items, list):
                    return items
    except Exception as e: print(f"Error fetching access list: {e}")
    return []

def allocate_mk_number(range_prefix):
    payload = {"range": str(range_prefix)}
    try:
        res = requests.post(f"{MK_BASE_URL}/getnum/number", headers=get_mk_headers(), json=payload, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, dict):
                return data.get("data", {}) or data
    except Exception as e: print(f"Error allocating number: {e}")
    return None

def check_mk_otp_batch(request_ids_list):
    if not request_ids_list: return []
    payload = {"request_ids": [int(rid) for rid in request_ids_list]}
    try:
        res = requests.post(f"{MK_BASE_URL}/check/status", headers=get_mk_headers(), json=payload, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, dict):
                return data.get("data", {}).get("results", []) or data.get("results", []) or []
    except Exception as e: print(f"Error checking OTP batch: {e}")
    return []

# ==========================================
# Background Listeners
# ==========================================
def mk_otp_checker_listener():
    global user_active_sessions, recent_success_otps
    while True:
        try:
            if user_active_sessions:
                req_ids = list(user_active_sessions.keys())
                results = check_mk_otp_batch(req_ids)
                
                for res in results:
                    if not isinstance(res, dict): continue
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
                            
                            detected_service = detect_service(full_sms)
                            reward = get_otp_reward(detected_service)
                            update_user_stats(owner_id, reward, 0)
                            
                            user_balance = get_user(owner_id).get("balance", 0.0)
                            service_html, srv_eid = get_service_info_html(detected_service)
                            
                            inbox_text = (
                                f"— — — — — — — — — —\n"
                                f"<blockquote>{service_html} <code>{number}</code></blockquote>\n"
                                f"<blockquote><tg-emoji emoji-id=\"5420323438508155202\">➕</tg-emoji> <b>REWARD</b>  ➜ +${reward:.4f} USD</blockquote>\n"
                                f"<blockquote><tg-emoji emoji-id=\"5190899075968441286\">💳</tg-emoji> <b>BALANCE</b> ➜ ${user_balance:.4f} USD</blockquote>\n"
                                f"— — — — — — — — — —"
                            )
                            markup = {"inline_keyboard": [[{"text": f"{otp_code}", "icon_custom_emoji_id": srv_eid, "copy_text": {"text": otp_code}, "style": "success"}]]}
                            send_message(owner_id, inbox_text, reply_markup=markup)
                            
                            del user_active_sessions[r_id]
                            update_daily_stat("otps", 1)
                            save_local_data()
                            
                    elif status in ["expired", "not_found"]:
                        if r_id in user_active_sessions:
                            del user_active_sessions[r_id]
                            save_local_data()
        except Exception as e: print(f"OTP Listener Error: {e}")
        time.sleep(10)

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
    pending_count = len(pending_withdrawals)
    return {
        "inline_keyboard": [
            [{"text": f"PENDING WITHDRAWALS ({pending_count})", "callback_data": "view_pending_withdrawals", "style": "danger"}],
            [{"text": "BROADCAST", "callback_data": "broadcast_menu", "style": "primary"}],
            [{"text": "CLOSE", "callback_data": "close_panel", "style": "danger"}]
        ]
    }

def get_owner_panel_text():
    return (
        "<b>📊 OWNER PANEL (ADMIN CONTROL) 📊</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"<blockquote><b>👤 TOTAL USERS » {get_total_users()}</b></blockquote>\n"
        f"<blockquote><b>📱 TODAY NUMBERS » {daily_stats['numbers']}</b></blockquote>\n"
        f"<blockquote><b>💬 TODAY OTPS » {daily_stats['otps']}</b></blockquote>\n"
        f"<blockquote><b>⏳ PENDING WITHDRAWALS » {len(pending_withdrawals)}</b></blockquote>\n"
        "━━━━━━━━━━━━━━━━━━"
    )

def get_services_content():
    try:
        items = fetch_access_list()
        if not items: 
            return "⚠️ <b>MK Network API chưa trả về danh sách quốc gia (Kho số đang trống hoặc lỗi kết nối). Vui lòng thử lại sau!</b>", {"inline_keyboard": [[{"text": "CLOSE", "callback_data": "close_panel", "style": "danger"}]]}
        
        kb = {"inline_keyboard": []}
        row = []
        seen_countries = set()
        
        for item in items[:12]:
            if not isinstance(item, dict): continue
            country = item.get("country") or item.get("name") or "Unknown"
            range_prefix = item.get("range") or item.get("code") or ""
            if country and country not in seen_countries:
                seen_countries.add(country)
                row.append({"text": str(country), "callback_data": f"cnt_{str(range_prefix)[:10]}", "style": "primary"})
                if len(row) == 2:
                    kb["inline_keyboard"].append(row)
                    row = []
        if row: kb["inline_keyboard"].append(row)
        kb["inline_keyboard"].append([{"text": "CLOSE", "callback_data": "close_panel", "style": "danger"}])
        return "🌍 <b>Select Country / Range:</b>", kb
    except Exception as e:
        return f"❌ <b>Lỗi kết nối API:</b> <code>{html.escape(str(e))}</code>", None

def get_number_allocation_content(range_prefix, user_id=None):
    global user_active_sessions, otp_button_link
    try:
        num_data = allocate_mk_number(range_prefix)
        
        if num_data and isinstance(num_data, dict):
            req_id = num_data.get("request_id") or num_data.get("id")
            full_number = num_data.get("full_number", "") or num_data.get("number", "")
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
    except Exception as e:
        print(f"Allocation error: {e}")
    return "❌ <b>Out of stock or API error. Please try another range.</b>", {"inline_keyboard": [[{"text": "BACK", "callback_data": "live_number_back", "style": "danger"}]]}

def broadcast_worker(from_chat_id, message_id, target_msg_id):
    users = get_all_user_ids() 
    success_count = 0
    for uid in users:
        try:
            res = copy_message(uid, from_chat_id, message_id)
            if res and res.get("ok"): success_count += 1
            time.sleep(0.05) 
        except: pass
        
    send_message(from_chat_id, f"✅ <b>Broadcast Completed!</b>\nSuccessfully sent to {success_count} users out of {len(users)}.")
    if target_msg_id:
        edit_message(from_chat_id, target_msg_id, get_owner_panel_text(), reply_markup=get_admin_inline_keyboard())

# ==========================================
# Handlers
# ==========================================
def handle_message(message):
    if message.get("chat", {}).get("type") != "private": return
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    text = message.get("text", "")
    first_name = message["from"].get("first_name", "User")
    message_id = message["message_id"]
    
    add_user(user_id, first_name)
    user_data = get_user(user_id)
    
    if user_id in user_states:
        state_data = user_states[user_id]
        state = state_data.get("state")
        msg_id = state_data.get("msg_id")
        
        if state == "waiting_ton_address":
            address = text.strip()
            if len(address) >= 30 and (address.startswith("EQ") or address.startswith("UQ") or address.startswith("0:")):
                update_user_ton_address(user_id, address)
                send_message(chat_id, f"✅ <b>TON USDT Address saved successfully!</b>\n\n<code>{address}</code>", reply_markup=get_main_keyboard(user_id))
                del user_states[user_id]
            else:
                send_message(chat_id, "❌ <b>Invalid TON Wallet Address!</b>\nPlease make sure it starts with <code>EQ</code>, <code>UQ</code>, or <code>0:</code> and try again.")
            return
            
        elif state == "waiting_broadcast":
            if msg_id: edit_message(chat_id, msg_id, "⏳ <b>Broadcasting message to all users...</b>")
            threading.Thread(target=broadcast_worker, args=(chat_id, message_id, msg_id), daemon=True).start()
            del user_states[user_id]
            return

    if text.startswith("/start"):
        send_message(chat_id, f"🔥 <b>FAST NODE • LIVE OTP GATEWAY</b>\n\nWelcome {html.escape(str(first_name))}, choose an option from the menu:", reply_markup=get_main_keyboard(user_id))
    
    elif text == "LIVE NUMBER":
        try:
            msg, markup = get_services_content()
            if markup: send_message(chat_id, msg, reply_markup=markup)
            else: send_message(chat_id, msg)
        except Exception as e:
            send_message(chat_id, f"❌ <b>Lỗi hệ thống:</b> <code>{html.escape(str(e))}</code>")
        
    elif text == "WALLET":
        ton_addr = user_data.get("ton_address", "")
        addr_display = f"<code>{ton_addr}</code>" if ton_addr else "<i>Not Configured Yet</i>"
        
        wallet_txt = (
            f"💰 <b>YOUR WALLET</b>\n"
            f"— — — — — — — — — —\n"
            f"👤 <b>NAME:</b> {html.escape(str(first_name))}\n"
            f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
            f"💵 <b>BALANCE:</b> ${user_data['balance']:.4f} USD\n"
            f"⚡ <b>USDT (TON):</b> {addr_display}\n"
            f"— — — — — — — — — —\n"
            f"📌 <b>Minimum Withdraw:</b> ${bot_settings['min_withdraw']:.2f} USD"
        )
        
        kb = {"inline_keyboard": [
            [{"text": "⚙️ SET TON USDT ADDRESS", "callback_data": "set_ton_address", "style": "primary"}],
            [{"text": "💸 WITHDRAW ALL BALANCE", "callback_data": "request_withdraw", "style": "success"}]
        ]}
        send_message(chat_id, wallet_txt, reply_markup=kb)
        
    elif text == "OWNER PANEL" and user_id == ADMIN_ID:
        send_message(chat_id, get_owner_panel_text(), reply_markup=get_admin_inline_keyboard())

def handle_callback(callback_query):
    global pending_withdrawals
    query_id = callback_query["id"]
    user_id = callback_query["from"]["id"]
    data = callback_query["data"]
    chat_id = callback_query["message"]["chat"]["id"]
    message_id = callback_query["message"]["message_id"]
    
    if data == "live_number_back":
        try:
            msg, markup = get_services_content()
            if markup: edit_message(chat_id, message_id, msg, reply_markup=markup)
            else: edit_message(chat_id, message_id, msg)
        except Exception as e:
            edit_message(chat_id, message_id, f"❌ <b>Lỗi:</b> {e}")
        answer_callback_query(query_id)
        
    elif data.startswith("cnt_"):
        range_prefix = data[4:]
        msg, markup = get_number_allocation_content(range_prefix, user_id=user_id)
        edit_message(chat_id, message_id, msg, reply_markup=markup)
        answer_callback_query(query_id, "Number allocated!")
        
    elif data == "set_ton_address":
        user_states[user_id] = {"state": "waiting_ton_address", "msg_id": message_id}
        edit_message(chat_id, message_id, "⚙️ <b>Please send your USDT (TON Network) wallet address now:</b>")
        answer_callback_query(query_id)
        
    elif data == "request_withdraw":
        user_data = get_user(user_id)
        balance = user_data.get("balance", 0.0)
        ton_addr = user_data.get("ton_address", "")
        min_w = bot_settings.get("min_withdraw", 5.0)
        
        if not ton_addr:
            answer_callback_query(query_id, "❌ Please configure your USDT TON address first!", show_alert=True)
            return
            
        if balance < min_w:
            answer_callback_query(query_id, f"❌ Insufficient balance! Minimum withdrawal is ${min_w:.2f} USD.", show_alert=True)
            return
            
        amount_to_withdraw = balance
        update_user_stats(user_id, -amount_to_withdraw, 0)
        
        req_item = {
            "req_id": int(time.time()),
            "user_id": user_id,
            "first_name": user_data.get("first_name", "User"),
            "amount": amount_to_withdraw,
            "address": ton_addr,
            "date": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        pending_withdrawals.append(req_item)
        save_local_data()
        
        answer_callback_query(query_id, "Withdrawal request submitted successfully!", show_alert=True)
        edit_message(chat_id, message_id, f"✅ <b>WITHDRAWAL SUBMITTED!</b>\n\nAmount: ${amount_to_withdraw:.4f} USD\nAddress: <code>{ton_addr}</code>\nStatus: Pending Admin Approval")
        
    elif data == "broadcast_menu" and user_id == ADMIN_ID:
        user_states[user_id] = {"state": "waiting_broadcast", "msg_id": message_id}
        edit_message(chat_id, message_id, "📣 <b>BROADCAST SYSTEM</b>\n\nSend any text, photo, video, or audio message you want to broadcast to all users.")
        answer_callback_query(query_id, "Send your broadcast content now!")

    elif data == "view_pending_withdrawals" and user_id == ADMIN_ID:
        if not pending_withdrawals:
            answer_callback_query(query_id, "No pending withdrawals!", show_alert=True)
            return
            
        item = pending_withdrawals[0]
        text = (
            f"<b>💳 PENDING WITHDRAWAL APPROVAL</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>User:</b> <a href='tg://user?id={item['user_id']}'>{html.escape(item['first_name'])}</a>\n"
            f"🆔 <b>User ID:</b> <code>{item['user_id']}</code>\n"
            f"💵 <b>Amount:</b> ${item['amount']:.4f} USD\n"
            f"⚡ <b>TON Address:</b> <code>{item['address']}</code>\n"
            f"📅 <b>Date:</b> {item['date']}\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        kb = {"inline_keyboard": [
            [{"text": "✅ APPROVE", "callback_data": f"app_w_{item['req_id']}", "style": "success"},
             {"text": "❌ REJECT", "callback_data": f"rej_w_{item['req_id']}", "style": "danger"}],
            [{"text": "CLOSE", "callback_data": "close_panel", "style": "danger"}]
        ]}
        send_message(chat_id, text, reply_markup=kb)
        answer_callback_query(query_id)

    elif data.startswith("app_w_") and user_id == ADMIN_ID:
        req_id = int(data[6:])
        item = next((x for x in pending_withdrawals if x["req_id"] == req_id), None)
        if item:
            pending_withdrawals.remove(item)
            save_local_data()
            send_message(item["user_id"], f"🎉 <b>WITHDRAWAL APPROVED!</b>\nYour payment of ${item['amount']:.4f} USD has been sent to your TON wallet:\n<code>{item['address']}</code>")
            edit_message(chat_id, message_id, f"✅ <b>Approved withdrawal for ID {item['user_id']} (${item['amount']:.4f} USD)</b>")
            answer_callback_query(query_id, "Approved!")
            
    elif data.startswith("rej_w_") and user_id == ADMIN_ID:
        req_id = int(data[6:])
        item = next((x for x in pending_withdrawals if x["req_id"] == req_id), None)
        if item:
            pending_withdrawals.remove(item)
            update_user_stats(item["user_id"], item["amount"], 0)
            save_local_data()
            send_message(item["user_id"], f"❌ <b>WITHDRAWAL REJECTED!</b>\nYour request of ${item['amount']:.4f} USD was rejected and refunded back to your wallet.")
            edit_message(chat_id, message_id, f"❌ <b>Rejected & Refunded withdrawal for ID {item['user_id']}</b>")
            answer_callback_query(query_id, "Rejected!")

    elif data == "close_panel":
        delete_message(chat_id, message_id)
        answer_callback_query(query_id, "Closed")

def main():
    global BOT_USERNAME
    load_local_data()
    init_sqlite()
    BOT_USERNAME = get_bot_info()
    set_bot_commands()
    
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
