import requests
import time
import json
import random
import sqlite3
import os
import re
import html
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

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
user_states = {}
user_cache = {} 
user_active_sessions = {} 
recent_success_otps = set()
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

GLOBAL_BODY_EMOJIS = {
    "➖": "5870818207383686839", "🚫": "5334807341109908955", "🌐": "5334590977837403844",
    "🌟": "5337102391244263212", "⌛": "5337172996211648018", "💬": "5337302974806922068",
    "🔥": "5337267511261960341", "💸": "5429612421977253466", "📊": "5353032893096567467", 
    "👤": "5352861489541714456", "🚀": "5352597830089347330", "✅": "5352694861990501856", 
    "🆔": "5226929552319594190", "💳": "5190899075968441286", "🏆": "5240021484516185513"
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

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive 24/7!")

def start_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

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
    global recent_traffic, bot_settings, user_active_sessions, daily_stats, daily_user_otps, pending_withdrawals
    if os.path.exists(BOT_DATA_FILE):
        try:
            with open(BOT_DATA_FILE, "r") as f:
                data = json.load(f)
                recent_traffic = data.get("recent_traffic", [])
                loaded_settings = data.get("bot_settings", {})
                for k, v in loaded_settings.items(): bot_settings[k] = v
                daily_stats = data.get("daily_stats", {"date": "", "numbers": 0, "otps": 0})
                daily_user_otps = data.get("daily_user_otps", {"date": "", "users": {}})
                user_active_sessions = data.get("user_active_sessions", {})
                pending_withdrawals = data.get("pending_withdrawals", [])
        except Exception as e: print(f"Error loading local data: {e}")

def save_local_data():
    try:
        with open(BOT_DATA_FILE, "w") as f:
            json.dump({
                "recent_traffic": recent_traffic, 
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
    try: requests.post(BASE_URL + "deleteMessage", json=payload)
    except Exception: pass

def init_sqlite():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, 
            first_name TEXT DEFAULT 'User', 
            balance REAL DEFAULT 0.0, 
            total_invites INTEGER DEFAULT 0,
            ton_address TEXT DEFAULT '',
            joined_date TEXT DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()

def get_user(user_id):
    if user_id in user_cache: return user_cache[user_id]
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT first_name, balance, total_invites, ton_address, joined_date FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        user_data = {"user_id": user_id, "first_name": row[0], "balance": row[1], "total_invites": row[2], "ton_address": row[3] or "", "joined_date": row[4] or ""}
        user_cache[user_id] = user_data
        return user_data
    return None

def add_user(user_id, first_name="User"):
    add_to_broadcast_list(user_id)
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, joined_date FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (user_id, first_name, balance, total_invites, ton_address, joined_date) VALUES (?, ?, 0.0, 0, '', ?)", (user_id, first_name, now_str))
        conn.commit()
    conn.close()
    if user_id not in user_cache:
        user_cache[user_id] = {"user_id": user_id, "first_name": first_name, "balance": 0.0, "total_invites": 0, "ton_address": "", "joined_date": row[1] if row and row[1] else now_str}

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

def fetch_access_list():
    try:
        res = requests.get(f"{MK_BASE_URL}/access_list", headers=get_mk_headers(), timeout=10)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, dict):
                items = data.get("data", {}).get("items") or data.get("data") or data.get("items")
                if isinstance(items, list): return items
    except Exception: pass
    return []

def allocate_mk_number(range_prefix):
    payload = {"range": str(range_prefix)}
    try:
        res = requests.post(f"{MK_BASE_URL}/getnum/number", headers=get_mk_headers(), json=payload, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, dict): return data.get("data", {}) or data
    except Exception: pass
    return None

def check_mk_otp_batch(request_ids_list):
    if not request_ids_list: return []
    payload = {"request_ids": [int(rid) for rid in request_ids_list]}
    try:
        res = requests.post(f"{MK_BASE_URL}/check/status", headers=get_mk_headers(), json=payload, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, dict): return data.get("data", {}).get("results", []) or data.get("results", []) or []
    except Exception: pass
    return []

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
        except Exception: pass
        time.sleep(10)

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
            [{"text": "👥 CHECK ALL USERS", "callback_data": "admin_user_list", "style": "primary"}],
            [{"text": f"PENDING WITHDRAWALS ({len(pending_withdrawals)})", "callback_data": "view_pending_withdrawals", "style": "danger"}],
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
    items = fetch_access_list()
    if not items: 
        return "⚠️ <b>MK Network API chưa trả về danh sách quốc gia. Vui lòng thử lại sau!</b>", {"inline_keyboard": [[{"text": "CLOSE", "callback_data": "close_panel", "style": "danger"}]]}
    
    kb = {"inline_keyboard": []}
    row = []
    for item in items:
        if not isinstance(item, dict): continue
        country = item.get("country") or item.get("name") or "Unknown"
        range_prefix = item.get("range") or item.get("code") or ""
        count = item.get("count") or item.get("total") or ""
        btn_text = f"{country} ({count})" if count else f"{country}"
        row.append({"text": str(btn_text), "callback_data": f"cnt_{str(range_prefix)}", "style": "primary"})
        if len(row) == 2:
            kb["inline_keyboard"].append(row)
            row = []
    if row: kb["inline_keyboard"].append(row)
    kb["inline_keyboard"].append([{"text": "CLOSE", "callback_data": "close_panel", "style": "danger"}])
    return "🌍 <b>Select Country / Range:</b>", kb

def get_number_allocation_content(range_prefix, user_id=None):
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
                [{"text": "OTP Group", "url": "https://t.me/FastNodeOTP_bot", "style": "success"}],
                [{"text": "BACK", "callback_data": "live_number_back", "style": "danger"}]
            ]
        }
        return msg, kb
    return "❌ <b>Out of stock or API error. Please try another range.</b>", {"inline_keyboard": [[{"text": "BACK", "callback_data": "live_number_back", "style": "danger"}]]}

def get_leaderboard_text():
    users = get_all_user_ids()
    user_scores = []
    for uid in users:
        u = get_user(uid)
        if u: user_scores.append((u.get("first_name", "User"), u.get("balance", 0.0)))
    user_scores.sort(key=lambda x: x[1], reverse=True)
    
    lb_msg = "🏆 <b>TOP 5 LEADERBOARD (BALANCE)</b>\n━━━━━━━━━━━━━━━━━\n"
    if not user_scores: lb_msg += "<i>No users on leaderboard yet.</i>\n"
    else:
        for idx, (name, bal) in enumerate(user_scores[:5]):
            medal = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"][idx]
            lb_msg += f"{medal} <b>{html.escape(str(name))}</b> — ${bal:.4f} USD\n"
    lb_msg += "━━━━━━━━━━━━━━━━━"
    return lb_msg

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
            delete_message(chat_id, message_id)
            if msg_id: delete_message(chat_id, msg_id)
            
            if len(address) >= 30 and (address.startswith("EQ") or address.startswith("UQ") or address.startswith("0:")):
                update_user_ton_address(user_id, address)
                send_message(chat_id, f"✅ <b>TON USDT Address saved successfully!</b>\n\n<code>{address}</code>", reply_markup=get_main_keyboard(user_id))
                del user_states[user_id]
            else:
                send_message(chat_id, "❌ <b>Invalid TON Wallet Address!</b>\nPlease make sure it starts with <code>EQ</code>, <code>UQ</code>, or <code>0:</code> and try again.")
            return

    if text.startswith("/start"):
        send_message(chat_id, f"🔥 <b>FAST NODE • LIVE OTP GATEWAY</b>\n\nWelcome {html.escape(str(first_name))}, choose an option from the menu:", reply_markup=get_main_keyboard(user_id))
    elif text == "LIVE NUMBER":
        msg, markup = get_services_content()
        send_message(chat_id, msg, reply_markup=markup)
    elif text == "LIVE TRAFFIC":
        send_message(chat_id, "📈 <b>LIVE TRAFFIC MONITOR</b>\n━━━━━━━━━━━━━━━━━━\n<i>All systems operating normally via MK Network v3 API.</i>\n━━━━━━━━━━━━━━━━━━")
    elif text == "INVITE FRIEND":
        invite_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        send_message(chat_id, f"👥 <b>REFERRAL PROGRAM</b>\n━━━━━━━━━━━━━━━━━━\n🔗 <b>Your Link:</b>\n<code>{invite_link}</code>\n🎁 <b>Per Invite:</b> $0.0010 USD\n📊 <b>Total Invites:</b> {user_data['total_invites']}\n━━━━━━━━━━━━━━━━━━", reply_markup={"inline_keyboard": [[{"text": "COPY LINK", "copy_text": {"text": invite_link}, "style": "success"}]]})
    elif text == "LEADERBOARD":
        send_message(chat_id, get_leaderboard_text())
    elif text == "WALLET":
        ton_addr = user_data.get("ton_address", "")
        addr_display = f"<code>{ton_addr}</code>" if ton_addr else "<i>Not Configured Yet</i>"
        wallet_txt = (
            f"💰 <b>YOUR WALLET</b>\n— — — — — — — — — —\n"
            f"👤 <b>NAME:</b> {html.escape(str(first_name))}\n"
            f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
            f"💵 <b>BALANCE:</b> ${user_data['balance']:.4f} USD\n"
            f"⚡ <b>USDT (TON):</b> {addr_display}\n— — — — — — — — — —\n"
            f"📌 <b>Minimum Withdraw:</b> $5.00 USD"
        )
        send_message(chat_id, wallet_txt, reply_markup={"inline_keyboard": [[{"text": "⚙️ SET TON USDT ADDRESS", "callback_data": "set_ton_address", "style": "primary"}], [{"text": "💸 WITHDRAW ALL BALANCE", "callback_data": "request_withdraw", "style": "success"}]]})
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
    elif data == "admin_user_list" and user_id == ADMIN_ID:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, first_name, balance, total_invites, joined_date FROM users ORDER BY joined_date DESC")
        rows = cursor.fetchall()
        conn.close()
        
        msg = f"👥 <b>REGISTERED USERS DIRECTORY ({len(rows)})</b>\n━━━━━━━━━━━━━━━━━━\n"
        if not rows:
            msg += "<i>No users registered yet.</i>"
        else:
            for r in rows:
                uid, fname, bal, inv, jdate = r
                safe_name = html.escape(str(fname))
                jdate_fmt = jdate if jdate else "Unknown"
                msg += f"👤 <a href=\"tg://user?id={uid}\">{safe_name}</a>\n" \
                       f" ├ 🆔 ID: <code>{uid}</code>\n" \
                       f" ├ 💵 Bal: <b>${bal:.4f}</b> | Inv: <b>{inv}</b>\n" \
                       f" └ 📅 Joined: <code>{jdate_fmt}</code>\n\n"
        
        kb = {"inline_keyboard": [[{"text": "« BACK TO PANEL", "callback_data": "back_to_owner_panel", "style": "primary"}]]}
        edit_message(chat_id, message_id, msg, reply_markup=kb)
        answer_callback_query(query_id)
    elif data == "back_to_owner_panel" and user_id == ADMIN_ID:
        edit_message(chat_id, message_id, get_owner_panel_text(), reply_markup=get_admin_inline_keyboard())
        answer_callback_query(query_id)
    elif data == "set_ton_address":
        user_states[user_id] = {"state": "waiting_ton_address", "msg_id": message_id}
        edit_message(chat_id, message_id, "⚙️ <b>Please send your USDT (TON Network) wallet address now:</b>", reply_markup={"inline_keyboard": [[{"text": "❌ CANCEL / BACK", "callback_data": "cancel_ton_address", "style": "danger"}]]})
        answer_callback_query(query_id)
    elif data == "cancel_ton_address":
        if user_id in user_states: del user_states[user_id]
        delete_message(chat_id, message_id)
        send_message(chat_id, "❌ <b>Setup cancelled.</b>", reply_markup=get_main_keyboard(user_id))
        answer_callback_query(query_id, "Cancelled")
    elif data == "close_panel":
        delete_message(chat_id, message_id)
        answer_callback_query(query_id, "Closed")

def main():
    global BOT_USERNAME
    load_local_data()
    init_sqlite()
    BOT_USERNAME = get_bot_info()
    set_bot_commands()
    
    threading.Thread(target=start_health_server, daemon=True).start()
    threading.Thread(target=mk_otp_checker_listener, daemon=True).start()
    
    print(f"🚀 Bot @{BOT_USERNAME} is running securely!")
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
