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
# 👑 1. CẤU HÌNH ADMIN TỐI CAO & TELEGRAM BOT
# ==========================================
ADMIN_ID = 6726769296
TOKEN = "8622066775:AAFncl413hILhGl-J6DQD9oDbK4PEEHsERc"
GROUP_CHAT_ID = "-1004341368656"
GROUP_OTP_LINK = "https://t.me/LIVEOTPIVAS"
BRIDGE_API_KEY = "khoibro_secret_bridge_key_123"

bot = telebot.TeleBot(TOKEN)

# ==========================================
# 🌐 2. FLASK WEB SERVER (CHUẨN PORT RENDER 24/7)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot IVASMS OTP Global Webhook Server đang chạy 24/7 trên Render!"

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        return '', 403

# ==========================================
# 🚀 3. ENDPOINT NHẬN SMS: BẮT TRỌN OTP, ẨN RÁC
# ==========================================
@app.route('/api/push-sms', methods=['POST'])
def api_push_sms_handler():
    try:
        data = request.json if request.is_json else {}
        client_key = data.get("key", "")
        if client_key and client_key != BRIDGE_API_KEY:
            return {"status": "error", "message": "Unauthorized API Key"}, 403

        raw_text = data.get("raw_text", "")
        service_name = data.get("service", "WhatsApp")
        country_name = data.get("country", "Global")

        useless_phrases = [
            "No SMS found", "Range Count", "Client System", "Client Active SMS", 
            "My Numbers", "My SMS Statistics", "Test System", "Invoices system", 
            "Dashboard", "Sender Message Time Revenue", "TRUSTED PREMIUM SMS",
            "Account Login Email address Password Remember me Forgot"
        ]
        if not raw_text or (any(phrase in raw_text for phrase in useless_phrases) and len(raw_text) < 50):
            return {"status": "ignored", "message": "Ignored useless text"}, 200

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
        masked_phone = data.get("phone", "")
        if not masked_phone and phones:
            p = phones[0]
            clean_p = re.sub(r'\D', '', p)
            if len(clean_p) >= 8:
                masked_phone = ("+" if p.startswith("+") else "") + clean_p[:4] + "****" + clean_p[-2:]
            else:
                masked_phone = p
        if not masked_phone:
            masked_phone = "+8433****08"

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
        return {"status": "success", "message": "SMS handled successfully"}, 200
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

# ==========================================
# ⚙️ 4. QUẢN LÝ DỮ LIỆU & KHO SỐ
# ==========================================
USER_ACTIVE_PHONES = {}      
OTP_ACTIVE_SESSIONS = {}     
PHONE_CREATION_TIME = {}     
COUNTRY_CACHE = {}           
USER_WITHDRAW_STATE = {}     
USER_PENDING_WALLET = {}     

USERS_FILE = "users_log.json"
STATS_FILE = "otp_stats.json"
SPAM_TRACKER_FILE = "spam_tracker.json"
SETTINGS_FILE = "settings.json"
WITHDRAW_HISTORY_FILE = "withdraw_history.json"
DELETED_NUMBERS_FILE = "deleted_numbers.json"
USER_LAST_ACTION = {}        

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

def load_deleted_numbers():
    if os.path.exists(DELETED_NUMBERS_FILE):
        try:
            with open(DELETED_NUMBERS_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

DELETED_NUMBERS = load_deleted_numbers()

def save_deleted_numbers(deleted_set):
    try:
        with open(DELETED_NUMBERS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(deleted_set), f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def get_user(uid, name="", username=""):
    users = load_json_db(USERS_FILE)
    uid_str = str(uid)
    if uid_str not in users:
        users[uid_str] = {
            "id": uid, "name": name or "Ẩn danh", "username": username or "Không có",
            "balance": 0.0, "referrals": 0, "referral_earnings": 0.0,
            "referred_by": None, "joined_at": datetime.datetime.now().strftime('%H:%M:%S - %d/%m/%Y')
        }
        save_json_db(USERS_FILE, users)
    return users[uid_str]

def mask_phone_number(phone):
    p = phone.strip()
    return p[:4] + "****" + p[-2:] if len(p) > 6 else p

def check_user_status(user_id, name=""):
    if user_id == ADMIN_ID:
        return True, ""
    spam_data = load_json_db(SPAM_TRACKER_FILE)
    uid = str(user_id)
    now = time.time()
    if uid in spam_data:
        info = spam_data[uid]
        ban_until = info.get("ban_until", 0)
        if ban_until == 0 or now < ban_until:
            return False, "⛔ Tài khoản của bạn đang bị khóa tạm thời do thao tác quá nhanh."
    return True, ""

# ==========================================
# 🌍 5. BỘ TỪ ĐIỂN 195+ QUỐC GIA ĐẦY ĐỦ NHẤT
# ==========================================
GLOBAL_COUNTRY_PREFIXES = {
    "1": ("🇺🇸 Mỹ / Canada (+1)", "US"), "52": ("🇲🇽 Mexico (+52)", "MX"), "53": ("🇨🇺 Cuba (+53)", "CU"),
    "509": ("🇭🇹 Haiti (+509)", "HT"), "1809": ("🇩🇴 CH Dominica (+1-809)", "DO"), "1829": ("🇩🇴 CH Dominica (+1-829)", "DO_2"),
    "1849": ("🇩🇴 CH Dominica (+1-849)", "DO_3"), "502": ("🇬🇹 Guatemala (+502)", "GT"), "504": ("🇭🇳 Honduras (+504)", "HN"),
    "505": ("🇳🇮 Nicaragua (+505)", "NI"), "506": ("🇨🇷 Costa Rica (+506)", "CR"), "507": ("🇵🇦 Panama (+507)", "PA"),
    "503": ("🇸🇻 El Salvador (+503)", "SV"), "501": ("🇧🇿 Belize (+501)", "BZ"), "1876": ("🇯🇲 Jamaica (+1-876)", "JM"),
    "1441": ("🇧🇲 Bermuda (+1-441)", "BM"), "1242": ("🇧🇸 Bahamas (+1-242)", "BS"), "1246": ("🇧🇧 Barbados (+1-246)", "BB"),
    "1264": ("🇦🇮 Anguilla (+1-264)", "AI"), "1268": ("🇦🇬 Antigua & Barbuda (+1-268)", "AG"), "1758": ("🇱🇨 Saint Lucia (+1-758)", "LC"),
    "1784": ("🇻🇨 St. Vincent & Grenadines (+1-784)", "VC"), "1473": ("🇬🇩 Grenada (+1-473)", "GD"), "1869": ("🇰🇳 St. Kitts & Nevis (+1-869)", "KN"),
    "1767": ("🇩🇲 Dominica (+1-767)", "DM"), "1345": ("🇰🇾 Quần đảo Cayman (+1-345)", "KY"), "55": ("🇧🇷 Brazil (+55)", "BR"),
    "54": ("🇦🇷 Argentina (+54)", "AR"), "57": ("🇨🇴 Colombia (+57)", "CO"), "51": ("🇵🇪 Peru (+51)", "PE"),
    "58": ("🇻🇪 Venezuela (+58)", "VE"), "56": ("🇨🇱 Chile (+56)", "CL"), "593": ("🇪🇨 Ecuador (+593)", "EC"),
    "591": ("🇧🇴 Bolivia (+591)", "BO"), "595": ("🇵🇾 Paraguay (+595)", "PY"), "598": ("🇺🇾 Uruguay (+598)", "UY"),
    "592": ("🇬🇾 Guyana (+592)", "GY"), "597": ("🇸🇷 Suriname (+597)", "SR"), "44": ("🇬🇧 Vương Quốc Anh (+44)", "UK"),
    "33": ("🇫🇷 Pháp (+33)", "FR"), "49": ("🇩🇪 Đức (+49)", "DE"), "39": ("🇮🇹 Ý (+39)", "IT"),
    "34": ("🇪🇸 Tây Ban Nha (+34)", "ES"), "7": ("🇷🇺 Nga / Kazakhstan (+7)", "RU"), "380": ("🇺🇦 Ukraine (+380)", "UA"),
    "48": ("🇵🇱 Ba Lan (+48)", "PL"), "31": ("🇳🇱 Hà Lan (+31)", "NL"), "32": ("🇧🇪 Bỉ (+32)", "BE"),
    "41": ("🇨🇭 Thụy Sĩ (+41)", "CH"), "43": ("🇦🇹 Áo (+43)", "AT"), "46": ("🇸🇪 Thụy Điển (+46)", "SE"),
    "47": ("🇳🇴 Na Uy (+47)", "NO"), "45": ("🇩🇰 Đan Mạch (+45)", "DK"), "358": ("🇫🇮 Phần Lan (+358)", "FI"),
    "353": ("🇮🇪 Ai-len (+353)", "IE"), "351": ("🇵🇹 Bồ Đào Nha (+351)", "PT"), "30": ("🇬🇷 Hy Lạp (+30)", "GR"),
    "420": ("🇨🇿 Cộng Hòa Séc (+420)", "CZ"), "36": ("🇭🇺 Hungary (+36)", "HU"), "40": ("🇷🇴 Romania (+40)", "RO"),
    "359": ("🇧🇬 Bulgaria (+359)", "BG"), "385": ("🇭🇷 Croatia (+385)", "HR"), "386": ("🇸🇮 Slovenia (+386)", "SI"),
    "421": ("🇸🇰 Slovakia (+421)", "SK"), "370": ("🇱🇹 Lithuania (+370)", "LT"), "371": ("🇱🇻 Latvia (+371)", "LV"),
    "372": ("🇪🇪 Estonia (+372)", "EE"), "354": ("🇮🇸 Iceland (+354)", "IS"), "373": ("🇲🇩 Moldova (+373)", "MD"),
    "375": ("🇧🇾 Belarus (+375)", "BY"), "381": ("🇷🇸 Serbia (+381)", "RS"), "387": ("🇧🇦 Bosnia & Herzegovina (+387)", "BA"),
    "382": ("🇲🇪 Montenegro (+382)", "ME"), "355": ("🇦🇱 Albania (+355)", "AL"), "356": ("🇲🇹 Malta (+356)", "MT"),
    "352": ("🇱🇺 Luxembourg (+352)", "LU"), "377": ("🇲🇨 Monaco (+377)", "MC"), "378": ("🇸🇲 San Marino (+378)", "SM"),
    "379": ("🇻🇦 Vatican (+379)", "VA"), "423": ("🇱🇮 Liechtenstein (+423)", "LI"), "350": ("🇬🇮 Gibraltar (+350)", "GI"),
    "389": ("🇲🇰 Bắc Macedonia (+389)", "MK"), "298": ("🇫🇴 Quần đảo Faroe (+298)", "FO"), "299": ("🇬🇱 Greenland (+299)", "GL"),
    "84": ("🇻🇳 Việt Nam (+84)", "VN"), "86": ("🇨🇳 Trung Quốc (+86)", "CN"), "81": ("🇯🇵 Nhật Bản (+81)", "JP"),
    "82": ("🇰🇷 Hàn Quốc (+82)", "KR"), "91": ("🇮🇳 Ấn Độ (+91)", "IN"), "62": ("🇮🇩 Indonesia (+62)", "ID"),
    "92": ("🇵🇰 Pakistan (+92)", "PK"), "880": ("🇧🇩 Bangladesh (+880)", "BD"), "63": ("🇵🇭 Philippines (+63)", "PH"),
    "66": ("🇹🇭 Thái Lan (+66)", "TH"), "60": ("🇲🇾 Malaysia (+60)", "MY"), "65": ("🇸🇬 Singapore (+65)", "SG"),
    "95": ("🇲🇲 Myanmar (+95)", "MM"), "855": ("🇰🇭 Campuchia (+855)", "KH"), "856": ("🇱🇦 Lào (+856)", "LA"),
    "94": ("🇱🇰 Sri Lanka (+94)", "LK"), "977": ("🇳🇵 Nepal (+977)", "NP"), "93": ("🇦🇫 Afghanistan (+93)", "AF"),
    "98": ("🇮🇷 Iran (+98)", "IR"), "964": ("🇮🇶 Iraq (+964)", "IQ"), "90": ("🇹🇷 Thổ Nhĩ Kỳ (+90)", "TR"),
    "972": ("🇮🇱 Israel (+972)", "IL"), "962": ("🇯🇴 Jordan (+962)", "JO"), "961": ("🇱🇧 Lebanon (+961)", "LB"),
    "963": ("🇸🇾 Syria (+963)", "SY"), "965": ("🇰🇼 Kuwait (+965)", "KW"), "966": ("🇸🇦 Ả Rập Xê Út (+966)", "SA"),
    "971": ("🇦🇪 UAE (+971)", "AE"), "974": ("🇶🇦 Qatar (+974)", "QA"), "973": ("🇧🇭 Bahrain (+973)", "BH"),
    "968": ("🇴🇲 Oman (+968)", "OM"), "967": ("🇾🇪 Yemen (+967)", "YE"), "886": ("🇹🇼 Đài Loan (+886)", "TW"),
    "852": ("🇭🇰 Hồng Kong (+852)", "HK"), "853": ("🇲🇦 Ma Cao (+853)", "MO"), "976": ("🇲🇳 Mông Cổ (+976)", "MN"),
    "998": ("🇺🇿 Uzbekistan (+998)", "UZ"), "77": ("🇰🇿 Kazakhstan (+77)", "KZ"), "993": ("🇹🇲 Turkmenistan (+993)", "TM"),
    "992": ("🇹🇯 Tajikistan (+992)", "TJ"), "996": ("🇰🇬 Kyrgyzstan (+996)", "KG"), "994": ("🇦🇿 Azerbaijan (+994)", "AZ"),
    "374": ("🇦🇲 Armenia (+374)", "AM"), "995": ("🇬🇪 Georgia (+995)", "GE"), "673": ("🇧🇳 Brunei (+673)", "BN"),
    "670": ("🇹🇱 Đông Timor (+670)", "TL"), "960": ("🇲🇻 Maldives (+960)", "MV"), "970": ("🇵🇸 Palestine (+970)", "PS"),
    "975": ("🇧🇹 Bhutan (+975)", "BT"), "61": ("🇦🇺 Úc (+61)", "AU"), "64": ("🇳🇿 New Zealand (+64)", "NZ"),
    "675": ("🇵🇬 Papua New Guinea (+675)", "PG"), "679": ("🇫🇯 Fiji (+679)", "FJ"), "685": ("🇼🇸 Samoa (+685)", "WS"),
    "676": ("🇹🇴 Tonga (+676)", "TO"), "678": ("🇻🇺 Vanuatu (+678)", "VU"), "677": ("🇸🇧 Quần đảo Solomon (+677)", "SB"),
    "686": ("🇰🇮 Kiribati (+686)", "KI"), "691": ("🇫🇲 Micronesia (+691)", "FM"), "692": ("🇲🇭 Quần đảo Marshall (+692)", "MH"),
    "680": ("🇵🇼 Palau (+680)", "PW"), "688": ("🇹🇻 Tuvalu (+688)", "TV"), "674": ("🇳🇷 Nauru (+674)", "NR"),
    "682": ("🇨🇰 Quần đảo Cook (+682)", "CK"), "687": ("🇳🇨 New Caledonia (+687)", "NC"), "689": ("🇵🇫 French Polynesia (+689)", "PF"),
    "20": ("🇪🇬 Ai Cập (+20)", "EG"), "27": ("🇿🇦 Nam Phi (+27)", "ZA"), "234": ("🇳🇬 Nigeria (+234)", "NG"),
    "254": ("🇰🇪 Kenya (+254)", "KE"), "251": ("🇪🇹 Ethiopia (+251)", "ET"), "212": ("🇲🇦 Maroc (+212)", "MA"),
    "213": ("🇩🇿 Algeria (+213)", "DZ"), "216": ("🇹🇳 Tunisia (+216)", "TN"), "218": ("🇱🇾 Libya (+218)", "LY"),
    "233": ("🇬🇭 Ghana (+233)", "GH"), "225": ("🇨🇮 Bờ Biển Ngà (+225)", "CI"), "237": ("🇨🇲 Cameroon (+237)", "CM"),
    "255": ("🇹ℤ Tanzania (+255)", "TZ"), "256": ("🇺🇬 Uganda (+256)", "UG"), "250": ("🇷🇼 Rwanda (+250)", "RW"),
    "260": ("🇿🇲 Zambia (+260)", "ZM"), "263": ("🇿🇼 Zimbabwe (+263)", "ZW"),
    "258": ("🇲ℤ Mozambique (+258)", "MZ"), "244": ("🇦🇴 Angola (+244)", "AO"),
    "261": ("🇲🇬 Madagascar (+261)", "MG"), "249": ("🇸🇩 Sudan (+249)", "SD"),
    "221": ("🇸🇳 Senegal (+221)", "SN"), "223": ("🇲🇱 Mali (+223)", "ML"),
    "226": ("🇧🇫 Burkina Faso (+226)", "BF"), "227": ("🇳🇪 Niger (+227)", "NE"),
    "228": ("🇹🇬 Togo (+228)", "TG"), "229": ("🇧🇯 Benin (+229)", "BJ"),
    "235": ("🇹🇩 Chad (+235)", "TD"), "241": ("🇬🇦 Gabon (+241)", "GA"),
    "242": ("🇨🇬 Congo (+242)", "CG"), "243": ("🇨🇩 CHDC Congo (+243)", "CD"),
    "257": ("🇧🇮 Burundi (+257)", "BI"), "253": ("🇩🇯 Djibouti (+253)", "DJ"),
    "252": ("🇸🇴 Somalia (+252)", "SO"), "291": ("🇪🇷 Eritrea (+291)", "ER"),
    "232": ("🇸🇱 Sierra Leone (+232)", "SL"), "231": ("🇱🇷 Liberia (+231)", "LR"),
    "224": ("🇬🇳 Guinea (+224)", "GN"), "245": ("🇬🇼 Guinea-Bissau (+245)", "GW"),
    "220": ("🇬🇲 Gambia (+220)", "GM"), "230": ("🇲🇺 Mauritius (+230)", "MU"),
    "248": ("🇸🇨 Seychelles (+248)", "SC"), "269": ("🇰🇲 Comoros (+269)", "KM"),
    "268": ("🇸🇿 Eswatini (+268)", "SZ"), "266": ("🇱🇸 Lesotho (+266)", "LS"),
    "267": ("🇧🇼 Botswana (+267)", "BW"), "264": ("🇳🇦 Namibia (+264)", "NA"),
    "265": ("🇲🇼 Malawi (+265)", "MW"),
}

def get_country_info(phone):
    p = phone.replace("+", "").strip()
    for length in [4, 3, 2, 1]:
        if len(p) >= length:
            prefix = p[:length]
            if prefix in GLOBAL_COUNTRY_PREFIXES:
                return GLOBAL_COUNTRY_PREFIXES[prefix]
    fallback_code = p[:2] if len(p) >= 2 else p[:1]
    return f"🌐 Quốc tế Khác (+{fallback_code})", f"OTHER_{fallback_code}"

def load_text_batch():
    file_path = "numbers.txt"
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            batch_numbers = [line.strip() for line in lines if line.strip()]
            if batch_numbers:
                temp_cache = {}
                for num_str in batch_numbers:
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
                return True, len(batch_numbers)
        except Exception:
            pass
    return False, 0

load_text_batch()

def get_available_countries():
    valid_countries = {}
    for code, data in COUNTRY_CACHE.items():
        active_nums = [n for n in data["numbers"] if n not in DELETED_NUMBERS]
        if active_nums:
            valid_countries[code] = f"{data['name']} — [{len(active_nums)} Số]"
    return valid_countries

# ==========================================
# ⌨️ 6. GIAO DIỆN BÀN PHÍM MENU DƯỚI
# ==========================================
def get_main_menu_markup(is_admin=False):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("📞 Get Number"), KeyboardButton("🗑 Clear Prefix"))
    markup.add(KeyboardButton("🔍 Search with Prefix"))
    markup.add(KeyboardButton("💰 My Balance"), KeyboardButton("💸 Withdraw"))
    markup.add(KeyboardButton("👥 Refer"), KeyboardButton("📊 Stats"))
    markup.add(KeyboardButton("⚡ Live Traffic"), KeyboardButton("🏆 Top Users"))
    markup.add(KeyboardButton("❓ Help"))
    if is_admin:
        markup.add(KeyboardButton("👑 Admin Panel"))
    return markup

@bot.message_handler(commands=['start'])
def cmd_start(message):
    uid = message.from_user.id
    name = message.from_user.first_name or "Bạn"
    ok, err_msg = check_user_status(uid, name)
    if not ok:
        bot.send_message(uid, err_msg, parse_mode="HTML")
        return
    get_user(uid, name, message.from_user.username or "")
    text = f"👋 Chào mừng <b>{name}</b> đến với hệ thống <b>IVASMS OTP Global</b>!\n\n🌐 Tự động nhận diện 195+ quốc gia."
    bot.send_message(uid, text, parse_mode="HTML", reply_markup=get_main_menu_markup(uid == ADMIN_ID))

@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
    uid = message.from_user.id
    text = message.text
    chat_id = message.chat.id

    ok, err_msg = check_user_status(uid)
    if not ok:
        bot.send_message(chat_id, err_msg, parse_mode="HTML")
        return

    if uid in USER_WITHDRAW_STATE and USER_WITHDRAW_STATE[uid]:
        wallet_addr = text.strip()
        TON_REGEX = re.compile(r'^(EQ|UQ)[A-Za-z0-9\-_]{46}$')
        if not TON_REGEX.match(wallet_addr):
            bot.send_message(chat_id, "❌ <b>Địa chỉ ví không hợp lệ!</b> Ví TON phải bắt đầu bằng EQ hoặc UQ và có đúng 48 ký tự:", parse_mode="HTML")
            return
        USER_PENDING_WALLET[uid] = wallet_addr
        USER_WITHDRAW_STATE[uid] = False
        user_info = get_user(uid)
        current_bal = user_info.get("balance", 0.0)
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(InlineKeyboardButton("✅ Xác Nhận", callback_data="confirm_withdraw_action"), InlineKeyboardButton("❌ Hủy", callback_data="cancel_withdraw"))
        bot.send_message(chat_id, f"🔍 <b>XÁC NHẬN RÚT</b>\n💵 Số tiền: <b>${current_bal:.4f} USDT</b>\n📤 Ví: <code>{wallet_addr}</code>", parse_mode="HTML", reply_markup=markup)
        return

    if text in ["📞 Get Number", "🔍 Search with Prefix"]:
        countries = get_available_countries()
        if not countries:
            bot.send_message(chat_id, "❌ Kho số hiện tại đang trống!")
            return
        markup = InlineKeyboardMarkup(row_width=1)
        for code, label in countries.items():
            markup.add(InlineKeyboardButton(f"🌍 {label}", callback_data=f"country_{code}_0"))
        bot.send_message(chat_id, "🌍 <b>CHỌN QUỐC GIA (195+):</b>", parse_mode="HTML", reply_markup=markup)

    elif text == "💰 My Balance":
        user_info = get_user(uid)
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(InlineKeyboardButton("💸 Withdraw (USDT TON)", callback_data="request_withdraw"), InlineKeyboardButton("📜 Lịch sử rút", callback_data="withdraw_history"))
        bot.send_mess
