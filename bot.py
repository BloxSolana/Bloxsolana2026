import asyncio
import requests
import random
import sqlite3
import os
import re
import html
import threading
import time
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==========================================
# Configuration (Fast Node • All-in-One Engine)
# ==========================================
BOT_TOKEN = "9139656226:AAF3G3Kll7E0DipP80mnXGWvex4BMdEVCzc"
ADMIN_ID = 6726769296
TARGET_CHAT = '-1004341368656'
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"
BOT_USERNAME = ""

# API nguồn cào OTP thực tế
API1_URL = "http://147.135.212.197/crapi/time/viewstats"
API1_TOKEN = "RldRNEVBYIFbkYpaY19udX53hX1DZnZhiI9iRkGEjGGFdXZKfmw"

# Global states
user_states = {}
user_cache = {} 
recent_success_otps = set()
recent_traffic = []
daily_stats = {"date": "", "numbers": 0, "otps": 0} 

# Admin & Bot Settings
bot_settings = {
    "withdraw_on": True,
    "min_withdraw": 5.0, 
    "otp_default_rate": 0.005, 
    "otp_service_rates": {},
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
    "Binance": {"emoji": "💱", "id": "5429438106434575354"},
    "Discord": {"emoji": "🎬", "id": "5429594374524676604"},
    "Other": {"emoji": "📶", "id": "5429353834881261942"}
}

# --- COMPLETE COUNTRY DATABASE ---
country_db = {
    "1": ("USA/Canada", "🇺🇸"), "93": ("Afghanistan", "🇦🇫"), "355": ("Albania", "🇦🇱"), "213": ("Algeria", "🇩🇿"), 
    "376": ("Andorra", "🇦🇩"), "244": ("Angola", "🇦🇴"), "1264": ("Anguilla", "🇦🇮"), "1268": ("Antigua", "🇦🇬"),
    "54": ("Argentina", "🇦🇷"), "374": ("Armenia", "🇦🇲"), "297": ("Aruba", "🇦🇼"), "61": ("Australia", "🇦🇺"),
    "43": ("Austria", "🇦🇹"), "994": ("Azerbaijan", "🇦🇿"), "1242": ("Bahamas", "🇧🇸"), "973": ("Bahrain", "🇧🇭"),
    "880": ("Bangladesh", "🇧🇩"), "1246": ("Barbados", "🇧🇧"), "375": ("Belarus", "🇧🇾"), "32": ("Belgium", "🇧🇪"),
    "501": ("Belize", "🇧🇿"), "229": ("Benin", "🇧🇯"), "1441": ("Bermuda", "🇧🇲"), "975": ("Bhutan", "🇧🇹"),
    "591": ("Bolivia", "🇧🇴"), "387": ("Bosnia", "🇧🇦"), "267": ("Botswana", "🇧🇼"), "55": ("Brazil", "🇧🇷"),
    "673": ("Brunei", "🇧🇳"), "359": ("Bulgaria", "🇧🇬"), "226": ("Burkina", "🇧🇫"), "257": ("Burundi", "🇧🇮"),
    "855": ("Cambodia", "🇰🇭"), "237": ("Cameroon", "🇨🇲"), "238": ("Cape Verde", "🇨🇻"), "1345": ("Cayman", "🇰🇾"),
    "236": ("CAR", "🇨🇫"), "235": ("Chad", "🇹🇩"), "56": ("Chile", "🇨🇱"), "86": ("China", "🇨🇳"),
    "57": ("Colombia", "🇨🇴"), "269": ("Comoros", "🇰🇲"), "242": ("Congo", "🇨🇬"), "243": ("DRC", "🇨🇩"),
    "506": ("Costa Rica", "🇨🇷"), "385": ("Croatia", "🇭🇷"), "53": ("Cuba", "🇨🇺"), "357": ("Cyprus", "🇨🇾"),
    "420": ("Czech", "🇨🇿"), "45": ("Denmark", "🇩🇰"), "253": ("Djibouti", "🇩🇯"), "1767": ("Dominica", "🇩🇲"),
    "1849": ("Dominican", "🇩🇴"), "593": ("Ecuador", "🇪🇨"), "20": ("Egypt", "🇪🇬"), "503": ("El Salvador", "🇸🇻"),
    "240": ("Equatorial", "🇬🇶"), "291": ("Eritrea", "🇪🇷"), "372": ("Estonia", "🇪🇪"), "251": ("Ethiopia", "🇪🇹"),
    "679": ("Fiji", "🇫🇯"), "358": ("Finland", "🇫🇮"), "33": ("France", "🇫🇷"), "594": ("French Guiana", "🇬🇫"),
    "689": ("French Poly", "🇵🇫"), "241": ("Gabon", "🇬🇦"), "220": ("Gambia", "🇬🇲"), "995": ("Georgia", "🇬🇪"),
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
    "223": ("Mali", "🇲🇱"), "356": ("Malta", "🇲🇹"), "692": ("Marshall", "🇲🇭"), "596": ("Martinique", "🇲🇶"),
    "222": ("Mauritania", "🇲🇷"), "230": ("Mauritius", "🇲🇺"), "262": ("Mayotte", "🇾🇹"), "52": ("Mexico", "🇲🇽"),
    "691": ("Micronesia", "🇫🇲"), "373": ("Moldova", "🇲🇩"), "377": ("Monaco", "🇲🇨"), "976": ("Mongolia", "🇲🇳"),
    "382": ("Montenegro", "🇲🇪"), "1664": ("Montserrat", "🇲🇸"), "212": ("Morocco", "🇲🇦"), "258": ("Mozambique", "🇲🇿"),
    "95": ("Myanmar", "🇲🇲"), "264": ("Namibia", "🇳🇦"), "674": ("Nauru", "🇳🇷"), "977": ("Nepal", "🇳🇵"),
    "31": ("Netherlands", "🇳🇱"), "687": ("New Caledonia", "🇳🇨"), "64": ("New Zealand", "🇳🇿"), "505": ("Nicaragua", "🇳🇮"),
    "227": ("Niger", "🇳🇪"), "234": ("Nigeria", "🇳🇬"), "683": ("Niue", "🇳🇺"), "850": ("North Korea", "🇰🇵"),
    "47": ("Norway", "🇳🇴"), "968": ("Oman", "🇴🇲"), "92": ("Pakistan", "🇵🇰"), "680": ("Palau", "🇵🇼"),
    "970": ("Palestine", "🇵🇸"), "507": ("Panama", "🇵🇦"), "675": ("PNG", "🇵🇬"), "595": ("Paraguay", "🇵🇾"),
    "51": ("Peru", "🇵🇪"), "63": ("Philippines", "🇵🇭"), "48": ("Poland", "🇵🇱"), "351": ("Portugal", "🇵🇹"),
    "1787": ("Puerto Rico", "🇵🇷"), "974": ("Qatar", "🇶🇦"), "40": ("Romania", "🇷🇴"), "7": ("Russia", "🇷🇺"),
    "250": ("Rwanda", "🇷🇼"), "685": ("Samoa", "🇼🇸"), "378": ("San Marino", "🇸🇲"), "239": ("Sao Tome", "🇸🇹"),
    "966": ("Saudi Arabia", "🇸🇦"), "221": ("Senegal", "🇸🇳"), "381": ("Serbia", "🇷🇸"), "248": ("Seychelles", "🇸🇨"),
    "232": ("Sierra Leone", "🇸🇱"), "65": ("Singapore", "🇸🇬"), "421": ("Slovakia", "🇸🇰"), "386": ("Slovenia", "🇸🇮"),
    "677": ("Solomon", "🇸🇧"), "252": ("Somalia", "🇸🇴"), "27": ("South Africa", "🇿🇦"), "82": ("South Korea", "🇰🇷"),
    "211": ("South Sudan", "🇸🇸"), "34": ("Spain", "🇪🇸"), "94": ("Sri Lanka", "🇱🇰"), "249": ("Sudan", "🇸🇩"),
    "597": ("Suriname", "🇸🇷"), "268": ("Swaziland", "🇸🇿"), "46": ("Sweden", "🇸🇪"), "41": ("Switzerland", "🇨🇭"),
    "963": ("Syria", "🇸🇾"), "886": ("Taiwan", "🇹🇼"), "992": ("Tajikistan", "🇹🇯"), "255": ("Tanzania", "🇹🇿"),
    "66": ("Thailand", "🇹🇭"), "670": ("Timor-Leste", "🇹🇱"), "228": ("Togo", "🇹🇬"), "690": ("Tokelau", "🇹🇰"),
    "676": ("Tonga", "🇹🇴"), "1868": ("Trinidad", "🇹🇹"), "216": ("Tunisia", "🇹🇳"), "90": ("Turkey", "🇹🇷"),
    "993": ("Turkmenistan", "🇹🇲"), "1649": ("Turks", "🇹🇨"), "688": ("Tuvalu", "🇹🇻"), "256": ("Uganda", "🇺🇬"),
    "380": ("Ukraine", "🇺🇦"), "971": ("UAE", "🇦🇪"), "44": ("UK", "🇬🇧"), "598": ("Uruguay", "🇺🇾"),
    "998": ("Uzbekistan", "🇺🇿"), "678": ("Vanuatu", "🇻🇺"), "379": ("Vatican", "🇻🇦"), "58": ("Venezuela", "🇻🇪"),
    "84": ("Vietnam", "🇻🇳"), "1284": ("Virgin (British)", "🇻🇬"), "1340": ("Virgin (US)", "🇻🇮"),
    "967": ("Yemen", "🇾🇪"), "260": ("Zambia", "🇿🇲"), "263": ("Zimbabwe", "🇿🇼")
}

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Fast Node Bot is alive 24/7!")

def start_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

def detect_service(message_text):
    msg_lower = str(message_text).lower()
    for service, info in PREMIUM_APPS.items():
        if service.lower() in msg_lower:
            return service
    return "Other"

def get_service_info_html(service_name):
    app_info = PREMIUM_APPS.get(service_name, PREMIUM_APPS["Other"])
    return f'<tg-emoji emoji-id="{app_info["id"]}">{app_info["emoji"]}</tg-emoji> <b>{html.escape(service_name.upper())}</b>', app_info["id"]

def update_daily_stat(key, amount=1):
    global daily_stats
    today = time.strftime("%Y-%m-%d")
    if daily_stats.get("date") != today:
        daily_stats = {"date": today, "numbers": 0, "otps": 0}
    daily_stats[key] = daily_stats.get(key, 0) + amount

def load_local_data():
    global recent_traffic, bot_settings, daily_stats, pending_withdrawals
    if os.path.exists(BOT_DATA_FILE):
        try:
            with open(BOT_DATA_FILE, "r") as f:
                data = json.load(f)
                recent_traffic = data.get("recent_traffic", [])
                loaded_settings = data.get("bot_settings", {})
                for k, v in loaded_settings.items(): bot_settings[k] = v
                daily_stats = data.get("daily_stats", {"date": "", "numbers": 0, "otps": 0})
                pending_withdrawals = data.get("pending_withdrawals", [])
        except Exception as e: print(f"Error loading local data: {e}")

def save_local_data():
    try:
        with open(BOT_DATA_FILE, "w") as f:
            json.dump({
                "recent_traffic": recent_traffic, 
                "bot_settings": bot_settings,
                "daily_stats": daily_stats,
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

def get_total_users(): return len(get_all_user_ids())

# --- GIAO DIỆN MENU NÚT BẤM (CHÍNH) ---
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

# --- ENGINE CÀO API NGUỒN THỰC TẾ & BẮN OTP NGẦM (CÓ AUTO-RETRY) ---
async def dispatch_update_engine(bot_obj, service, phone, msg, timestamp, country, flag, is_test=False):
    clean_phone = str(phone).replace("+", "")
    masked = clean_phone[:6] + "****" + clean_phone[-3:] if len(clean_phone) > 7 else clean_phone
    match = re.search(r'\d{3}[-\s]?\d{3}', str(msg))
    code = match.group(0) if match else "N/A"

    header = "🧪 <b>『 ᴛᴇsᴛ ᴏᴛᴘ sᴇɴᴛ 』</b> 🧪" if is_test else "💐 <b>『 ɴᴇw ᴏᴛᴘ ʀᴇᴄᴇɪᴠᴇᴅ 』</b> ✨"

    caption = (f"{header}\n"
               f"━━━━━━━━━━━━━━━━━━━━━\n\n"
               f"<b>⌚ ᴛɪᴍᴇ:</b> <code>{html.escape(str(timestamp))}</code>\n"
               f"<b>🌍 ᴄᴏᴜɴᴛʀʏ:</b> {html.escape(str(country))} {flag}\n"
               f"<b>📱 ɴᴜᴍʙᴇ🇷:</b> <code>{html.escape(str(masked))}</code>\n"
               f"<b>🛠 ꜱᴇʀᴠɪᴄᴇ:</b> <code>{html.escape(str(service))}</code>\n"
               f"<b>🔑 ᴄᴏᴅᴇ:</b> <code>{html.escape(str(code))}</code>\n\n"
               f"<b>💬 ᴍᴇssᴀɢᴇ:</b>\n<pre>{html.escape(str(msg))}</pre>\n\n"
               f"━━━━━━━━━━━━━━━━━━━━━")
    
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✨ K.BRO YOUTUBE", url="https://youtube.com/@memefactoryvn"),
            InlineKeyboardButton("👑 ADMIN", url="https://t.me/BloxSolana")
        ]
    ])
    
    try:
        requests.post(BASE_URL + "sendMessage", json={
            "chat_id": TARGET_CHAT,
            "text": apply_emojis(caption),
            "parse_mode": "HTML",
            "reply_markup": kb.to_dict(),
            "disable_web_page_preview": True
        })
    except Exception as e: 
        print(f"Error dispatching update: {e}")

def process_data(dataset):
    unified = []
    if isinstance(dataset, dict) and "data" in dataset:
        for item in dataset["data"]:
            unified.append([item.get("cli", "Unknown"), item.get("num", ""), item.get("message", ""), item.get("dt", "")])
    elif isinstance(dataset, list):
        unified = dataset
    return unified

def sync_engine_loop(bot_obj):
    s1 = None
    print("🚀 Fast Node Engine Background Sync Started Successfully!")
    
    while True:
        headers = {"User-Agent": "Mozilla/5.0"}
        max_retries = 3
        success = False
        
        for attempt in range(max_retries):
            try:
                r = requests.get(API1_URL, params={"token": API1_TOKEN}, headers=headers, timeout=10)
                if r.status_code == 200:
                    data_json = r.json()
                    dataset = process_data(data_json)
                    if dataset:
                  
