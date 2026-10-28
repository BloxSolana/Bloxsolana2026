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
# 🚀 3. ENDPOINT NHẬN SMS & LỌC OTP
# ==========================================
@app.route('/api/push-sms', methods=['POST'])
def api_push_sms_handler():
    try:
        data = request.json if request.is_json else {}
        if data.get("key", "") and data.get("key") != BRIDGE_API_KEY:
            return {"status": "error", "message": "Unauthorized"}, 403

        raw_text = data.get("raw_text", "")
        service_name = data.get("service", "WhatsApp")
        country_name = data.get("country", "Global")

        useless_phrases = ["No SMS found", "Range Count", "Client System", "Dashboard", "TRUSTED PREMIUM SMS"]
        if not raw_text or (any(p in raw_text for p in useless_phrases) and len(raw_text) < 50):
            return {"status": "ignored"}, 200

        otp_display = "Không tìm thấy"
        match_pattern = re.search(r'(?:код|code|ma|otp)[:\s\-]*([0-9]{4,6})', raw_text, re.IGNORECASE)
        if match_pattern:
            otp_display = match_pattern.group(1)
        else:
            all_nums = re.findall(r'\b\d{4,6}\b', raw_text)
            valid_nums = [n for n in all_nums if not n.startswith('2026') and not n.startswith('2025')]
            if valid_nums:
                otp_display = valid_nums[-1]

        phones = re.findall(r'\+?\d{8,15}', raw_text)
        masked_phone = data.get("phone", "") or (phones[0] if phones else "+8433****08")
        
        group_msg = (
            "👍 <b>Stock Updated!</b>\n\n"
            f"🌐 <b>Country:</b> {country_name}\n"
            f"📱 <b>Service:</b> {service_name}\n\n"
            f"📞 <b>Số điện thoại:</b> <code>{masked_phone}</code>\n"
            f"🔑 <b>Mã OTP:</b> <code>{otp_display}</code>"
        )
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(f"🚀 {country_name} {service_name} ↗", url=GROUP_OTP_LINK))
        bot.send_message(GROUP_CHAT_ID, group_msg, parse_mode="HTML", reply_markup=markup)
        return {"status": "success"}, 200
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

# ==========================================
# ⚙️ 4. QUẢN LÝ DỮ LIỆU & KHO SỐ 195+ QUỐC GIA
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
    "1": ("🇺🇸 Mỹ / Canada (+1)", "US"), "52": ("🇲🇽 Mexico (+52)", "MX"), "53": ("🇨🇺 Cuba (+53)", "CU"),
    "509": ("🇭🇹 Haiti (+509)", "HT"), "1809": ("🇩🇴 CH Dominica (+1-809)", "DO"), "502": ("🇬🇹 Guatemala (+502)", "GT"),
    "504": ("🇭🇳 Honduras (+504)", "HN"), "505": ("🇳🇮 Nicaragua (+505)", "NI"), "506": ("🇨🇷 Costa Rica (+506)", "CR"),
    "507": ("🇵🇦 Panama (+507)", "PA"), "503": ("🇸🇻 El Salvador (+503)", "SV"), "501": ("🇧🇿 Belize (+501)", "BZ"),
    "55": ("🇧🇷 Brazil (+55)", "BR"), "54": ("🇦🇷 Argentina (+54)", "AR"), "57": ("🇨🇴 Colombia (+57)", "CO"),
    "51": ("🇵🇪 Peru (+51)", "PE"), "58": ("🇻🇪 Venezuela (+58)", "VE"), "56": ("🇨🇱 Chile (+56)", "CL"),
    "593": ("🇪🇨 Ecuador (+593)", "EC"), "591": ("🇧🇴 Bolivia (+591)", "BO"), "595": ("🇵🇾 Paraguay (+595)", "PY"),
    "598": ("🇺🇾 Uruguay (+598)", "UY"), "44": ("🇬🇧 Anh (+44)", "UK"), "33": ("🇫🇷 Pháp (+33)", "FR"),
    "49": ("🇩🇪 Đức (+49)", "DE"), "39": ("🇮🇹 Ý (+39)", "IT"), "34": ("🇪🇸 Tây Ban Nha (+34)", "ES"),
    "7": ("🇷🇺 Nga (+7)", "RU"), "380": ("🇺🇦 Ukraine (+380)", "UA"), "48": ("🇵🇱 Ba Lan (+48)", "PL"),
    "31": ("🇳🇱 Hà Lan (+31)", "NL"), "32": ("🇧🇪 Bỉ (+32)", "BE"), "41": ("🇨🇭 Thụy Sĩ (+41)", "CH"),
    "43": ("🇦🇹 Áo (+43)", "AT"), "46": ("🇸🇪 Thụy Điển (+46)", "SE"), "47": ("🇳🇴 Na Uy (+47)", "NO"),
    "45": ("🇩🇰 Đan Mạch (+45)", "DK"), "358": ("🇫🇮 Phần Lan (+358)", "FI"), "353": ("🇮🇪 Ai-len (+353)", "IE"),
    "351": ("🇵🇹 Bồ Đào Nha (+351)", "PT"), "30": ("🇬🇷 Hy Lạp (+30)", "GR"), "420": ("🇨🇿 Séc (+420)", "CZ"),
    "36": ("🇭🇺 Hungary (+36)", "HU"), "40": ("🇷🇴 Romania (+40)", "RO"), "359": ("🇧🇬 Bulgaria (+359)", "BG"),
    "84": ("🇻🇳 Việt Nam (+84)", "VN"), "86": ("🇨🇳 Trung Quốc (+86)", "CN"), "81": ("🇯🇵 Nhật Bản (+81)", "JP"),
    "82": ("🇰🇷 Hàn Quốc (+82)", "KR"), "91": ("🇮🇳 Ấn Độ (+91)", "IN"), "62": ("🇮🇩 Indonesia (+62)", "ID"),
    "63": ("🇵🇭 Philippines (+63)", "PH"), "66": ("🇹🇭 Thái Lan (+66)", "TH"), "60": ("🇲🇾 Malaysia (+60)", "MY"),
    "65": ("🇸🇬 Singapore (+65)", "SG"), "92": ("🇵🇰 Pakistan (+92)", "PK"), "880": ("🇧🇩 Bangladesh (+880)", "BD"),
    "95": ("🇲🇲 Myanmar (+95)", "MM"), "855": ("🇰🇭 Campuchia (+855)", "KH"), "856": ("🇱🇦 Lào (+856)", "LA"),
    "90": ("🇹🇷 Thổ Nhĩ Kỳ (+90)", "TR"), "972": ("🇮🇱 Israel (+972)", "IL"), "966": ("🇸🇦 Ả Rập Xê Út (+966)", "SA"),
    "971": ("🇦🇪 UAE (+971)", "AE"), "61": ("🇦🇺 Úc (+61)", "AU"), "64": ("🇳🇿 New Zealand (+64)", "NZ"),
    "20": ("🇪🇬 Ai Cập (+20)", "EG"), "27": ("🇿🇦 Nam Phi (+27)", "ZA"), "234": ("🇳🇬 Nigeria (+234)", "NG")
}

def get_country_info(phone):
    p = phone.replace("+", "").strip()
    for length in [4, 3, 2, 1]:
        if len(p) >= length and p[:length] in GLOBAL_COUNTRY_PREFIXES:
            return GLOBAL_COUNTRY_PREFIXES[p[:length]]
    return "🌐 Quốc tế Khác", "OTHER"

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
            valid[code] = f"{data['name']} — [{len(active)} Số]"
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
# ⌨️ 5. GIAO DIỆN BÀN PHÍM MENU DƯỚI
# ==========================================
def get_main_menu_markup(is_admin=False):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("📞 Get Number"), KeyboardButton("🗑 Clear Prefix"))
    markup.add(KeyboardButton("🔍 Search with Prefix"))
    markup.add(KeyboardButton("💰 My Balance"), KeyboardButton("💸 Withdraw"))
    markup.add(KeyboardButton("👤 Hồ Sơ"), KeyboardButton("👥 Refer"))
    markup.add(KeyboardButton("📊 Stats"), KeyboardButton("⚡ Live Traffic"))
    markup.add(KeyboardButton("🏆 Top Users"), KeyboardButton("❓ Help"))
    if is_admin:
        markup.add(KeyboardButton("👑 Admin Panel"))
    return markup

@bot.message_handler(commands=['start'])
def cmd_start(message):
    uid = message.from_user.id
    name = message.from_user.first_name or "Bạn"
    username = message.from_user.username or "Không có"
    users = load_json_db(USERS_FILE)
    if str(uid) not in users:
        users[str(uid)] = {"id": uid, "name": name, "username": username, "balance": 0.0, "referrals": 0}
        save_json_db(USERS_FILE, users)
    
    text = f"👋 Chào mừng <b>{name}</b> đến với hệ thống <b>IVASMS OTP Global</b>!\n🌐 Tự động nhận diện 195+ quốc gia."
    bot.send_message(uid, text, parse_mode="HTML", reply_markup=get_main_menu_markup(uid == ADMIN_ID))

@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
    uid = message.from_user.id
    text = message.text
    chat_id = message.chat.id
    name = message.from_user.first_name or "Bạn"
    username = message.from_user.username or "Không có"

    try:
        bot.delete_message(chat_id, message.message_id)
    except Exception:
        pass

    if uid in USER_WITHDRAW_STATE and USER_WITHDRAW_STATE[uid]:
        wallet_addr = text.strip()
        if not re.match(r'^(EQ|UQ)[A-Za-z0-9\-_]{46}$', wallet_addr):
            bot.send_message(chat_id, "❌ <b>Ví TON không hợp lệ!</b> Phải bắt đầu bằng EQ hoặc UQ và có đúng 48 ký tự. Gửi lại:", parse_mode="HTML")
            return
        
        USER_PENDING_WALLET[uid] = wallet_addr
        USER_WITHDRAW_STATE[uid] = False
        
        users = load_json_db(USERS_FILE)
        bal = users.get(str(uid), {}).get("balance", 0.0)
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(InlineKeyboardButton("✅ Xác Nhận", callback_data="confirm_withdraw"), InlineKeyboardButton("❌ Hủy", callback_data="cancel_withdraw"))
        bot.send_message(chat_id, f"🔍 <b>XÁC NHẬN RÚT</b>\n💵 Số tiền: <b>${bal:.4f} USDT</b>\n📤 Ví: <code>{wallet_addr}</code>", parse_mode="HTML", reply_markup=markup)
        return

    if text in ["📞 Get Number", "🔍 Search with Prefix"]:
        countries = get_available_countries()
        if not countries:
            bot.send_message(chat_id, "❌ Kho số hiện tại đang trống!")
            return
        markup = InlineKeyboardMarkup(row_width=1)
        for code, label in countries.items():
            markup.add(InlineKeyboardButton(f"🌍 {label}", callback_data=f"country_{code}"))
        markup.add(InlineKeyboardButton("🔙 Quay Lại", callback_data="close_menu"))
        bot.send_message(chat_id, "🌍 <b>CHỌN QUỐC GIA:</b>", parse_mode="HTML", reply_markup=markup)

    elif text == "💰 My Balance":
        users = load_json_db(USERS_FILE)
        bal = users.get(str(uid), {}).get("balance", 0.0)
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton("💸 Withdraw (USDT TON)", callback_data="request_withdraw"), InlineKeyboardButton("🔙 Quay lại", callback_data="close_menu"))
        bot.send_message(chat_id, f"💰 <b>SỐ DƯ TÀI KHOẢN:</b>\n💵 Số dư: <code>${bal:.4f}</code>", parse_mode="HTML", reply_markup=markup)

    elif text == "💸 Withdraw":
        users = load_json_db(USERS_FILE)
        bal = users.get(str(uid), {}).get("balance", 0.0)
        if bal < 5.0:
            bot.send_message(chat_id, f"❌ Số dư hiện tại là ${bal:.4f}. Bạn cần đạt tối thiểu **$5.0** mới được phép rút tiền!", parse_mode="HTML")
            return
        USER_WITHDRAW_STATE[uid] = True
        bot.send_message(chat_id, "📥 Gửi địa chỉ ví <b>USDT mạng TON</b> của bạn (bắt đầu bằng EQ hoặc UQ):", parse_mode="HTML")

    elif text == "👤 Hồ Sơ":
        users = load_json_db(USERS_FILE)
        u_data = users.get(str(uid), {"balance": 0.0})
        profile_text = (
            "👤 <b>HỒ SƠ CÁ NHÂN</b>\n"
            "-----------------------------------\n"
            f"🏷 <b>Tên Nick:</b> {name}\n"
            f"🔗 <b>Username:</b> @{username}\n"
            f"🆔 <b>Telegram ID:</b> <code>{uid}</code>\n"
            f"💵 <b>Số dư hiện tại:</b> <code>${u_data.get('balance', 0.0):.4f}</code>"
        )
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Quay lại", callback_data="close_menu"))
        bot.send_message(chat_id, profile_text, parse_mode="HTML", reply_markup=markup)

    elif text == "👥 Refer":
        bot_info = bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={uid}"
        users = load_json_db(USERS_FILE)
        refs = users.get(str(uid), {}).get("referrals", 0)
        ref_text = f"👥 <b>MỜI BẠN BÈ NHẬN THƯỞNG</b>\n\n🔗 Link giới thiệu của bạn:\n<code>{ref_link}</code>\n\n📊 Đã mời: <b>{refs}</b> người."
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Quay lại", callback_data="close_menu"))
        bot.send_message(chat_id, ref_text, parse_mode="HTML", reply_markup=markup)

    elif text == "📊 Stats":
        stats_text = f"📊 <b>THỐNG KÊ HỆ THỐNG</b>\n-----------------------------------\n👤 ID của bạn: <code>{uid}</code>\n🟢 Trạng thái hoạt động: Ổn định (24/7)"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Quay lại", callback_data="close_menu"))
        bot.send_message(chat_id, stats_text, parse_mode="HTML", reply_markup=markup)

    elif text == "⚡ Live Traffic":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🚀 Mở Kênh Live OTP", url=GROUP_OTP_LINK), InlineKeyboardButton("🔙 Quay lại", callback_data="close_menu"))
        bot.send_message(chat_id, f"⚡ Kênh thông báo Live Traffic chính thức:", parse_mode="HTML", reply_markup=markup)

    elif text == "🏆 Top Users":
        users_db = load_json_db(USERS_FILE)
        text_top = "🏆 <b>BẢNG XẾP HẠNG NGƯỜI DÙNG (TOP SỐ DƯ):</b>\n\n"
        if not users_db:
            text_top += "<i>Chưa có dữ liệu.</i>"
        else:
            sorted_users = sorted(users_db.values(), key=lambda x: x.get('balance', 0.0), reverse=True)
            for idx, u_info in enumerate(sorted_users[:10], 1):
                text_top += f"<b>#{idx}</b> | 👤 {u_info.get('name')} — <code>${u_info.get('balance', 0.0):.4f}</code>\n"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Quay lại", callback_data="close_menu"))
        bot.send_message(chat_id, text_top, parse_mode="HTML", reply_markup=markup)

    elif text == "❓ Help":
        help_text = "❓ <b>HƯỚNG DẪN SỬ DỤNG</b>\n- Chọn <b>Get Number</b> để lấy số điện thoại nhận OTP.\n- Số có hiệu lực trong 15 phút, có thể bấm đổi số mới bất cứ lúc nào.\n- Số dư tối thiểu để rút là 5$."
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Quay lại", callback_data="close_menu"))
        bot.send_message(chat_id, help_text, parse_mode="HTML", reply_markup=markup)

    elif text == "👑 Admin Panel" and uid == ADMIN_ID:
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("💸 Duyệt lệnh rút tiền", callback_data="admin_view_withdraws"),
            InlineKeyboardButton("🛡 Kiểm tra gian lận (Fraud Log)", callback_data="admin_view_fraud"),
            InlineKeyboardButton("🔄 Sync số mới", callback_data="admin_reload"),
            InlineKeyboardButton("🔙 Quay lại", callback_data="close_menu")
        )
        bot.send_message(chat_id, "👑 <b>BẢNG ADMIN TỐI CAO</b>", parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    try:
        uid = call.from_user.id
        data = call.data
        chat_id = call.message.chat.id
        msg_id = call.message.message_id
        
        if data == "close_menu":
            bot.answer_callback_query(call.id, "Đã đóng.")
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

                masked = selected_num[:4] + "****" + selected_num[-2:]
                
                markup = InlineKeyboardMarkup(row_width=1)
                markup.add(
                    InlineKeyboardButton(f"📞 Số: {masked} (Hiệu lực 15p)", callback_data=f"getnum_{selected_num}"),
                    InlineKeyboardButton("🔄 Đổi số khác ngay", callback_data=f"country_{code}"),
                    InlineKeyboardButton("🔙 Quay lại danh sách", callback_data="back_to_countries")
                )
                bot.edit_message_text(f"📋 <b>Kho số quốc gia ({code}):</b>\nNhấn vào số để xác nhận nhận diện hoặc đổi số ngay lập tức.", chat_id, msg_id, parse_mode="HTML", reply_markup=markup)

        elif data == "back_to_countries":
            countries = get_available_countries()
            markup = InlineKeyboardMarkup(row_width=1)
            for code, label in countries.items():
                markup.add(InlineKeyboardButton(f"🌍 {label}", callback_data=f"country_{code}"))
            markup.add(InlineKeyboardButton("🔙 Quay Lại", callback_data="close_menu"))
            bot.edit_message_text("🌍 <b>CHỌN QUỐC GIA:</b>", chat_id, msg_id, parse_mode="HTML", reply_markup=markup)

        elif data.startswith("getnum_"):
            phone = data.replace("getnum_", "")
            USER_ACTIVE_PHONES[chat_id] = {"phone": phone, "expire": time.time() + 900}
            log_fraud(uid, f"Nhận số thành công: {phone}")
            bot.edit_message_text(
                f"✅ <b>ĐÃ CẤP SỐ THÀNH CÔNG!</b>\n📞 <code>{phone}</code>\n⏳ Hiệu lực trong 15 phút. Đang chờ mã OTP từ hệ thống...", 
                chat_id, msg_id, parse_mode="HTML"
            )

        elif data == "request_withdraw":
            users = load_json_db(USERS_FILE)
            bal = users.get(str(uid), {}).get("balance", 0.0)
            if bal < 5.0:
                bot.answer_callback_query(call.id, f"Chưa đủ điều kiện rút 5$! (Hiện có ${bal:.4f})", show_alert=True)
                return
            bot.answer_callback_query(call.id)
            USER_WITHDRAW_STATE[uid] = True
            bot.send_message(chat_id, "📥 Gửi địa chỉ ví <b>USDT mạng TON</b> của bạn:", parse_mode="HTML")
            try:
                bot.delete_message(chat_id, msg_id)
            except Exception:
                pass

        elif data == "cancel_withdraw":
            USER_WITHDRAW_STATE[uid] = False
            USER_PENDING_WALLET.pop(uid, None)
            bot.answer_callback_query(call.id, "Đã hủy yêu cầu rút.")
            try:
                bot.delete_message(chat_id, msg_id)
            except Exception:
                pass

        elif data == "confirm_withdraw":
            wallet = USER_PENDING_WALLET.pop(uid, None)
            USER_WITHDRAW_STATE[uid] = False
            if not wallet:
                bot.answer_callback_query(call.id, "Phiên giao dịch hết hạn!", show_alert=True)
                return
            
            users = load_json_db(USERS_FILE)
            uid_str = str(uid)
            bal = users.get(uid_str, {}).get("balance", 0.0)
            
            if bal < 5.0:
                bot.answer_callback_query(call.id, "Số dư chưa đạt tối thiểu 5$!", show_alert=True)
                return
            
            users[uid_str]["balance"] = 0.0
            save_json_db(USERS_FILE, users)
            
            history = load_json_db(WITHDRAW_HISTORY_FILE)
            if uid_str not in history:
                history[uid_str] = []
            history[uid_str].append({
                "amount": bal,
                "wallet": wallet,
                "status": "⏳ Đang chờ duyệt",
                "time": datetime.datetime.now().strftime('%H:%M:%S - %d/%m/%Y')
            })
            save_json_db(WITHDRAW_HISTORY_FILE, history)
            log_fraud(uid, f"Tạo lệnh rút tiền: ${bal:.4f} về ví {wallet}")
            
            bot.answer_callback_query(call.id, "Gửi lệnh rút thành công!")
            bot.edit_message_text(f"✅ <b>Gửi lệnh rút thành công!</b>\nLệnh đã chuyển vào danh sách chờ duyệt của Admin.", chat_id, msg_id, parse_mode="HTML")

        elif data == "admin_view_withdraws" and uid == ADMIN_ID:
            history = load_json_db(WITHDRAW_HISTORY_FILE)
            pending = [(u, i, it) for u, items in history.items() for i, it in enumerate(items) if "⏳" in it.get("status", "")]
            if not pending:
                bot.answer_callback_query(call.id, "Không có lệnh rút nào đang chờ!", show_alert=True)
                return
            markup = InlineKeyboardMarkup(row_width=1)
            text_p = "💸 <b>LỆNH RÚT ĐANG CHỜ DUYỆT:</b>\n\n"
            for u_id, idx, it in pending[:5]:
                text_p += f"• ID {u_id} | ${it.get('amount'):.4f}\n"
                markup.add(InlineKeyboardButton(f"✅ Duyệt ID {u_id} (${it.get('amount')})", callback_data=f"done_w_{u_id}_{idx}"))
            markup.add(InlineKeyboardButton("🔙 Quay lại", callback_data="close_menu"))
            bot.edit_message_text(text_p, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)

        elif data.startswith("done_w_") and uid == ADMIN_ID:
            parts = data.split("_")
            target_uid, item_idx = parts[2], int(parts[3])
            history = load_json_db(WITHDRAW_HISTORY_FILE)
            if target_uid in history and len(history[target_uid]) > item_idx:
                history[target_uid][item_idx]["status"] = "✅ Đã thanh toán thành công"
                save_json_db(WITHDRAW_HISTORY_FILE, history)
                try:
                    bot.send_message(int(target_uid), "🎉 <b>Yêu cầu rút tiền của bạn đã được Admin duyệt và thanh toán USDT thành công!</b>", parse_mode="HTML")
                except Exception:
                    pass
                bot.answer_callback_query(call.id, "Đã duyệt lệnh rút!", show_alert=True)

        elif data == "admin_view_fraud" and uid == ADMIN_ID:
            fraud_db = load_json_db(FRAUD_LOG_FILE)
            text_f = "🛡 <b>LOG HOẠT ĐỘNG & KIỂM TRA GIAN LẬN:</b>\n\n"
            if not fraud_db:
                text_f += "<i>Chưa có log bất thường.</i>"
            else:
                for u_id, logs in list(fraud_db.items())[-5:]:
                    text_f += f"👤 <b>ID:</b> <code>{u_id}</code>\n"
                    for l in logs[-3:]:
                        text_f += f" - {l['action']} ({l['time']})\n"
                    text_f += "-------------------\n"
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔙 Quay lại", callback_data="close_menu"))
            bot.edit_message_text(text_f, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)

        elif data == "admin_reload" and uid == ADMIN_ID:
            _, count = load_text_batch()
            bot.answer_callback_query(call.id, f"Đã sync thành công {count} dòng số!", show_alert=True)

    except Exception as e:
        print(f"Lỗi callback: {e}")

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
        print(f"🔗 Đã thiết lập Webhook tự động tới: {RENDER_URL}/{TOKEN}")
    
    app.run(host='0.0.0.0', port=port)
