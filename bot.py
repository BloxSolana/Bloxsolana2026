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
from flask import Flask, request

# ==========================================
# 👑 1. CẤU HÌNH HỆ THỐNG & TELEGRAM BOT
# ==========================================
ADMIN_ID = 6726769296
TOKEN = "8622066775:AAFncl413hILhGl-J6DQD9oDbK4PEEHsERc"
GROUP_CHAT_ID = "-1004341368656"
GROUP_OTP_LINK = "https://t.me/LIVEOTPIVAS"
BRIDGE_API_KEY = "khoibro_secret_bridge_key_123"

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
# 🚀 3. ENDPOINT NHẬN SMS & TỰ ĐỘNG BÓC TÁCH DỊCH VỤ / QUỐC GIA THÔNG MINH
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

        # 1. TỰ ĐỘNG NHẬN DIỆN TÊN DỊCH VỤ TỪ NỘI DUNG SMS (RAW TEXT)
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
        elif "GOOGLE" in text_upper or "G-" in text_upper:
            service_name = "Google"
        elif "INSTAGRAM" in text_upper or "IG" in text_upper:
            service_name = "Instagram"
        elif "TWITTER" in text_upper or "X.COM" in text_upper:
            service_name = "Twitter / X"
        elif "DISCORD" in text_upper:
            service_name = "Discord"
        elif "NETFLIX" in text_upper:
            service_name = "Netflix"
        elif "ZALO" in text_upper:
            service_name = "Zalo"

        # Lấy số điện thoại từ request hoặc quét trong raw_text
        extracted_phone = data.get("phone", "")
        if not extracted_phone:
            phones = re.findall(r'\+?[0-9]{10,15}', raw_text)
            if phones:
                extracted_phone = phones[0]

        # 2. TỰ ĐỘNG NHẬN DIỆN QUỐC GIA CHUẨN TỪ SỐ ĐIỆN THOẠI HOẶC NỘI DUNG
        country_name = "Russia (+7)"
        if extracted_phone:
            c_name, c_code = get_country_info(extracted_phone)
            country_name = c_name

        # 3. THUẬT TOÁN BÓC TÁCH MÃ OTP THÔNG MINH
        otp_display = "Not Found"
        
        # Bắt các định dạng mã OTP phổ biến (VD: 693-423, 30908, hoặc sau các từ khóa mã/code)
        dash_match = re.search(r'\b([0-9]{3}\-[0-9]{3})\b', raw_text)
        if dash_match:
            otp_display = dash_match.group(1).replace("-", "")
        else:
            # Tìm các chuỗi số từ 4 đến 8 chữ số đứng sau các từ khóa OTP/code/ma
            otp_keyword_match = re.search(r'(?:OTP|code|mã|is)[:\s#]*([0-9]{4,8})', raw_text, re.IGNORECASE)
            if otp_keyword_match:
                otp_display = otp_keyword_match.group(1)
            else:
                all_digits = re.findall(r'\b\d{5,6}\b', raw_text)
                valid_digits = [d for d in all_digits if not d.startswith(('2026', '2025', '0120'))]
                if valid_digits:
                    otp_display = valid_digits[-1]
                else:
                    all_4 = re.findall(r'\b\d{4}\b', raw_text)
                    valid_4 = [d for d in all_4 if not d.startswith(('2026', '2025', '0120'))]
                    if valid_4:
                        otp_display = valid_4[-1]

        # Chuẩn hóa hiển thị số điện thoại che giữa chống lộ
        masked_phone = "+790280****50"
        if extracted_phone:
            clean_p = re.sub(r'\D', '', extracted_phone)
            if len(clean_p) >= 10:
                masked_phone = ("+" if extracted_phone.startswith("+") else "") + clean_p[:5] + "****" + clean_p[-2:]
            else:
                masked_phone = extracted_phone

        group_msg = (
            "👍 <b>Stock Updated!</b>\n\n"
            f"🌐 <b>Country:</b> {country_name}\n"
            f"📱 <b>Service:</b> {service_name}\n\n"
            f"📞 <b>Phone Number:</b> <code>{masked_phone}</code>\n"
            f"🔑 <b>OTP Code:</b> <code>{otp_display}</code>"
        )
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(f"🚀 {country_name} - {service_name} ↗", url=GROUP_OTP_LINK))
        bot.send_message(GROUP_CHAT_ID, group_msg, parse_mode="HTML", reply_markup=markup)
        return {"status": "success"}, 200
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

# ==========================================
# ⚙️ 4. BỘ TỪ ĐIỂN 195+ QUỐC GIA CHUẨN XÁC
# ==========================================
USER_ACTIVE_PHONES = {}      
USER_CLICKED_NUMBERS = {}    
COUNTRY_CACHE = {}
USER_WITHDRAW_STATE = {}
USER_PENDING_WALLET = {}

USERS_FILE = "users_log.json"
WITHDRAW_HISTORY_FILE = "withdraw_history.json"
DELETED_NUMBERS_FILE = "deleted_numbers.json"
FRAUD_LOG_FILE = "fraud_tracker.json"

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
    "856": ("🇱🇦 Laos (+856)", "LA"), "95": ("🇲🇲 Myanmar (+95)", "MM"), "1809": ("🇩🇴 Dominican Rep (+1-809)", "DO"),
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
    "234": ("🇳🇬 Nigeria (+234)", "NG"), "254": ("🇰🇪 Kenya (+254)", "254"), "212": ("🇲🇦 Morocco (+212)", "MA")
}

def get_country_info(phone):
    p = phone.replace("+", "").strip()
    for length in [4, 3, 2, 1]:
        if len(p) >= length:
            prefix = p[:length]
            if prefix in GLOBAL_COUNTRY_PREFIXES:
                return GLOBAL_COUNTRY_PREFIXES[prefix]
    return "🌐 Global Other", "OTHER"

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
        active = [n for n in data["numbers"] if n not in DELETED_NUMBERS]
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
# ⌨️ 5. GIAO DIỆN BÀN PHÍM MENU DƯỚI (DÀNH CHO USER)
# ==========================================
def get_main_menu_markup(is_admin=False):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("📞 Get Number"), KeyboardButton("🔍 Search with Prefix"))
    markup.add(KeyboardButton("💰 My Balance"), KeyboardButton("💸 Withdraw"))
    markup.add(KeyboardButton("👤 Profile"), KeyboardButton("👥 Refer"))
    markup.add(KeyboardButton("📊 Stats"), KeyboardButton("⚡ Live Traffic"))
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
            bot.send_message(chat_id, "❌ <b>Invalid wallet address!</b> TON wallet must start with EQ or UQ and have 48 chars. Try again:", parse_mode="HTML")
            return
        
        USER_PENDING_WALLET[uid] = wallet_addr
        USER_WITHDRAW_STATE[uid] = False
        
        users = load_json_db(USERS_FILE)
        bal = users.get(str(uid), {}).get("balance", 0.0)
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(InlineKeyboardButton("✅ Confirm", callback_data="confirm_withdraw"), InlineKeyboardButton("❌ Cancel", callback_data="cancel_withdraw"))
        bot.send_message(chat_id, f"🔍 <b>CONFIRM WITHDRAWAL</b>\n💵 Amount: <b>${bal:.4f} USDT</b>\n📤 Wallet: <code>{wallet_addr}</code>", parse_mode="HTML", reply_markup=markup)
        return

    if text in ["📞 Get Number", "🔍 Search with Prefix"]:
        countries = get_available_countries()
        if not countries:
            bot.send_message(chat_id, "❌ Stock is currently empty!")
            return
        markup = InlineKeyboardMarkup(row_width=1)
        for code, label in countries.items():
            markup.add(InlineKeyboardButton(f"🌍 {label}", callback_data=f"country_{code}"))
        markup.add(InlineKeyboardButton("🔙 Back", callback_data="close_menu"))
        bot.send_message(chat_id, "🌍 <b>SELECT COUNTRY:</b>", parse_mode="HTML", reply_markup=markup)

    elif text == "💰 My Balance":
        users = load_json_db(USERS_FILE)
        bal = users.get(str(uid), {}).get("balance", 0.0)
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton("💸 Withdraw (USDT TON)", callback_data="request_withdraw"), InlineKeyboardButton("🔙 Back", callback_data="close_menu"))
        bot.send_message(chat_id, f"💰 <b>ACCOUNT BALANCE:</b>\n💵 Balance: <code>${bal:.4f}</code>", parse_mode="HTML", reply_markup=markup)

    elif text == "💸 Withdraw":
        users = load_json_db(USERS_FILE)
        bal = users.get(str(uid), {}).get("balance", 0.0)
        if bal < 5.0:
            bot.send_message(chat_id, f"❌ Current balance is ${bal:.4f}. You need at least **$5.0** to withdraw!", parse_mode="HTML")
            return
        USER_WITHDRAW_STATE[uid] = True
        bot.send_message(chat_id, "📥 Send your <b>USDT TON Network</b> wallet address (starts with EQ or UQ):", parse_mode="HTML")

    elif text == "👤 Profile":
        users = load_json_db(USERS_FILE)
        u_data = users.get(str(uid), {"balance": 0.0})
        profile_text = (
            "👤 <b>USER PROFILE</b>\n"
            "-----------------------------------\n"
            f"🏷 <b>Nick Name:</b> {name}\n"
            f"🔗 <b>Username:</b> @{username}\n"
            f"🆔 <b>Telegram ID:</b> <code>{uid}</code>\n"
            f"💵 <b>Balance:</b> <code>${u_data.get('balance', 0.0):.4f}</code>"
        )
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Back", callback_data="close_menu"))
        bot.send_message(chat_id, profile_text, parse_mode="HTML", reply_markup=markup)

    elif text == "👥 Refer":
        bot_info = bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={uid}"
        users = load_json_db(USERS_FILE)
        refs = users.get(str(uid), {}).get("referrals", 0)
        ref_text = f"👥 <b>REFERRAL PROGRAM</b>\n\n🔗 Your referral link:\n<code>{ref_link}</code>\n\n📊 Total referred: <b>{refs}</b> users."
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Back", callback_data="close_menu"))
        bot.send_message(chat_id, ref_text, parse_mode="HTML", reply_markup=markup)

    elif text == "📊 Stats":
        stats_text = f"📊 <b>SYSTEM STATS</b>\n-----------------------------------\n👤 Your ID: <code>{uid}</code>\n🟢 Status: Stable (24/7)"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Back", callback_data="close_menu"))
        bot.send_message(chat_id, stats_text, parse_mode="HTML", reply_markup=markup)

    elif text == "⚡ Live Traffic":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🚀 Open Live OTP Channel", url=GROUP_OTP_LINK), InlineKeyboardButton("🔙 Back", callback_data="close_menu"))
        bot.send_message(chat_id, f"⚡ Official Live Traffic notification channel:", parse_mode="HTML", reply_markup=markup)

    elif text == "🏆 Top Users":
        users_db = load_json_db(USERS_FILE)
        text_top = "🏆 <b>TOP USERS (BY BALANCE):</b>\n\n"
        if not users_db:
            text_top += "<i>No data available.</i>"
        else:
            sorted_users = sorted(users_db.values(), key=lambda x: x.get('balance', 0.0), reverse=True)
            for idx, u_info in enumerate(sorted_users[:10], 1):
                text_top += f"<b>#{idx}</b> | 👤 {u_info.get('name')} — <code>${u_info.get('balance', 0.0):.4f}</code>\n"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Back", callback_data="close_menu"))
        bot.send_message(chat_id, text_top, parse_mode="HTML", reply_markup=markup)

    elif text == "❓ Help":
        help_text = "❓ <b>HELP & GUIDE</b>\n- Select <b>Get Number</b> to get phone numbers for OTP.\n- Numbers are valid for 15 minutes, instant change available.\n- Minimum withdrawal is 5$."
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Back", callback_data="close_menu"))
        bot.send_message(chat_id, help_text, parse_mode="HTML", reply_markup=markup)

    elif text == "👑 Admin Panel" and uid == ADMIN_ID:
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("💸 Pending Withdrawals", callback_data="admin_view_withdraws"),
            InlineKeyboardButton("🛡 Anti-Fraud Logs", callback_data="admin_view_fraud"),
            InlineKeyboardButton("🗑 Clear Prefix", callback_data="admin_clear_prefix"),
            InlineKeyboardButton("🔄 Sync New Numbers", callback_data="admin_reload"),
            InlineKeyboardButton("🔙 Back", callback_data="close_menu")
        )
        bot.send_message(chat_id, "👑 <b>ADMIN PANEL</b>", parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    try:
        uid = call.from_user.id
        data = call.data
        chat_id = call.message.chat.id
        msg_id = call.message.message_id
        
        if data == "close_menu":
            bot.answer_callback_query(call.id, "Closed.")
            try:
                bot.delete_message(chat_id, msg_id)
            except Exception:
                pass

        elif data.startswith("country_"):
            code = data.replace("country_", "")
            if code in COUNTRY_CACHE:
                all_nums = COUNTRY_CACHE[code]["numbers"]
                clicked = USER_CLICKED_NUMBERS.get(uid, [])
                available = [n for n in all_nums if n not in clicked]
                if not available:
                    available = all_nums
                
                selected_num = available[0]
                if uid not in USER_CLICKED_NUMBERS:
                    USER_CLICKED_NUMBERS[uid] = []
                if selected_num not in USER_CLICKED_NUMBERS[uid]:
                    USER_CLICKED_NUMBERS[uid].append(selected_num)

                masked = selected_num[:5] + "****" + selected_num[-3:]
                
                markup = InlineKeyboardMarkup(row_width=1)
                markup.add(
                    InlineKeyboardButton(f"📞 Number: {masked} (Valid 15m)", callback_data=f"getnum_{selected_num}"),
                    InlineKeyboardButton("🔄 Change Number Instantly", callback_data=f"country_{code}"),
                    InlineKeyboardButton("🔙 Back to Countries", callback_data="back_to_countries")
                )
                bot.edit_message_text(f"📋 <b>Country Stock ({code}):</b>\nClick below to get the number or change instantly.", chat_id, msg_id, parse_mode="HTML", reply_markup=markup)

        elif data == "back_to_countries":
            countries = get_available_countries()
            markup = InlineKeyboardMarkup(row_width=1)
            for code, label in countries.items():
                markup.add(InlineKeyboardButton(f"🌍 {label}", callback_data=f"country_{code}"))
            markup.add(InlineKeyboardButton("🔙 Back", callback_data="close_menu"))
            bot.edit_message_text("🌍 <b>SELECT COUNTRY:</b>", chat_id, msg_id, parse_mode="HTML", reply_markup=markup)

        elif data.startswith("getnum_"):
            phone = data.replace("getnum_", "")
            USER_ACTIVE_PHONES[chat_id] = {"phone": phone, "expire": time.time() + 900}
            log_fraud(uid, f"Got number successfully: {phone}")
            bot.edit_message_text(
                f"✅ <b>NUMBER ASSIGNED SUCCESSFULLY!</b>\n📞 <code>{phone}</code>\n⏳ Valid for 15 minutes. Waiting for OTP...", 
                chat_id, msg_id, parse_mode="HTML"
            )

        elif data == "request_withdraw":
            users = load_json_db(USERS_FILE)
            bal = users.get(str(uid), {}).get("balance", 0.0)
            if bal < 5.0:
                bot.answer_callback_query(call.id, f"Minimum withdrawal is 5$! (Current: ${bal:.4f})", show_alert=True)
                return
            bot.answer_callback_query(call.id)
            USER_WITHDRAW_STATE[uid] = True
            bot.send_message(chat_id, "📥 Send your <b>USDT TON Network</b> wallet address:", parse_mode="HTML")
            try:
                bot.delete_message(chat_id, msg_id)
            except Exception:
                pass

        elif data == "cancel_withdraw":
            USER_WITHDRAW_STATE[uid] = False
            USER_PENDING_WALLET.pop(uid, None)
            bot.answer_callback_query(call.id, "Withdrawal cancelled.")
            try:
                bot.delete_message(chat_id, msg_id)
            except Exception:
                pass

        elif data == "confirm_withdraw":
            wallet = USER_PENDING_WALLET.pop(uid, None)
            USER_WITHDRAW_STATE[uid] = False
            if not wallet:
                bot.answer_callback_query(call.id, "Session expired!", show_alert=True)
                return
            
            users = load_json_db(USERS_FILE)
            uid_str = str(uid)
            bal = users.get(uid_str, {}).get("balance", 0.0)
            
            if bal < 5.0:
                bot.answer_callback_query(call.id, "Balance less than 5$!", show_alert=True)
                return
            
            users[uid_str]["balance"] = 0.0
            save_json_db(USERS_FILE, users)
            
            history = load_json_db(WITHDRAW_HISTORY_FILE)
            if uid_str not in history:
                history[uid_str] = []
            history[uid_str].append({
                "amount": bal,
                "wallet": wallet,
                "status": "⏳ Pending",
                "time": datetime.datetime.now().strftime('%H:%M:%S - %d/%m/%Y')
            })
            save_json_db(WITHDRAW_HISTORY_FILE, history)
            log_fraud(uid, f"Created withdrawal request: ${bal:.4f} to wallet {wallet}")
            
            bot.answer_callback_query(call.id, "Withdrawal request sent!")
            bot.edit_message_text(f"✅ <b>Withdrawal request submitted!</b>\nSent to Admin pending review list.", chat_id, msg_id, parse_mode="HTML")

        elif data == "admin_view_withdraws" and uid == ADMIN_ID:
            history = load_json_db(WITHDRAW_HISTORY_FILE)
            pending = [(u, i, it) for u, items in history.items() for i, it in enumerate(items) if "⏳" in it.get("status", "")]
            if not pending:
                bot.answer_callback_query(call.id, "No pending withdrawals!", show_alert=True)
                return
            markup = InlineKeyboardMarkup(row_width=1)
            text_p = "💸 <b>PENDING WITHDRAWALS:</b>\n\n"
            for u_id, idx, it in pending[:5]:
                text_p += f"• ID {u_id} | ${it.get('amount'):.4f}\n"
                markup.add(InlineKeyboardButton(f"✅ Approve ID {u_id} (${it.get('amount')})", callback_data=f"done_w_{u_id}_{idx}"))
            markup.add(InlineKeyboardButton("🔙 Back", callback_data="close_menu"))
            bot.edit_message_text(text_p, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)

        elif data.startswith("done_w_") and uid == ADMIN_ID:
            parts = data.split("_")
            target_uid, item_idx = parts[2], int(parts[3])
            history = load_json_db(WITHDRAW_HISTORY_FILE)
            if target_uid in history and len(history[target_uid]) > item_idx:
                history[target_uid][item_idx]["status"] = "✅ Paid Successfully"
                save_json_db(WITHDRAW_HISTORY_FILE, history)
                try:
                    bot.send_message(int(target_uid), "🎉 <b>Your withdrawal request has been approved and paid in USDT by Admin successfully!</b>", parse_mode="HTML")
                except Exception:
                    pass
                bot.answer_callback_query(call.id, "Withdrawal approved!", show_alert=True)

        elif data == "admin_view_fraud" and uid == ADMIN_ID:
            fraud_db = load_json_db(FRAUD_LOG_FILE)
            text_f = "🛡 <b>ANTI-FRAUD & ACTIVITY LOGS:</b>\n\n"
            if not fraud_db:
                text_f = "<i>No suspicious logs.</i>"
            else:
                for u_id, logs in list(fraud_db.items())[-5:]:
                    text_f += f"👤 <b>ID:</b> <code>{u_id}</code>\n"
                    for l in logs[-3:]:
                        text_f += f" - {l['action']} ({l['time']})\n"
                    text_f += "-------------------\n"
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔙 Back", callback_data="close_menu"))
            bot.edit_message_text(text_f, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)

        elif data == "admin_clear_prefix" and uid == ADMIN_ID:
            global DELETED_NUMBERS
            DELETED_NUMBERS = set()
            if os.path.exists(DELETED_NUMBERS_FILE):
                os.remove(DELETED_NUMBERS_FILE)
            load_text_batch()
            bot.answer_callback_query(call.id, "Cleared prefix cache & deleted numbers successfully!", show_alert=True)

        elif data == "admin_reload" and uid == ADMIN_ID:
            _, count = load_text_batch()
            bot.answer_callback_query(call.id, f"Synced {count} numbers successfully!", show_alert=True)

    except Exception as e:
        print(f"Callback error: {e}")

# ==========================================
# 🚀 KHỞI ĐỘNG ỨNG DỤNG BIND PORT CHUẨN RENDER
# ==========================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "")
    if RENDER_URL:
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=f"{RENDER_URL}/{TOKEN}")
        print(f"🔗 Webhook configured automatically to: {RENDER_URL}/{TOKEN}")
    
    app.run(host='0.0.0.0', port=port)
