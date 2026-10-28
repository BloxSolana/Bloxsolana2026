import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import requests
from bs4 import BeautifulSoup
import re
import datetime
import os
import json
import time
import random
import html
import threading
import base64
from flask import Flask, request

# ==========================================
# 👑 1. CẤU HÌNH HỆ THỐNG & GITHUB & TELEGRAM BOT
# ==========================================
ADMIN_ID = 6726769296
TOKEN = "8622066775:AAFncl413hILhGl-J6DQD9oDbK4PEEHsERc"
GROUP_CHAT_ID = "-1004341368656"
GROUP_OTP_LINK = "https://t.me/LIVEOTPIVAS"
BRIDGE_API_KEY = "khoibro_secret_bridge_key_123"

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "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")
REPO_OWNER = "BloxSolana"
REPO_NAME = "Bloxsolana2026"
FILE_PATH = "numbers.txt"
BRANCH = "main"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ==========================================
# 🌐 2. FLASK WEBHOOK CHO RENDER 24/7
# ==========================================
@app.route('/')
def home():
    return "Bot IVASMS OTP Global Webhook Server đang chạy 24/7!"

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return '', 403

# ==========================================
# 📊 3. QUẢN LÝ DASHBOARD THỐNG KÊ & GITHUB SYNC
# ==========================================
DASHBOARD_STATS_FILE = "dashboard_stats.json"

def load_json_db(filename):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_json_db(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_dashboard_stats():
    data = load_json_db(DASHBOARD_STATS_FILE)
    today_str = datetime.datetime.now().strftime('%Y-%m-%d')
    if data.get("date") != today_str:
        data = {"date": today_str, "services": {}}
        save_json_db(DASHBOARD_STATS_FILE, data)
    if "services" not in data:
        data["services"] = {}
    return data

def record_service_message(service_name):
    data = load_dashboard_stats()
    if service_name not in data["services"]:
        data["services"][service_name] = 0
    data["services"][service_name] += 1
    save_json_db(DASHBOARD_STATS_FILE, data)

def push_numbers_to_github(numbers_list):
    try:
        api_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json"
        }
        get_res = requests.get(api_url, headers=headers, timeout=10)
        sha = None
        if get_res.status_code == 200:
            sha = get_res.json().get("sha")
            
        file_content_str = "\n".join(numbers_list)
        content_encoded = base64.b64encode(file_content_str.encode("utf-8")).decode("utf-8")
        
        payload = {
            "message": "Auto-remove expired number after 15 minutes",
            "content": content_encoded,
            "branch": BRANCH
        }
        if sha:
            payload["sha"] = sha
            
        requests.put(api_url, json=payload, headers=headers, timeout=10)
    except Exception as e:
        print(f"⚠️ Lỗi đẩy GitHub khi xóa số hết hạn: {e}")

# ==========================================
# ⏰ 4. LUỒNG CHẠY NGẦM TỰ ĐỘNG XÓA SỐ SAU 15 PHÚT
# ==========================================
def background_expiry_worker():
    while True:
        try:
            time.sleep(10)
            now = time.time()
            expired_keys = []
            
            for chat_id, data in list(USER_ACTIVE_PHONES.items()):
                if now > data["expire"]:
                    expired_keys.append(chat_id)
                    phone_to_remove = data["phone"]
                    
                    try:
                        bot.send_message(
                            chat_id, 
                            f"⏰ <b>Thời gian 15 phút của số <code>{phone_to_remove}</code> đã hết!</b> Số đã tự động được thu hồi khỏi hệ thống.", 
                            parse_mode="HTML"
                        )
                    except:
                        pass
                    
                    file_path = "numbers.txt"
                    if os.path.exists(file_path):
                        with open(file_path, "r", encoding="utf-8") as f:
                            lines = [l.strip() for l in f if l.strip()]
                        
                        clean_target = re.sub(r'\D', '', phone_to_remove)
                        new_lines = [l for l in lines if re.sub(r'\D', '', l) != clean_target]
                        
                        if len(new_lines) < len(lines):
                            with open(file_path, "w", encoding="utf-8") as f:
                                for l in new_lines:
                                    f.write(l + "\n")
                            
                            push_numbers_to_github(new_lines)
                            load_text_batch()
                            print(f"🗑️ [EXPIRE] Đã tự động xóa duy nhất số hết hạn {phone_to_remove} khỏi numbers.txt & GitHub!")

            for chat_id in expired_keys:
                USER_ACTIVE_PHONES.pop(chat_id, None)
                
        except Exception as e:
            print(f"⚠️ Lỗi background expiry worker: {e}")

threading.Thread(target=background_expiry_worker, daemon=True).start()

# ==========================================
# 🚀 5. ENDPOINT NHẬN SMS & FORMAT CHUẨN MẪU ZM OTP (LỌC NOT FOUND)
# ==========================================
@app.route('/api/push-sms', methods=['POST'])
def api_push_sms_handler():
    try:
        data = request.json if request.is_json else {}
        if data.get("key", "") and data.get("key") != BRIDGE_API_KEY:
            return {"status": "error", "message": "Unauthorized"}, 403

        raw_text = data.get("raw_text", "")
        
        useless_phrases = ["No SMS found", "Range Count", "Client System", "Dashboard", "TRUSTED PREMIUM SMS"]
        if not raw_text or (any(p in raw_text for p in useless_phrases) and len(raw_text) < 20):
            return {"status": "ignored"}, 200

        # BÓC TÁCH MÃ OTP CHUẨN XÁC
        otp_display = None
        dash_match = re.search(r'\b([0-9]{3}\-[0-9]{3})\b', raw_text)
        if dash_match:
            otp_display = dash_match.group(1)
        else:
            otp_keyword_match = re.search(r'(?:OTP|code|mã|is)[:\s#]*([0-9]{4,8})', raw_text, re.IGNORECASE)
            if otp_keyword_match:
                otp_display = otp_keyword_match.group(1)
            else:
                all_digits = re.findall(r'\b\d{5,6}\b', raw_text)
                valid_digits = [d for d in all_digits if not d.startswith(('2026', '2025', '0120'))]
                if valid_digits:
                    raw_otp = valid_digits[-1]
                    if len(raw_otp) == 6:
                        otp_display = f"{raw_otp[:3]}-{raw_otp[3:]}"
                    else:
                        otp_display = raw_otp
                else:
                    all_4 = re.findall(r'\b\d{4}\b', raw_text)
                    valid_4 = [d for d in all_4 if not d.startswith(('2026', '2025', '0120'))]
                    if valid_4:
                        otp_display = valid_4[-1]

        # LỌC KHÔNG GỬI NẾU KHÔNG CÓ OTP
        if not otp_display or otp_display == "Not Found":
            return {"status": "ignored_no_otp"}, 200

        text_upper = raw_text.upper()
        service_name = "Other Service"
        
        if "WHATSAPP" in text_upper:
            service_name = "WhatsApp"
        elif "TELEGRAM" in text_upper:
            service_name = "Telegram"
        elif "FACEBOOK" in text_upper or "MA FACEBOOK" in text_upper or "FB" in text_upper:
            service_name = "Facebook"
        elif "TIKTOK" in text_upper:
            service_name = "TikTok"
        elif "SHOPEE" in text_upper:
            service_name = "Shopee"
        elif "PAYPAL" in text_upper:
            service_name = "PayPal"
        elif "UBER" in text_upper:
            service_name = "Uber"
        elif "APPLE" in text_upper or "ICLOUD" in text_upper:
            service_name = "Apple"
        elif "YANGO" in text_upper:
            service_name = "Yango"
        elif "MICROSOFT" in text_upper or "MS" in text_upper:
            service_name = "Microsoft"
        elif "AUTHMSG" in text_upper:
            service_name = "AUTHMSG"
        elif "TENCENT" in text_upper:
            service_name = "Tencent"
        elif "AMAZON" in text_upper:
            service_name = "Amazon"
        elif "LALAMOVE" in text_upper:
            service_name = "Lalamove"
        elif "PTAK" in text_upper:
            service_name = "PTAK"
        elif "NETFLIX" in text_upper:
            service_name = "Netflix"
        elif "MELBET" in text_upper:
            service_name = "Melbet"
        elif "TWVERIFY" in text_upper or "TWITTER" in text_upper or "X.COM" in text_upper:
            service_name = "TWVerify"
        elif "MSVERIFY" in text_upper:
            service_name = "MSVERIFY"
        elif "NCSOFT" in text_upper:
            service_name = "NCSOFT"
        elif "GOOGLE" in text_upper or "G-" in text_upper:
            service_name = "Google"
        elif "INSTAGRAM" in text_upper or "IG" in text_upper:
            service_name = "Instagram"
        elif "DISCORD" in text_upper:
            service_name = "Discord"
        elif "ZALO" in text_upper:
            service_name = "Zalo"
        elif "VERIFY" in text_upper:
            service_name = "VERIFY"

        record_service_message(service_name)

        extracted_phone = data.get("phone", "")
        if not extracted_phone or extracted_phone == "+790280****50":
            phones = re.findall(r'\+?[0-9]{10,15}', raw_text)
            if phones:
                extracted_phone = phones[0]

        if not extracted_phone:
            plus_phones = re.findall(r'\+[0-9]{10,14}', raw_text)
            if plus_phones:
                extracted_phone = plus_phones[0]

        country_display = "🇷🇺 Russia (+7)"
        country_code = "RU"
        if extracted_phone:
            c_name, c_code = get_country_info(extracted_phone)
            country_display = c_name
            country_code = c_code

        masked_phone = "+790280****50"
        if extracted_phone:
            clean_p = re.sub(r'\D', '', extracted_phone)
            if len(clean_p) >= 8:
                prefix_p = "+" + clean_p[:2]
                suffix_p = clean_p[-3:]
                masked_phone = f"{prefix_p}**{suffix_p}"
            else:
                masked_phone = extracted_phone

        pure_otp_code = otp_display.replace("-", "")

        # Form hiển thị gọn gàng, mã OTP bọc trong thẻ <code> giúp 1 chạm copy thẳng vào clipboard trên Telegram
        group_msg = (
            "⚡ <b>OTP RECEIVED</b>\n"
            "-----------------------------------\n"
            f"🇻🇳 <b>Country:</b> {country_display}\n"
            f"📞 <b>Number:</b> <code>{masked_phone}</code>\n"
            f"📱 <b>Service:</b> {service_name}\n"
            f"🔑 <b>OTP:</b> <code>{otp_display}</code>\n"
            "-----------------------------------\n"
            f"🕒 <i>{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
        )
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton(f"📋 COPY OTP • {pure_otp_code}", callback_data=f"copy_{pure_otp_code}"),
            InlineKeyboardButton("🤖 BOT", url=GROUP_OTP_LINK)
        )
        markup.add(
            InlineKeyboardButton("📢 CHANNEL", url=GROUP_OTP_LINK),
            InlineKeyboardButton("🔄 NUMBER UPDATES", url=GROUP_OTP_LINK)
        )
        
        bot.send_message(GROUP_CHAT_ID, group_msg, parse_mode="HTML", reply_markup=markup)
        return {"status": "success"}, 200
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

# ==========================================
# ⚙️ 6. QUẢN LÝ KHO SỐ & BỘ TỪ ĐIỂN QUỐC GIA
# ==========================================
USER_ACTIVE_PHONES = {}      
USER_CLICKED_NUMBERS = {}    
USER_ADD_CC_STATE = {}
GLOBAL_TAKEN_NUMBERS = set()
COUNTRY_CACHE = {}
USER_WITHDRAW_STATE = {}
USER_PENDING_WALLET = {}

USERS_FILE = "users_log.json"
WITHDRAW_HISTORY_FILE = "withdraw_history.json"
DELETED_NUMBERS_FILE = "deleted_numbers.json"
FRAUD_LOG_FILE = "fraud_tracker.json"

DELETED_NUMBERS = load_json_db(DELETED_NUMBERS_FILE)

GLOBAL_COUNTRY_PREFIXES = {
    "7": ("🇷🇺 Russia / Kazakhstan (+7)", "RU"), "1": ("🇺🇸 USA / Canada (+1)", "US"),
    "992": ("🇹🇯 Tajikistan (+992)", "TJ"), "993": ("🇹🇲 Turkmenistan (+993)", "TM"),
    "994": ("🇦🇿 Azerbaijan (+994)", "AZ"), "995": ("🇬🇪 Georgia (+995)", "GE"),
    "996": ("🇰🇬 Kyrgyzstan (+996)", "KG"), "998": ("🇺🇿 Uzbekistan (+998)", "UZ"),
    "972": ("🇮🇱 Israel (+972)", "IL"), "971": ("🇦🇪 UAE (+971)", "AE"), "966": ("🇸🇦 Saudi Arabia (+966)", "SA"),
    "965": ("🇰🇼 Kuwait (+965)", "KW"), "974": ("🇶🇦 Qatar (+974)", "QA"), "973": ("🇧🇭 Bahrain (+973)", "BH"),
    "968": ("🇴🇲 Oman (+968)", "OM"), "962": ("🇯🇴 Jordan (+962)", "JO"), "961": ("🇱🇧 Lebanon (+961)", "LB"),
    "963": ("🇸🇾 Syria (+963)", "SY"), "964": ("🇮🇶 Iraq (+964)", "IQ"), "98": ("🇮🇷 Iran (+98)", "IR"),
    "93": ("🇦🇫 Afghanistan (+93)", "AF"), "94": ("🇱🇰 Sri Lanka (+94)", "LK"), "92": ("🇵🇰 Pakistan (+92)", "PK"),
    "91": ("🇮🇳 India (+91)", "IN"), "880": ("🇧🇩 Bangladesh (+880)", "BD"), "86": ("🇨🇳 China (+86)", "CN"),
    "81": ("🇯🇵 Japan (+81)", "JP"), "82": ("🇰🇷 South Korea (+82)", "KR"), "84": ("🇻🇳 Vietnam (+84)", "VN"),
    "66": ("🇹🇭 Thailand (+66)", "TH"), "62": ("🇮🇩 Indonesia (+62)", "ID"), "60": ("🇲🇾 Malaysia (+60)", "MY"),
    "63": ("🇵🇭 Philippines (+63)", "PH"), "65": ("🇸🇬 Singapore (+65)", "SG"), "855": ("🇰🇭 Cambodia (+855)", "KH"),
    "856": ("🇱🇦 Laos (+855)", "LA"), "95": ("🇲🇲 Myanmar (+95)", "MM"), "1809": ("🇩🇴 Dominican Rep (+1-809)", "DO"),
    "52": ("🇲🇽 Mexico (+52)", "MX"), "55": ("🇧🇷 Brazil (+55)", "BR"), "54": ("🇦🇷 Argentina (+54)", "AR"),
    "57": ("🇨🇴 Colombia (+57)", "CO"), "51": ("🇵🇪 Peru (+51)", "PE"), "58": ("🇻🇪 Venezuela (+58)", "VE"),
    "56": ("🇨🇱 Chile (+56)", "CL"), "44": ("🇬🇧 United Kingdom (+44)", "UK"), "33": ("🇫🇷 France (+33)", "FR"),
    "49": ("🇩🇪 Germany (+49)", "DE"), "39": ("🇮🇹 Italy (+39)", "IT"), "34": ("🇪🇸 Spain (+34)", "ES"),
    "380": ("🇺🇦 Ukraine (+380)", "UA"), "48": ("🇵🇱 Poland (+48)", "PL"), "31": ("🇳🇱 Netherlands (+31)", "NL"),
    "32": ("🇧🇪 Belgium (+32)", "BE"), "41": ("🇨🇭 Switzerland (+41)", "CH"), "43": ("🇦🇹 Austria (+43)", "AT"),
    "46": ("🇸🇪 Sweden (+46)", "SE"), "47": ("🇳🇴 Norway (+47)", "NO"), "45": ("🇩🇰 Denmark (+45)", "DK"),
    "358": ("🇫🇮 Finland (+358)", "FI"), "353": ("🇮🇪 Ireland (+353)", "IE"), "351": ("🇵🇹 Portugal (+351)", "PT"),
    "30": ("🇬🇷 Greece (+30)", "GR"), "90": ("🇹🇷 Turkey (+90)", "TR"), "61": ("🇦🇺 Australia (+61)", "AU"),
    "64": ("🇳🇿 New Zealand (+64)", "NZ"), "20": ("🇪🇬 Egypt (+20)", "EG"), "27": ("🇿🇦 South Africa (+27)", "ZA"),
    "234": ("🇳🇬 Nigeria (+234)", "NG"), "254": ("🇰🇪 Kenya (+254)", "KE"), "212": ("🇲🇦 Morocco (+212)", "MA")
}

def get_country_info(phone):
    p = phone.replace("+", "").strip()
    for length in [4, 3, 2, 1]:
        if len(p) >= length:
            prefix = p[:length]
            if prefix in GLOBAL_COUNTRY_PREFIXES:
                return GLOBAL_COUNTRY_PREFIXES[prefix]
    return "🌐 Global Other", "OTHER"

def extract_phone_without_cc(phone):
    p = phone.replace("+", "").strip()
    for length in [4, 3, 2, 1]:
        if len(p) >= length:
            prefix = p[:length]
            if prefix in GLOBAL_COUNTRY_PREFIXES:
                return p[length:]
    return p

def load_text_batch():
    file_path = "numbers.txt"
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            temp_cache = {}
            for num_str in [l.strip() for l in lines if l.strip()]:
                digits_only = re.sub(r'\D', '', num_str)
                if len(digits_only) >= 7:
                    formatted = "+" + digits_only
                    if formatted not in DELETED_NUMBERS:
                        name, code = get_country_info(formatted)
                        if code not in temp_cache:
                            temp_cache[code] = {"name": name, "numbers": []}
                        if formatted not in temp_cache[code]["numbers"]:
                            temp_cache[code]["numbers"].append(formatted)
            global COUNTRY_CACHE
            COUNTRY_CACHE = temp_cache
            return True, len(lines)
        except Exception:
            pass
    return False, 0

load_text_batch()

def get_available_countries():
    valid = {}
    for code, data in COUNTRY_CACHE.items():
        active = [n for n in data["numbers"] if n not in DELETED_NUMBERS and n not in GLOBAL_TAKEN_NUMBERS]
        if active:
            valid[code] = f"{data['name']} — [{len(active)} Numbers]"
    return valid

def log_fraud(uid, action):
    fraud_db = load_json_db(FRAUD_LOG_FILE)
    uid_str = str(uid)
    if uid_str not in fraud_db:
        fraud_db[uid_str] = []
    fraud_db[uid_str].append({"action": action, "time": datetime.datetime.now().strftime('%H:%M:%S - %d/%m/%Y')})
    if len(fraud_db[uid_str]) > 50:
        fraud_db[uid_str] = fraud_db[uid_str][-50:]
    save_json_db(FRAUD_LOG_FILE, fraud_db)

# ==========================================
# ⌨️ 7. GIAO DIỆN BÀN PHÍM MENU DƯỚI
# ==========================================
def get_main_menu_markup(is_admin=False):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("📞 Get Number"), KeyboardButton("📊 Dashboard"))
    markup.add(KeyboardButton("🔍 Search with Prefix"), KeyboardButton("💰 My Balance"))
    markup.add(KeyboardButton("💸 Withdraw"), KeyboardButton("👤 Profile"))
    markup.add(KeyboardButton("👥 Refer"), KeyboardButton("⚡ Live Traffic"))
    markup.add(KeyboardButton("🏆 Top Users"), KeyboardButton("❓ Help"))
    if is_admin:
        markup.add(KeyboardButton("👑 Admin Panel"))
    return markup

@bot.message_handler(commands=['start'])
def cmd_start(message):
    uid = message.from_user.id
    name = message.from_user.first_name or "User"
    username = message.from_user.username or "None"
    users = load_json_db(USERS_FILE)
    if str(uid) not in users:
        users[str(uid)] = {"id": uid, "name": name, "username": username, "balance": 0.0, "referrals": 0}
        save_json_db(USERS_FILE, users)
    
    text = f"👋 Welcome <b>{name}</b> to <b>IVASMS OTP Global</b> system!\n🌐 Auto detecting 195+ countries."
    bot.send_message(uid, text, parse_mode="HTML", reply_markup=get_main_menu_markup(uid == ADMIN_ID))

@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
    uid = message.from_user.id
    text = message.text
    chat_id = message.chat.id
    name = message.from_user.first_name or "User"
    username = message.from_user.username or "None"

    try:
        bot.delete_message(chat_id, message.message_id)
    except Exception:
        pass

    if uid in USER_WITHDRAW_STATE and USER_WITHDRAW_STATE[uid]:
        wallet_addr = text.strip()
        if not re.match(r'^(EQ|UQ)[A-Za-z0-9\-_]{46}$', wallet_addr):
            bot.send_message(chat_id, "❌ <b>Invalid wallet 
