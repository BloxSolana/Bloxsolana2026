import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import requests
from bs4 import BeautifulSoup
import re
import datetime
import os
import threading
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
# 🌐 2. FLASK WEB SERVER (GIỮ BOT ONLINE 24/7)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot IVASMS OTP Global Webhook Server đang chạy 24/7 trên Render!"

# ==========================================
# 🚀 3. ENDPOINT NHẬN SMS: BẮT TRỌN MỌI OTP & ĐẨY LÊN GROUP
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
            valid_nums = []
            for n in all_nums:
                if n.startswith('2026') or n.startswith('2025'):
                    continue
                if f"${n}" in raw_text or f".{n}" in raw_text:
                    continue
                valid_nums.append(n)
            if valid_nums:
                otp_display = valid_nums[-1]

        phones = re.findall(r'\+?\d{8,15}', raw_text)
        masked_phone = data.get("phone", "")
        if not masked_phone and phones:
            p = phones[0]
            clean_p = re.sub(r'\D', '', p)
            if len(clean_p) >= 8:
                prefix_sign = "+" if p.startswith("+") else ""
                masked_phone = prefix_sign + clean_p[:4] + "****" + clean_p[-2:]
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

def run_web():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

try:
    bot.remove_webhook()
except Exception as e:
    print(f"Xử lý Webhook: {e}")

# ==========================================
# ⚙️ 4. QUẢN LÝ DỮ LIỆU & KHO SỐ
# ==========================================
session = requests.Session()
headers = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest'
}

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

DEFAULT_SETTINGS = {
    "min_withdraw": 5.0,        
    "max_withdraw": 100.0,
    "otp_reward": 0.009,        
    "refer_bonus": 0.01,
}

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        save_json_db(SETTINGS_FILE, DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS
    return load_json_db(SETTINGS_FILE)

def save_settings(s):
    save_json_db(SETTINGS_FILE, s)

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

def save_deleted_numbers(deleted_set):
    try:
        with open(DELETED_NUMBERS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(deleted_set), f, ensure_ascii=False, indent=4)
    except Exception:
        pass

DELETED_NUMBERS = load_deleted_numbers()

def remove_number_from_file(target_phone):
    DELETED_NUMBERS.add(target_phone)
    save_deleted_numbers(DELETED_NUMBERS)
    file_path = "numbers.txt"
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            new_lines = []
            target_clean = target_phone.replace("+", "").strip()
            for line in lines:
                line_clean = re.sub(r'\D', '', line)
                if line_clean != target_clean and line_clean:
                    new_lines.append(line)
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        except Exception as e:
            print(f"Lỗi khi xóa số khỏi file: {e}")

def get_user(uid, name="", username=""):
    users = load_json_db(USERS_FILE)
    uid_str = str(uid)
    if uid_str not in users:
        users[uid_str] = {
            "id": uid,
            "name": name or "Ẩn danh",
            "username": username or "Không có",
            "balance": 0.0,
            "referrals": 0,
            "referral_earnings": 0.0,
            "referred_by": None,
            "joined_at": datetime.datetime.now().strftime('%H:%M:%S - %d/%m/%Y')
        }
        save_json_db(USERS_FILE, users)
    return users[uid_str]

def mask_phone_number(phone):
    p = phone.strip()
    if len(p) > 6:
        return p[:4] + "****" + p[-2:]
    return p

def check_user_status(user_id, name=""):
    if user_id == ADMIN_ID:
        return True, ""
    spam_data = load_json_db(SPAM_TRACKER_FILE)
    uid = str(user_id)
    now = time.time()
    if uid in spam_data:
        info = spam_data[uid]
        ban_until = info.get("ban_until", 0)
        if ban_until == 0:
            return False, "⛔ <b>Tài khoản của bạn đã bị KHÓA VĨNH VIỄN</b>."
        if now < ban_until:
            return False, "⏳ <b>Bạn đang bị tạm khóa do thao tác quá nhanh.</b>"
    return True, ""

# ==========================================
# 🌍 6. BỘ TỪ ĐIỂN FULL 195+ QUỐC GIA CHUẨN XÁC
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

def clean_expired_sessions():
    now = time.time()
    for phone, create_time in list(PHONE_CREATION_TIME.items()):
        if now - create_time > 900:
            remove_number_from_file(phone)
            PHONE_CREATION_TIME.pop(phone, None)
            OTP_ACTIVE_SESSIONS.pop(phone, None)

def load_text_batch():
    clean_expired_sessions()
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
                            if formatted not in PHONE_CREATION_TIME:
                                PHONE_CREATION_TIME[formatted] = time.time()
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

def is_phone_busy(phone):
    if phone in OTP_ACTIVE_SESSIONS:
        return True
    for info in USER_ACTIVE_PHONES.values():
        if info.get("phone") == phone:
            return True
    return False

def get_numbers_by_category(category_code, page=0, limit=6):
    clean_expired_sessions()
    if category_code in COUNTRY_CACHE:
        all_nums = [n for n in COUNTRY_CACHE[category_code]["numbers"] if not is_phone_busy(n) and n not in DELETED_NUMBERS]
        start = page * limit
        end = start + limit
        return all_nums[start:end], len(all_nums)
    return [], 0

def get_available_countries():
    clean_expired_sessions()
    valid_countries = {}
    for code, data in COUNTRY_CACHE.items():
        active_nums = [n for n in data["numbers"] if not is_phone_busy(n) and n not in DELETED_NUMBERS]
        if active_nums:
            valid_countries[code] = f"{data['name']} — [{len(active_nums)} Số]"
    return valid_countries

# ==========================================
# ⌨️ 7. HỆ THỐNG BÀN PHÍM MENU DƯỚI (Y HỆT ẢNH MẪU)
# ==========================================
def get_main_menu_markup(is_admin=False):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = KeyboardButton("📞 Get Number")
    btn2 = KeyboardButton("🗑 Clear Prefix")
    btn3 = KeyboardButton("🔍 Search with Prefix")
    btn4 = KeyboardButton("💰 My Balance")
    btn5 = KeyboardButton("💸 Withdraw")
    btn6 = KeyboardButton("👥 Refer")
    btn7 = KeyboardButton("📊 Stats")
    btn8 = KeyboardButton("⚡ Live Traffic")
    btn9 = KeyboardButton("🏆 Top Users")
    btn10 = Keyóa vĩnh viễn do spam liên tục!"
            
        spam_data[uid] = {
            "name": name, "count": count, "ban_until": ban_until,
            "banned_at": datetime.datetime.now().strftime('%H:%M:%S - %d/%m/%Y')
        }
        save_json_db(SPAM_TRACKER_FILE, spam_data)
        return False, msg

    USER_LAST_ACTION[user_id] = now
    return True, ""

def unban_user_manual(user_id):
    spam_data = load_json_db(SPAM_TRACKER_FILE)
    uid = str(user_id)
    if uid in spam_data:
        del spam_data[uid]
        save_json_db(SPAM_TRACKER_FILE, spam_data)
        return True
    return False

# ==========================================
# 🌍 6. BỘ TỪ ĐIỂN MỞ RỘNG FULL 195+ QUỐC GIA
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

def clean_expired_sessions():
    try:
        now = time.time()
        for phone, create_time in list(PHONE_CREATION_TIME.items()):
            if now - create_time > 900:
                remove_number_from_file(phone)
                PHONE_CREATION_TIME.pop(phone, None)
                OTP_ACTIVE_SESSIONS.pop(phone, None)
                for cid, info in list(USER_ACTIVE_PHONES.items()):
                    if info.get("phone") == phone:
                        USER_ACTIVE_PHONES.pop(cid, None)
                        try:
                            bot.edit_message_text(
                                f"⏰ <b>SỐ ĐIỆN THOẠI <code>{phone}</code> ĐÃ HẾT HẠN!</b>\nSố này đã quá thời hạn 15 phút tồn tại.",
                                cid, info.get("msg_id"), parse_mode="HTML"
                            )
                        except Exception:
                            pass
    except Exception as e:
        print(f"Lỗi clean sessions: {e}")

def load_text_batch():
    clean_expired_sessions()
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
                            if formatted not in PHONE_CREATION_TIME:
                                PHONE_CREATION_TIME[formatted] = time.time()
                            name, code = get_country_info(formatted)
                            if code not in temp_cache:
                                temp_cache[code] = {"name": name, "numbers": []}
                            if formatted not in temp_cache[code]["numbers"]:
                                temp_cache[code]["numbers"].append(formatted)
                global COUNTRY_CACHE
                COUNTRY_CACHE = temp_cache
                return True, len(batch_numbers)
        except Exception as e:
            print(f"Lỗi load numbers.txt: {e}")
    return False, 0

load_text_batch()

def is_phone_busy(phone):
    if phone in OTP_ACTIVE_SESSIONS:
        return True
    for info in USER_ACTIVE_PHONES.values():
        if info.get("phone") == phone:
            return True
    return False

def get_numbers_by_category(category_code, page=0, limit=6):
    clean_expired_sessions()
    if category_code in COUNTRY_CACHE:
        all_nums = [n for n in COUNTRY_CACHE[category_code]["numbers"] if not is_phone_busy(n) and n not in DELETED_NUMBERS]
        start = page * limit
        end = start + limit
        return all_nums[start:end], len(all_nums)
    return [], 0

def get_available_countries():
    clean_expired_sessions()
    valid_countries = {}
    for code, data in COUNTRY_CACHE.items():
        active_nums = [n for n in data["numbers"] if not is_phone_busy(n) and n not in DELETED_NUMBERS]
        if active_nums:
            valid_countries[code] = f"{data['name']} — [{len(active_nums)} Số]"
    return valid_countries

# ==========================================
# 🤖 7. BOT HANDLERS & GIAO DIỆN NÚT NGANG (Y HỆT ẢNH MẪU 2 & 3)[cite: 7, 8]
# ==========================================
@bot.message_handler(commands=['start'])
def cmd_start(message):
    uid = message.from_user.id
    name = message.from_user.first_name or "Bạn"
    username = message.from_user.username or ""
    
    ok, err_msg = check_user_status(uid, name)
    if not ok:
        bot.send_message(uid, err_msg, parse_mode="HTML")
        return
        
    get_user(uid, name, username)
    
    text = (
        f"👋 Chào mừng <b>{name}</b> đến với hệ thống <b>IVASMS OTP Global</b>!\n\n"
        "🌐 Hỗ trợ nhận số & OTP tự động 195+ quốc gia.\n"
        "💰 Kiếm <b>0.009$</b> thưởng tự động khi nhận mã OTP thành công!"
    )
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🟢 📲 Get Number", callback_data="open_countries"),
        InlineKeyboardButton("🔴 🗑 Clear Prefix", callback_data="clear_prefix"),
        InlineKeyboardButton("🟢 🔍 Search with Prefix", callback_data="open_countries"),
        InlineKeyboardButton("🟢 💰 My Balance", callback_data="my_wallet"),
        InlineKeyboardButton("🔴 💸 Withdraw", callback_data="request_withdraw"),
        InlineKeyboardButton("🔵 👥 Refer", callback_data="refer_earn"),
        InlineKeyboardButton("🔵 📊 Stats", callback_data="my_stats"),
        InlineKeyboardButton("🔵 ⚡ Live Traffic", url=GROUP_OTP_LINK),
        InlineKeyboardButton("🔵 🏆 Top Users", callback_data="top_users_board"),
        InlineKeyboardButton("🔴 ❓ Help", callback_data="help_menu")
    )
    if uid == ADMIN_ID:
        markup.add(InlineKeyboardButton("👑 Bảng Điều Khiển Admin Tối Cao", callback_data="admin_panel"))
        
    bot.send_message(uid, text, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    try:
        uid = call.from_user.id
        data = call.data
        chat_id = call.message.chat.id
        msg_id = call.message.message_id
        
        if data == "open_countries":
            if uid in USER_ACTIVE_PHONES:
                curr_p = USER_ACTIVE_PHONES[uid].get("phone")
                bot.answer_callback_query(call.id, f"Bạn đang giữ số {curr_p}. Vui lòng hoàn thành hoặc Hủy số cũ trước!", show_alert=True)
                return

            countries = get_available_countries()
            if not countries:
                bot.answer_callback_query(call.id, "Kho số hiện tại đang trống!", show_alert=True)
                return
                
            markup = InlineKeyboardMarkup(row_width=1)
            for code, label in countries.items():
                markup.add(InlineKeyboardButton(f"🌍 {label}", callback_data=f"country_{code}_0"))
            markup.add(InlineKeyboardButton("🔙 Quay lại Menu Chính", callback_data="back_home"))
            bot.edit_message_text("🌍 <b>CHỌN QUỐC GIA CẦN LẤY SỐ:</b>", chat_id, msg_id, parse_mode="HTML", reply_markup=markup)

        elif data.startswith("country_"):
            parts = data.split("_")
            code = parts[1]
            page = int(parts[2])
            
            numbers, total = get_numbers_by_category(code, page)
            if not numbers:
                bot.answer_callback_query(call.id, "Hết số trong danh mục này!", show_alert=True)
                return
                
            markup = InlineKeyboardMarkup(row_width=1)
            for num in numbers:
                masked = mask_phone_number(num)
                markup.add(InlineKeyboardButton(f"📞 Lấy số: {masked}", callback_data=f"getnum_{code}_{page}_{num}"))
                
            nav_buttons = []
            if page > 0:
                nav_buttons.append(InlineKeyboardButton("⬅️ Trước", callback_data=f"country_{code}_{page-1}"))
            if (page + 1) * 6 < total:
                nav_buttons.append(InlineKeyboardButton("Sau ➡️", callback_data=f"country_{code}_{page+1}"))
            if nav_buttons:
                markup.row(*nav_buttons)
                
            markup.add(InlineKeyboardButton("🔄 Chọn Quốc Gia Khác", callback_data="open_countries"))
            bot.edit_message_text(f"📋 <b>Danh sách số sẵn sàng ({code}):</b>", chat_id, msg_id, parse_mode="HTML", reply_markup=markup)

        elif data.startswith("getnum_"):
            parts = data.split("_")
            code = parts[1]
            phone = parts[3]

            if is_phone_busy(phone):
                bot.answer_callback_query(call.id, "❌ Số này vừa có người khác lấy mất rồi!", show_alert=True)
                return
            
            if phone not in PHONE_CREATION_TIME:
                PHONE_CREATION_TIME[phone] = time.time()

            elapsed = time.time() - PHONE_CREATION_TIME[phone]
            remaining_time = 900 - elapsed
            if remaining_time <= 0:
                remove_number_from_file(phone)
                bot.answer_callback_query(call.id, "⚠️ Số này đã hết hạn 15 phút!", show_alert=True)
                return

            USER_ACTIVE_PHONES[chat_id] = {
                "phone": phone,
                "expire": time.time() + remaining_time,
                "code": code,
                "msg_id": msg_id
            }
            
            text = (
                "✅ <b>ĐÃ CẤP SỐ THÀNH CÔNG!</b>\n"
                "-----------------------------------\n"
                f"📞 <b>Số điện thoại:</b> <code>{phone}</code>\n"
                "💬 <b>Trạng thái:</b> Đang chờ mã OTP...\n"
                f"⏳ <i>Số này còn lại khoảng {int(remaining_time/60)} phút.</i>"
            )
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                InlineKeyboardButton("🔄 Đổi số mới", callback_data=f"nextnum_{code}_{phone}"),
                InlineKeyboardButton("❌ Hủy số", callback_data=f"cancelnum_{phone}")
            )
            bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)

        elif data.startswith("nextnum_"):
            parts = data.split("_")
            code = parts[1]
            old_phone = parts[2]

            USER_ACTIVE_PHONES.pop(chat_id, None)
            available_nums, _ = get_numbers_by_category(code, page=0, limit=50)
            available_nums = [n for n in available_nums if n != old_phone]

            if not available_nums:
                bot.answer_callback_query(call.id, "⚠️ Đã hết số khác trong danh mục này rồi!", show_alert=True)
                call.data = "open_countries"
                handle_callbacks(call)
                return

            new_phone = random.choice(available_nums)
            PHONE_CREATION_TIME[new_phone] = time.time()
            USER_ACTIVE_PHONES[chat_id] = {
                "phone": new_phone,
                "expire": time.time() + 900,
                "code": code,
                "msg_id": msg_id
            }

            text = (
                "✅ <b>ĐÃ ĐỔI SỐ MỚI!</b>\n"
                "-----------------------------------\n"
                f"📞 <b>Số mới:</b> <code>{new_phone}</code>\n"
                "💬 <b>Trạng thái:</b> Đang chờ mã OTP..."
            )
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                InlineKeyboardButton("🔄 Đổi số mới", callback_data=f"nextnum_{code}_{new_phone}"),
                InlineKeyboardButton("❌ Hủy số", callback_data=f"cancelnum_{new_phone}")
            )
            bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)

        elif data.startswith("cancelnum_"):
            phone = data.replace("cancelnum_", "")
            USER_ACTIVE_PHONES.pop(chat_id, None)
            bot.answer_callback_query(call.id, "Đã hủy số thành công.", show_alert=False)
            
            text = "👋 Bạn đã hủy số thành công. Chào mừng quay lại menu chính!"
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                InlineKeyboardButton("🟢 📲 Get Number", callback_data="open_countries"),
                InlineKeyboardButton("🟢 💰 My Balance", callback_data="my_wallet")
            )
            bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)

        elif data == "clear_prefix":
            bot.answer_callback_query(call.id, "Đã xóa bộ lọc prefix thành công!", show_alert=False)

        elif data == "help_menu":
            bot.answer_callback_query(call.id, "Hệ thống tự động nhận diện OTP & cấp số 195+ quốc gia.", show_alert=True)

        elif data == "my_wallet":
            user_info = get_user(uid, call.from_user.first_name, call.from_user.username or "")
            settings = load_settings()
            balance = user_info.get("balance", 0.0)
            min_w = settings.get("min_withdraw", 5.0)
            
            text = (
                "💰 <b>VÍ TÀI KHOẢN & THÔNG TIN CÁ NHÂN</b>\n"
                "-----------------------------------\n"
                f"👤 <b>Họ tên:</b> {user_info.get('name')}\n"
                f"🆔 <b>ID:</b> <code>{uid}</code>\n"
                f"💵 <b>Số dư:</b> <code>${balance:.4f}</code>\n"
                f"📉 <b>Rút tối thiểu:</b> <code>${min_w:.1f}</code>\n"
            )
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                InlineKeyboardButton("💸 Withdraw (USDT TON)", callback_data="request_withdraw"),
                InlineKeyboardButton("📜 Lịch sử rút", callback_data="withdraw_history"),
                InlineKeyboardButton("🔙 Quay lại Menu", callback_data="back_home")
            )
            bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)

        elif data == "request_withdraw":
            user_info = get_user(uid)
            settings = load_settings()
            balance = user_info.get("balance", 0.0)
            min_w = settings.get("min_withdraw", 5.0)
            
            if balance < min_w:
                bot.answer_callback_query(call.id, f"Số dư chưa đủ! Tối thiểu cần ${min_w:.1f}", show_alert=True)
            else:
                USER_WITHDRAW_STATE[uid] = True
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton("❌ Hủy bỏ", callback_data="cancel_withdraw"))
                bot.edit_message_text(
                    "📥 <b>RÚT TIỀN TỰ ĐỘNG (0% PHÍ)</b>\n\n"
                    "Vui lòng gửi địa chỉ ví <b>USDT mạng TON</b> của bạn vào ô chat:\n"
                    "<i>(Ví chuẩn TON bắt đầu bằng EQ hoặc UQ, đúng 48 ký tự).</i>",
                    chat_id, msg_id, parse_mode="HTML", reply_markup=markup
                )

        elif data == "cancel_withdraw":
            USER_WITHDRAW_STATE.pop(uid, None)
            USER_PENDING_WALLET.pop(uid, None)
            bot.answer_callback_query(call.id, "Đã hủy.", show_alert=False)
            call.data = "my_wallet"
            handle_callbacks(call)

        elif data == "confirm_withdraw_action":
            wallet_addr = USER_PENDING_WALLET.pop(uid, None)
            USER_WITHDRAW_STATE.pop(uid, None)
            
            if not wallet_addr:
                bot.answer_callback_query(call.id, "Phiên hết hạn!", show_alert=True)
                return
                
            settings = load_settings()
            users_db = load_json_db(USERS_FILE)
            uid_str = str(uid)
            min_w = settings.get("min_withdraw", 5.0)
            
            if uid_str in users_db:
                with_amount = users_db[uid_str]["balance"]
                if with_amount < min_w:
                    bot.answer_callback_query(call.id, "Số dư không đủ!", show_alert=True)
                    return
                    
                users_db[uid_str]["balance"] = 0.0
                save_json_db(USERS_FILE, users_db)
                
                history_db = load_json_db(WITHDRAW_HISTORY_FILE)
                if uid_str not in history_db:
                    history_db[uid_str] = []
                    
                current_time_str = datetime.datetime.now().strftime('%H:%M:%S - %d/%m/%Y')
                history_db[uid_str].append({
                    "amount": with_amount, "wallet": wallet_addr,
                    "status": "⏳ Đang chờ duyệt", "time": current_time_str
                })
                save_json_db(WITHDRAW_HISTORY_FILE, history_db)
                
                user_info = get_user(uid)
                admin_text = (
                    "💸 <b>YÊU CẦU RÚT TIỀN MỚI</b>\n"
                    f"👤 User: {user_info.get('name')} (<code>{uid}</code>)\n"
                    f"💵 Số tiền: <b>${with_amount:.4f} USDT</b>\n"
                    f"📤 Ví TON: <code>{wallet_addr}</code>"
                )
                markup_admin = InlineKeyboardMarkup()
                markup_admin.add(InlineKeyboardButton("💸 Duyệt lệnh", callback_data="admin_view_withdraws"))
                try:
                    bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML", reply_markup=markup_admin)
                except Exception:
                    pass
                    
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton("📜 Xem lịch sử", callback_data="withdraw_history"))
                bot.edit_message_text("✅ <b>Đã gửi yêu cầu rút tiền thành công cho Admin duyệt!</b>", chat_id, msg_id, parse_mode="HTML", reply_markup=markup)

        elif data == "withdraw_history":
            history_db = load_json_db(WITHDRAW_HISTORY_FILE)
            user_histories = history_db.get(str(uid), [])
            text = "📜 <b>LỊCH SỬ RÚT TIỀN:</b>\n\n"
            if not user_histories:
                text += "<i>Chưa có lịch sử.</i>"
            else:
                for idx, item in enumerate(user_histories[::-1], 1):
                    text += f"#{idx}. <b>${item.get('amount'):.4f}</b> — {item.get('status')}\n"
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔙 Quay lại Ví", callback_data="my_wallet"))
            bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)

        elif data == "refer_earn":
            bot_info = bot.get_me()
            ref_link = f"https://t.me/{bot_info.username}?start={uid}"
            user_info = get_user(uid)
            text = (
                f"👥 <b>MỜI BẠN BÈ NHẬN THƯỞNG</b>\n\n"
                f"🔗 Link giới thiệu:\n<code>{ref_link}</code>\n\n"
                f"📊 Đã mời: <b>{user_info.get('referrals', 0)}</b> người"
            )
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔙 Quay lại", callback_data="back_home"))
            bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)

        elif data == "my_stats":
            stats = load_json_db(STATS_FILE)
            my_count = stats.get(str(uid), {}).get("count", 0)
            text = f"📊 <b>Thống kê cá nhân:</b>\n🔑 Tổng OTP nhận thành công: <b>{my_count}</b> mã"
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔙 Quay lại", callback_data="back_home"))
            bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)

        elif data == "top_users_board":
            users_db = load_json_db(USERS_FILE)
            text = "🏆 <b>BẢNG XẾP HẠNG TOP USERS (KIẾM OTP):</b>\n\n"
            if not users_db:
                text += "<i>Chưa có dữ liệu.</i>"
            else:
                sorted_users = sorted(users_db.values(), key=lambda x: x.get('balance', 0.0), reverse=True)
                for idx, u_info in enumerate(sorted_users[:10], 1):
                    text += f"<b>#{idx}</b> | 👤 {u_info.get('name')} — <code>${u_info.get('balance', 0.0):.4f}</code>\n"
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔙 Quay lại", callback_data="back_home"))
            bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)

        elif data == "back_home":
            USER_WITHDRAW_STATE.pop(uid, None)
            USER_PENDING_WALLET.pop(uid, None)
            text = "👋 Chào mừng bạn quay lại menu chính!"
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                InlineKeyboardButton("🟢 📲 Get Number", callback_data="open_countries"),
                InlineKeyboardButton("🔴 🗑 Clear Prefix", callback_data="clear_prefix"),
                InlineKeyboardButton("🟢 🔍 Search with Prefix", callback_data="open_countries"),
                InlineKeyboardButton("🟢 💰 My Balance", callback_data="my_wallet"),
                InlineKeyboardButton("🔴 💸 Withdraw", callback_data="request_withdraw"),
                InlineKeyboardButton("🔵 👥 Refer", callback_data="refer_earn"),
                InlineKeyboardButton("🔵 📊 Stats", callback_data="my_stats"),
                InlineKeyboardButton("🔵 ⚡ Live Traffic", url=GROUP_OTP_LINK),
                InlineKeyboardButton("🔵 🏆 Top Users", callback_data="top_users_board"),
                InlineKeyboardButton("🔴 ❓ Help", callback_data="help_menu")
            )
            if uid == ADMIN_ID:
                markup.add(InlineKeyboardButton("👑 Bảng Điều Khiển Admin Tối Cao", callback_data="admin_panel"))
            bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)

        # ==========================================
        # 👑 ADMIN PANEL QUẢN LÝ
        # ==========================================
        elif data == "admin_panel" and uid == ADMIN_ID:
            users = load_json_db(USERS_FILE)
            text = (
                "👑 <b>BẢNG ĐIỀU KHIỂN ADMIN TỐI CAO</b>\n"
                "-----------------------------------\n"
                f"👥 Tổng user đăng ký: <b>{len(users)}</b>\n"
                f"📊 Tổng stock hiện có: <b>{sum(len(d['numbers']) for d in COUNTRY_CACHE.values())}</b>"
            )
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                InlineKeyboardButton("💸 Duyệt lệnh rút tiền", callback_data="admin_view_withdraws"),
                InlineKeyboardButton("👥 Xem danh sách user đăng ký", callback_data="admin_view_users"),
                InlineKeyboardButton("🏆 Top số dư user (Chống gian lận)", callback_data="admin_top_balances"),
                InlineKeyboardButton("🔄 Sync batch số mới", callback_data="admin_reload"),
                InlineKeyboardButton("🛡 Quản lý Spam & Ban", callback_data="admin_users"),
                InlineKeyboardButton("🔙 Về Menu chính", callback_data="back_home")
            )
            bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)

        elif data == "admin_view_users" and uid == ADMIN_ID:
            users_db = load_json_db(USERS_FILE)
            text = "👥 <b>DANH SÁCH USER ĐĂNG KÝ (10 User mới nhất):</b>\n\n"
            if not users_db:
                text += "<i>Chưa có người dùng nào.</i>"
            else:
                for u_id, u_info in list(users_db.items())[-10:]:
                    text += (
                        f"👤 <b>Tên:</b> {u_info.get('name')}\n"
                        f"🆔 ID: <code>{u_info.get('id')}</code> | @{u_info.get('username')}\n"
                        f"💵 Số dư: <code>${u_info.get('balance', 0.0):.4f}</code>\n"
                        f"📅 Đăng ký: {u_info.get('joined_at')}\n"
                        "-----------------------------------\n"
                    )
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔙 Quay lại Admin Panel", callback_data="admin_panel"))
            bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)

        elif data == "admin_top_balances" and uid == ADMIN_ID:
            users_db = load_json_db(USERS_FILE)
            text = "🏆 <b>BẢNG TOP SỐ DƯ USER (KIỂM TRA GIAN LẬN):</b>\n\n"
            if not users_db:
                text += "<i>Chưa có dữ liệu.</i>"
            else:
                sorted_users = sorted(users_db.values(), key=lambda x: x.get('balance', 0.0), reverse=True)
                for idx, u_info in enumerate(sorted_users[:10], 1):
                    text += (
                        f"<b>#{idx}</b> | 👤 <b>{u_info.get('name')}</b> (ID: <code>{u_info.get('id')}</code>)\n"
                        f"💵 <b>Số dư:</b> <code>${u_info.get('balance', 0.0):.4f}</code>\n"
                        "-----------------------------------\n"
                    )
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔙 Quay lại Admin Panel", callback_data="admin_panel"))
            bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)

        elif data == "admin_view_withdraws" and uid == ADMIN_ID:
            history_db = load_json_db(WITHDRAW_HISTORY_FILE)
            pending = [(u, i, it) for u, items in history_db.items() for i, it in enumerate(items) if "⏳" in it.get("status", "")]
            if not pending:
                bot.answer_callback_query(call.id, "Không có lệnh rút nào đang chờ!", show_alert=True)
                return
            markup = InlineKeyboardMarkup(row_width=1)
            text = "💸 <b>LỆNH RÚT ĐANG CHỜ DUYỆT:</b>\n\n"
            for u_id, idx, it in pending[:5]:
                text += f"• ID {u_id} | ${it.get('amount'):.4f}\n"
                markup.add(InlineKeyboardButton(f"✅ Duyệt ID {u_id} (${it.get('amount')})", callback_data=f"done_w_{u_id}_{idx}"))
            markup.add(InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel"))
            bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)

        elif data.startswith("done_w_") and uid == ADMIN_ID:
            parts = data.split("_")
            target_uid, item_idx = parts[2], int(parts[3])
            history_db = load_json_db(WITHDRAW_HISTORY_FILE)
            if target_uid in history_db and len(history_db[target_uid]) > item_idx:
                history_db[target_uid][item_idx]["status"] = "✅ Đã thanh toán thành công"
                save_json_db(WITHDRAW_HISTORY_FILE, history_db)
                try:
                    bot.send_message(int(target_uid), "🎉 <b>Yêu cầu rút tiền của bạn đã được Admin duyệt và chuyển USDT thành công!</b>", parse_mode="HTML")
                except Exception:
                    pass
                bot.answer_callback_query(call.id, "Đã duyệt!", show_alert=True)
                call.data = "admin_view_withdraws"
                handle_callbacks(call)

        elif data == "admin_reload" and uid == ADMIN_ID:
            success, count = load_text_batch()
            bot.answer_callback_query(call.id, f"Đã load thành công {count} số!", show_alert=True)

        elif data == "admin_users" and uid == ADMIN_ID:
            spam_data = load_json_db(SPAM_TRACKER_FILE)
            markup = InlineKeyboardMarkup(row_width=1)
            text = "🛡 <b>Danh sách user bị phạt:</b>\n\n"
            if not spam_data:
                text += "<i>Không có user nào bị phạt.</i>"
            else:
                for s_id, info in spam_data.items():
                    text += f"• ID: {s_id} ({info.get('name')})\n"
                    markup.add(InlineKeyboardButton(f"🔓 Gỡ khóa ID {s_id}", callback_data=f"unban_{s_id}"))
            markup.add(InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel"))
            bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)

        elif data.startswith("unban_") and uid == ADMIN_ID:
            target_uid = data.replace("unban_", "")
            if unban_user_manual(target_uid):
                bot.answer_callback_query(call.id, "Đã gỡ khóa!", show_alert=True)
                call.data = "admin_users"
                handle_callbacks(call)
    except Exception as e:
        print(f"Lỗi callback: {e}")

@bot.message_handler(func=lambda message: USER_WITHDRAW_STATE.get(message.from_user.id, False))
def handle_text_inputs(message):
    uid = message.from_user.id
    wallet_addr = message.text.strip()
    
    if wallet_addr.startswith('/'):
        USER_WITHDRAW_STATE.pop(uid, None)
        return

    TON_REGEX = re.compile(r'^(EQ|UQ)[A-Za-z0-9\-_]{46}$')
    if not TON_REGEX.match(wallet_addr):
        bot.send_message(uid, "❌ <b>Địa chỉ ví không hợp lệ!</b> Ví TON phải bắt đầu bằng EQ hoặc UQ và có đúng 48 ký tự. Gửi lại chính xác:", parse_mode="HTML")
        return
        
    USER_PENDING_WALLET[uid] = wallet_addr
    USER_WITHDRAW_STATE.pop(uid, None)
    
    user_info = get_user(uid)
    current_bal = user_info.get("balance", 0.0)
    
    confirm_text = (
        "🔍 <b>XÁC NHẬN RÚT TIỀN</b>\n"
        f"💵 Số tiền: <b>${current_bal:.4f} USDT</b>\n"
        f"📤 Ví nhận: <code>{wallet_addr}</code>"
    )
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✅ Xác Nhận", callback_data="confirm_withdraw_action"),
        InlineKeyboardButton("❌ Hủy", callback_data="cancel_withdraw")
    )
    bot.send_message(uid, confirm_text, parse_mode="HTML", reply_markup=markup)

if __name__ == "__main__":
    t_web = threading.Thread(target=run_web, daemon=True)
    t_web.start()
    
    print("🤖 Bot Telegram Webhook Server đang chạy mượt mà...")
    
    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"⚠️ Mất kết nối Telegram: {e}")
            print("⏳ Kết nối lại sau 5 giây...")
            time.sleep(5)
