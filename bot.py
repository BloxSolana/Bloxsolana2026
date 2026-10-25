import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
from bs4 import BeautifulSoup
import re
import datetime
import os
import threading
import json
import time
from flask import Flask

# ==========================================
# 👑 1. CẤU HÌNH ADMIN TỐI CAO & TELEGRAM BOT
# ==========================================
ADMIN_ID = 6726769296
TOKEN = "8622066775:AAG08FcNdjAapQcc1e5lCJBEsUMH-kzhYHM"
GROUP_CHAT_ID = "-1004341368656"
GROUP_OTP_LINK = "https://t.me/LIVEOTPIVAS"

bot = telebot.TeleBot(TOKEN)

# ==========================================
# 🌐 2. FLASK WEB SERVER (GIỮ BOT ONLINE 24/7)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot IVASMS OTP Global & Ultimate Security đang chạy 24/7 trên Render!"

def run_web():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# 🧹 Tắt Webhook cũ & xả kẹt hàng chờ Telegram
try:
    bot.remove_webhook()
except Exception as e:
    print(f"Xử lý Webhook: {e}")

# ==========================================
# ⚙️ 3. QUẢN LÝ DỮ LIỆU & CẤU HÌNH TÀI CHÍNH
# ==========================================
session = requests.Session()
headers = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/Mobile Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest'
}

USER_ACTIVE_PHONES = {}      # {chat_id: phone_number}
OTP_ACTIVE_SESSIONS = {}     # {phone: {"expire": timestamp, "otp": otp, "time": time_str}}
LAST_SEEN_OTPS = {}          # {phone: message_signature}
COUNTRY_CACHE = {}           # Kho số hoạt động theo lô (Phân loại toàn cầu)
CURRENT_FILE_POSITION = 0    # Con trỏ vị trí đọc file siêu nhẹ
USER_WITHDRAW_STATE = {}     # Trạng thái chờ user nhập ví USDT TON để rút tiền

USERS_FILE = "users_log.json"
STATS_FILE = "otp_stats.json"
SPAM_TRACKER_FILE = "spam_tracker.json"
SETTINGS_FILE = "settings.json"
USER_LAST_ACTION = {}        # Check thời gian thao tác chống spam

DEFAULT_SETTINGS = {
    "min_withdraw": 5.0,        # Min rút 5$
    "max_withdraw": 100.0,
    "otp_reward": 0.009,        # Thưởng nhận OTP 0.009$
    "refer_bonus": 0.01,        # Thưởng giới thiệu 0.01$
}

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        save_json_db(SETTINGS_FILE, DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS
    return load_json_db(SETTINGS_FILE)

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

# ==========================================
# 💰 4. QUẢN LÝ TÀI KHOẢN, SỐ DƯ & VÍ USER
# ==========================================
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

def update_balance(uid, amount):
    users = load_json_db(USERS_FILE)
    uid_str = str(uid)
    if uid_str in users:
        users[uid_str]["balance"] = round(users[uid_str].get("balance", 0.0) + amount, 4)
        save_json_db(USERS_FILE, users)
        return users[uid_str]["balance"]
    return 0.0

def mask_phone_number(phone):
    p = phone.strip()
    if len(p) > 6:
        return p[:4] + "***" + p[-2:]
    return p

# ==========================================
# 🛡️ 5. HỆ THỐNG CHỐNG SPAM 3 CẤP ĐỘ & UNBAN
# ==========================================
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
            return False, "⛔ <b>Tài khoản của bạn đã bị KHÓA VĨNH VIỄN</b> do vi phạm quy định spam nhiều lần."
            
        if now < ban_until:
            remaining_mins = int((ban_until - now) / 60) + 1
            return False, f"⏳ <b>Bạn đang bị tạm khóa do thao tác quá nhanh.</b>\n⏱ Thời gian mở khóa tự động sau: khoảng <b>{remaining_mins} phút</b> nữa."

    last_time = USER_LAST_ACTION.get(user_id, 0)
    if now - last_time < 0.8:
        if uid not in spam_data:
            count = 1
        else:
            count = spam_data[uid].get("count", 0) + 1
            
        if count == 1:
            ban_until = now + 300  # Phạt 5 phút
            msg = "⚠️ <b>Cảnh cáo Spam lần 1:</b> Bạn thao tác quá nhanh nên đã bị tạm khóa <b>5 phút</b>."
        elif count == 2:
            ban_until = now + 1800 # Phạt 30 phút
            msg = "⚠️ <b>Cảnh cáo Spam lần 2:</b> Nâng mức phạt tạm khóa <b>30 phút</b>."
        else:
            ban_until = 0          # Khóa vĩnh viễn
            msg = "⛔ <b>Khóa vĩnh viễn (Lần 3):</b> Tài khoản đã bị khóa vĩnh viễn do spam liên tục!"
            
        spam_data[uid] = {
            "name": name, 
            "count": count, 
            "ban_until": ban_until,
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
    "260": ("🇿🇲 Zambia (+260)", "ZM"), "263": ("🇿🇼 Zimbabwe (+263)", "ZW"), "258": ("🇲ℤ Mozambique (+258)", "MZ"),
    "244": ("🇦🇴 Angola (+244)", "AO"), "261": ("🇲🇬 Madagascar (+261)", "MG"), "249": ("🇸🇩 Sudan (+249)", "SD"),
    "221": ("🇸🇳 Senegal (+221)", "SN"), "223": ("🇲🇱 Mali (+223)", "ML"), "226": ("🇧🇫 Burkina Faso (+226)", "BF"),
    "227": ("🇳🇪 Niger (+227)", "NE"), "228": ("🇹🇬 Togo (+228)", "TG"), "229": ("🇧🇯 Benin (+229)", "BJ"),
    "235": ("🇹🇩 Chad (+235)", "TD"), "241": ("🇬🇦 Gabon (+241)", "GA"), "242": ("🇨🇬 Congo (+242)", "CG"),
    "243": ("🇨🇩 CHDC Congo (+243)", "CD"), "257": ("🇧🇮 Burundi (+257)", "BI"), "253": ("🇩🇯 Djibouti (+253)", "DJ"),
    "252": ("🇸🇴 Somalia (+252)", "SO"), "291": ("🇪🇷 Eritrea (+291)", "ER"), "232": ("🇸🇱 Sierra Leone (+232)", "SL"),
    "231": ("🇱🇷 Liberia (+231)", "LR"), "224": ("🇬🇳 Guinea (+224)", "GN"), "245": ("🇬🇼 Guinea-Bissau (+245)", "GW"),
    "220": ("🇬🇲 Gambia (+220)", "GM"), "230": ("🇲🇺 Mauritius (+230)", "MU"), "248": ("🇸🇨 Seychelles (+248)", "SC"),
    "269": ("🇰🇲 Comoros (+269)", "KM"), "268": ("🇸🇿 Eswatini (+268)", "SZ"), "266": ("🇱🇸 Lesotho (+266)", "LS"),
    "267": ("🇧🇼 Botswana (+267)", "BW"), "264": ("🇳🇦 Namibia (+264)", "NA"), "265": ("🇲🇼 Malawi (+265)", "MW"),
    "239": ("🇸🇹 São Tomé & Príncipe (+239)", "ST"), "240": ("🇬🇶 Guinea Xích Đạo (+240)", "GQ"), "236": ("🇨🇫 CH Trung Phi (+236)", "CF"),
    "222": ("🇲🇷 Mauritania (+222)", "MR"), "211": ("🇸🇸 Nam Sudan (+211)", "SS"), "290": ("🇸🇭 Saint Helena (+290)", "SH"),
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

# ==========================================
# 📢 7. HÀM BROADCAST THÔNG BÁO STOCK MỚI
# ==========================================
def broadcast_stock_updated(added_count, total_stock):
    text = (
        "✅ <b>Stock Updated!</b>\n"
        "__________________________________\n\n"
        "🌐 <b>Country:</b> GLOBAL / ALL COUNTRY 🌍\n"
        f"⏩ <b>Added:</b> {added_count}\n"
        f"📊 <b>Total Stock:</b> {total_stock}\n"
        "👤 <b>Uploaded by:</b> A D M I N\n"
        "__________________________________"
    )
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📲 Get Number", callback_data="open_countries"))

    try:
        bot.send_message(GROUP_CHAT_ID, text, parse_mode="HTML", reply_markup=markup)
    except Exception:
        pass

    users = load_json_db(USERS_FILE)
    for uid in users:
        try:
            bot.send_message(int(uid), text, parse_mode="HTML", reply_markup=markup)
            time.sleep(0.05)
        except Exception:
            pass

# ==========================================
# 🧹 8. TỰ ĐỘNG THU HỒI & XÓA SỐ SAU 5 PHÚT
# ==========================================
def clean_expired_sessions():
    now = time.time()
    expired_phones = []
    for phone, info in list(OTP_ACTIVE_SESSIONS.items()):
        if now > info.get("expire", 0):
            expired_phones.append(phone)
            
    for p in expired_phones:
        if p in OTP_ACTIVE_SESSIONS:
            del OTP_ACTIVE_SESSIONS[p]
        for cid, active_p in list(USER_ACTIVE_PHONES.items()):
            if active_p == p:
                del USER_ACTIVE_PHONES[cid]

def load_text_batch(reset=False):
    global COUNTRY_CACHE, CURRENT_FILE_POSITION
    if reset:
        CURRENT_FILE_POSITION = 0
        
    file_path = "numbers.txt"
    if not os.path.exists(file_path):
        COUNTRY_CACHE = {}
        return False, "Không tìm thấy file numbers.txt!"
    
    clean_expired_sessions()
    try:
        batch_numbers = []
        with open(file_path, "r", encoding="utf-8") as f:
            f.seek(CURRENT_FILE_POSITION)
            while len(batch_numbers) < 100:
                line = f.readline()
                if not line:
                    CURRENT_FILE_POSITION = 0
                    f.seek(0)
                    line = f.readline()
                    if not line:
                        break
                num_str = line.strip()
                if num_str:
                    digits_only = re.sub(r'\D', '', num_str)
                    if len(digits_only) >= 7:
                        formatted = "+" + digits_only
                        if formatted not in batch_numbers and formatted not in OTP_ACTIVE_SESSIONS:
                            batch_numbers.append(formatted)
            CURRENT_FILE_POSITION = f.tell()

        if not batch_numbers:
            COUNTRY_CACHE = {}
            return False, "File numbers.txt trống!"

        temp_cache = {}
        for formatted in batch_numbers:
            name, code = get_country_info(formatted)
            if code not in temp_cache:
                temp_cache[code] = {"name": name, "numbers": []}
            if formatted not in temp_cache[code]["numbers"]:
                temp_cache[code]["numbers"].append(formatted)
        COUNTRY_CACHE = temp_cache
        
        count = len(batch_numbers)
        threading.Thread(target=broadcast_stock_updated, args=(count, count), daemon=True).start()
        return True, count
    except Exception as e:
        return False, str(e)

if os.path.exists("numbers.txt"):
    load_text_batch()

def get_numbers_by_category(category_code, page=0, limit=6):
    clean_expired_sessions()
    if category_code in COUNTRY_CACHE:
        all_nums = [n for n in COUNTRY_CACHE[category_code]["numbers"] if n not in OTP_ACTIVE_SESSIONS]
        start = page * limit
        end = start + limit
        return all_nums[start:end], len(all_nums)
    return [], 0

def get_available_countries():
    clean_expired_sessions()
    valid_countries = {}
    for code, data in COUNTRY_CACHE.items():
        active_nums = [n for n in data["numbers"] if n not in OTP_ACTIVE_SESSIONS]
        if active_nums:
            valid_countries[code] = f"{data['name']} [{len(active_nums)} Stock]"
    return valid_countries

# ==========================================
# ⚡ 9. GỬI OTP, CỘNG THƯỞNG 0.009$ & TỰ THU HỒI
# ==========================================
def send_auto_otp(chat_id, number, otp_code, full_msg="", user_id=None, user_name=None):
    settings = load_settings()
    reward = settings.get("otp_reward", 0.009)
    
    if user_id:
        update_balance(user_id, reward)
        stats = load_json_db(STATS_FILE)
        uid_str = str(user_id)
        if uid_str not in stats:
            stats[uid_str] = {"name": user_name, "count": 0}
        stats[uid_str]["count"] += 1
        save_json_db(STATS_FILE, stats)

    text = (
        "⚡️ <b>HỆ THỐNG XÁC THỰC TỰ ĐỘNG</b> ⚡️\n"
        "-----------------------------------\n"
        f"📞 <b>Số điện thoại:</b> <code>{number}</code>\n"
        f"🔑 <b>Mã OTP:</b> <code>{otp_code}</code>\n"
        f"💰 <b>Thưởng nhận OTP:</b> +<code>${reward:.3f}</code>\n"
    )
    if full_msg:
        text += f"💬 <b>Nội dung:</b> <i>{full_msg[:100]}</i>\n"
    text += "\n⏳ <b>Trạng thái:</b> <i>Đã nhận OTP thành công, cộng 0.009$ vào ví và tự động xóa/thu hồi số!</i>"

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(f"📋 COPY OTP • {otp_code}", callback_data=f"copy_{otp_code}"))
    try:
        bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)
    except Exception as e:
        print(f"Lỗi gửi OTP tới {chat_id}: {e}")

def fetch_and_parse_otps():
    clean_expired_sessions()
    found_otps = []
    today_str = datetime.datetime.now().strftime('%Y-%m-%d')
    yesterday_str = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    
    urls = [
        ("https://ivasms.com/portal/sms_received", {'start_date': yesterday_str, 'end_date': today_str}),
        ("https://ivasms.com/portal/live", None)
    ]
    
    for url, post_data in urls:
        try:
            if post_data:
                resp = session.post(url, data=post_data, headers=headers, timeout=10)
                if resp.status_code != 200 or len(resp.text) < 300:
                    resp = session.get(url, headers=headers, timeout=10)
            else:
                resp = session.get(url, headers=headers, timeout=10)
                
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                for element in soup.find_all(['tr', 'div', 'td']):
                    text_content = element.get_text(separator=" ", strip=True)
                    for code, data in COUNTRY_CACHE.items():
                        for phone in data["numbers"]:
                            clean_phone = phone.replace("+", "").strip()
                            if clean_phone in text_content:
                                otps = re.findall(r'\b\d{4,6}\b', text_content)
                                for otp in otps:
                                    if len(otp) >= 4 and not otp.startswith('2026') and otp != clean_phone[-4:]:
                                        if phone not in OTP_ACTIVE_SESSIONS:
                                            expire_time = time.time() + 300 
                                            current_time_str = datetime.datetime.now().strftime('%H:%M:%S - %d/%m/%Y')
                                            OTP_ACTIVE_SESSIONS[phone] = {
                                                "expire": expire_time,
                                                "otp": otp,
                                                "time": current_time_str
                                            }
                                        target_cid = None
                                        for cid, p in USER_ACTIVE_PHONES.items():
                                            if p == phone:
                                                target_cid = cid
                                                break
                                        found_otps.append((phone, otp, text_content, target_cid))
        except Exception as e:
            print(f"Lỗi quét SMS từ {url}: {e}")
    return found_otps

def background_sms_scanner():
    while True:
        try:
            results = fetch_and_parse_otps()
            for phone, otp, full_msg, target_cid in results:
                sig = f"{phone}_{otp}"
                if sig != LAST_SEEN_OTPS.get(phone):
                    LAST_SEEN_OTPS[phone] = sig
                    if target_cid:
                        user_info = get_user(target_cid)
                        send_auto_otp(target_cid, phone, otp, full_msg, user_id=target_cid, user_name=user_info.get("name"))
        except Exception as e:
            print(f"Lỗi background scanner: {e}")
        time.sleep(3)

# ==========================================
# 📲 10. LỆNH /START & GIAO DIỆN CHÍNH
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
    
    # Xử lý link giới thiệu
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        ref_id = int(args[1])
        if ref_id != uid:
            users_db = load_json_db(USERS_FILE)
            uid_str = str(uid)
            if uid_str in users_db and users_db[uid_str].get("referred_by") is None:
                users_db[uid_str]["referred_by"] = ref_id
                ref_str = str(ref_id)
                if ref_str in users_db:
                    settings = load_settings()
                    bonus = settings.get("refer_bonus", 0.01)
                    users_db[ref_str]["referrals"] = users_db[ref_str].get("referrals", 0) + 1
                    users_db[ref_str]["balance"] = round(users_db[ref_str].get("balance", 0.0) + bonus, 4)
                    users_db[ref_str]["referral_earnings"] = round(users_db[ref_str].get("referral_earnings", 0.0) + bonus, 4)
                save_json_db(USERS_FILE, users_db)

    text = (
        f"👋 Chào mừng <b>{name}</b> đến với hệ thống <b>IVASMS OTP Global</b>!\n\n"
        "🌐 Hỗ trợ nhận số & OTP tự động 195+ quốc gia.\n"
        "💰 Kiếm <b>0.009$</b> thưởng tự động khi nhận mã OTP thành công!\n"
        "⏳ Tự động thu hồi số sau 5 phút để bảo vệ kho số."
    )
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📲 Bắt đầu Lấy Số", callback_data="open_countries"),
        InlineKeyboardButton("💰 Số dư / Ví", callback_data="my_wallet")
    )
    markup.add(
        InlineKeyboardButton("👥 Giới thiệu bạn bè", callback_data="refer_earn"),
        InlineKeyboardButton("📊 Thống kê", callback_data="my_stats")
    )
    markup.add(InlineKeyboardButton("💬 Hỗ trợ", url=GROUP_OTP_LINK))
    if uid == ADMIN_ID:
        markup.add(InlineKeyboardButton("👑 Bảng Điều Khiển Admin", callback_data="admin_panel"))
        
    bot.send_message(uid, text, parse_mode="HTML", reply_markup=markup)

# ==========================================
# 🔄 11. XỬ LÝ SỰ KIỆN CALLBACK QUERY
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = call.from_user.id
    data = call.data
    
    if data == "open_countries":
        countries = get_available_countries()
        if not countries:
            bot.answer_callback_query(call.id, "Kho số hiện tại đang trống hoặc đang cập nhật!", show_alert=True)
            return
            
        markup = InlineKeyboardMarkup(row_width=1)
        for code, label in countries.items():
            markup.add(InlineKeyboardButton(label, callback_data=f"country_{code}_0"))
        markup.add(InlineKeyboardButton("🔙 Quay lại", callback_data="back_home"))
        
        try:
            bot.edit_message_text("🌍 <b>Chọn Quốc Gia Cần Lấy Số:</b>", call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)
        except Exception:
            pass

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
            markup.add(InlineKeyboardButton(f"📞 {masked} (Lấy ngay)", callback_data=f"getnum_{code}_{page}_{num}"))
            
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Trang trước", callback_data=f"country_{code}_{page-1}"))
        if (page + 1) * 6 < total:
            nav_buttons.append(InlineKeyboardButton("Trang sau ➡️", callback_data=f"country_{code}_{page+1}"))
        if nav_buttons:
            markup.row(*nav_buttons)
            
        markup.add(InlineKeyboardButton("🔙 Chọn Quốc Gia Khác", callback_data="open_countries"))
        
        try:
            bot.edit_message_text(f"📋 <b>Danh sách số sẵn sàng ({code}):</b>", call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)
        except Exception:
            pass

    elif data.startswith("getnum_"):
        parts = data.split("_")
        phone = parts[3]
        chat_id = call.message.chat.id
        
        USER_ACTIVE_PHONES[chat_id] = phone
        OTP_ACTIVE_SESSIONS[phone] = {
            "expire": time.time() + 300, 
            "otp": "PENDING",
            "time": datetime.datetime.now().strftime('%H:%M:%S - %d/%m/%Y')
        }
        
        text = (
            "✅ <b>ĐÃ CẤP SỐ THÀNH CÔNG!</b>\n"
            "-----------------------------------\n"
            f"📞 <b>Số điện thoại:</b> <code>{phone}</code>\n"
            "💬 <b>Trạng thái:</b> Bot đang tự động lắng nghe tin nhắn OTP...\n"
            "⏳ <i>Số này có hiệu lực 5 phút, tự động xóa/thu hồi sau khi nhận OTP hoặc hết giờ!</i>"
        )
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔄 Kiểm tra tin nhắn ngay", callback_data=f"checksms_{phone}"))
        markup.add(InlineKeyboardButton("❌ Đổi số khác", callback_data="open_countries"))
        
        try:
            bot.edit_message_text(text, chat_id, call.message.message_id, parse_mode="HTML", reply_markup=markup)
        except Exception:
            pass

    elif data.startswith("checksms_"):
        phone = data.replace("checksms_", "")
        if phone in OTP_ACTIVE_SESSIONS and OTP_ACTIVE_SESSIONS[phone]["otp"] != "PENDING":
            info = OTP_ACTIVE_SESSIONS[phone]
            send_auto_otp(call.message.chat.id, phone, info["otp"], user_id=uid, user_name=call.from_user.first_name)
            bot.answer_callback_query(call.id, "Đã tìm thấy mã OTP gần nhất!", show_alert=False)
        else:
            bot.answer_callback_query(call.id, "Chưa có tin nhắn OTP nào cho số này. Thử lại sau ít giây!", show_alert=True)

    elif data.startswith("copy_"):
        otp_val = data.replace("copy_", "")
        bot.answer_callback_query(call.id, f"Đã copy mã OTP: {otp_val}", show_alert=False)

    elif data == "my_wallet":
        user_info = get_user(uid, call.from_user.first_name, call.from_user.username or "")
        settings = load_settings()
        balance = user_info.get("balance", 0.0)
        min_w = settings.get("min_withdraw", 5.0)
        
        text = (
            "💰 <b>VÍ TÀI KHOẢN & THÔNG TIN CÁ NHÂN</b>\n"
            "-----------------------------------\n"
            f"👤 <b>Họ và tên:</b> {user_info.get('name')}\n"
            f"🆔 <b>Telegram ID:</b> <code>{uid}</code>\n"
            f"📅 <b>Ngày đăng ký:</b> {user_info.get('joined_at')}\n"
            f"💵 <b>Số dư hiện tại:</b> <code>${balance:.4f}</code>\n"
            f"📉 <b>Hạn mức rút tối thiểu:</b> <code>${min_w:.1f}</code>\n"
            f"⚡ <b>Phí giao dịch rút:</b> <code>0% (Miễn phí)</code>\n"
        )
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("💸 Yêu cầu Rút tiền (USDT - Mạng TON)", callback_data="request_withdraw"),
            InlineKeyboardButton("🔙 Quay lại Menu Chính", callback_data="back_home")
        )
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)
        except Exception:
            pass

    elif data == "request_withdraw":
        user_info = get_user(uid)
        settings = load_settings()
        balance = user_info.get("balance", 0.0)
        min_w = settings.get("min_withdraw", 5.0)
        
        if balance < min_w:
            bot.answer_callback_query(call.id, f"Số dư chưa đủ để rút! Tối thiểu cần ${min_w:.1f}", show_alert=True)
        else:
            # Kích hoạt trạng thái nhập ví TON
            USER_WITHDRAW_STATE[uid] = True
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("❌ Hủy bỏ & Quay lại", callback_data="my_wallet"))
            try:
                bot.edit_message_text(
                    "📥 <b>HỆ THỐNG RÚT TIỀN TỰ ĐỘNG</b>\n"
                    "-----------------------------------\n"
                    "💎 <b>Loại tài sản:</b> USDT (Mạng TON)\n"
                    "💸 <b>Phí rút tiền:</b> <code>0% (Miễn phí hoàn toàn)</code>\n\n"
                    "👇 Vui lòng gửi địa chỉ ví <b>USDT mạng TON</b> của bạn vào khung chat bên dưới:\n"
                    "<i>(Ví chuẩn TON phải bắt đầu bằng <b>EQ</b> hoặc <b>UQ</b> và có đúng <b>48 ký tự</b>).</i>\n\n"
                    "⚠️ <i>Lưu ý: Hệ thống sẽ tự động quét đúng định dạng mạng TON để bảo vệ tài sản của bạn!</i>",
                    call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup
                )
            except Exception:
                pass

    elif data == "refer_earn":
        bot_info = bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={uid}"
        user_info = get_user(uid)
        settings = load_settings()
        bonus = settings.get("refer_bonus", 0.01)
        
        text = (
            "👥 <b>CHƯƠNG TRÌNH GIỚI THIỆU BẠN BÈ</b>\n"
            "-----------------------------------\n"
            f"🎁 <b>Thưởng mỗi lượt mời:</b> <code>${bonus:.2f}</code>\n"
            f"📊 <b>Tổng số bạn đã mời:</b> <b>{user_info.get('referrals', 0)}</b> người\n"
            f"💵 <b>Tổng tiền hoa hồng:</b> <code>${user_info.get('referral_earnings', 0.0):.4f}</code>\n\n"
            "🔗 <b>Link giới thiệu của bạn:</b>\n"
            f"<code>{ref_link}</code>"
        )
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Quay lại", callback_data="back_home"))
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)
        except Exception:
            pass

    elif data == "my_stats":
        stats = load_json_db(STATS_FILE)
        uid_str = str(uid)
        my_count = stats.get(uid_str, {}).get("count", 0)
        
        text = (
            "📊 <b>Thống kê cá nhân:</b>\n"
            f"👤 <b>Tên:</b> {call.from_user.first_name}\n"
            f"🆔 <b>Telegram ID:</b> <code>{uid}</code>\n"
            f"🔑 <b>Tổng số OTP nhận thành công:</b> <b>{my_count}</b> mã\n"
        )
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Quay lại", callback_data="back_home"))
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)
        except Exception:
            pass

    elif data == "back_home":
        USER_WITHDRAW_STATE.pop(uid, None)
        text = "👋 Chào mừng bạn quay lại menu chính của **IVASMS OTP Global**!"
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("📲 Bắt đầu Lấy Số", callback_data="open_countries"),
            InlineKeyboardButton("💰 Số dư / Ví", callback_data="my_wallet")
        )
        markup.add(
            InlineKeyboardButton("👥 Giới thiệu", callback_data="refer_earn"),
            InlineKeyboardButton("📊 Thống kê", callback_data="my_stats")
        )
        markup.add(InlineKeyboardButton("💬 Hỗ trợ", url=GROUP_OTP_LINK))
        if uid == ADMIN_ID:
            markup.add(InlineKeyboardButton("👑 Bảng Điều Khiển Admin", callback_data="admin_panel"))
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)
        except Exception:
            pass

    elif data == "admin_panel" and uid == ADMIN_ID:
        users = load_json_db(USERS_FILE)
        spam_data = load_json_db(SPAM_TRACKER_FILE)
        text = (
            "👑 <b>BẢNG ĐIỀU KHIỂN ADMIN TỐI CAO</b>\n"
            "-----------------------------------\n"
            f"👥 Tổng số user: <b>{len(users)}</b>\n"
            f"📊 Tổng số stock: <b>{sum(len(d['numbers']) for d in COUNTRY_CACHE.values())}</b>\n"
            f"🛡 Số tài khoản đang bị phạt/khóa: <b>{len(spam_data)}</b>\n"
        )
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("🔄 Nạp Batch Số Mới", callback_data="admin_reload"),
            InlineKeyboardButton("🛡 Quản lý & Mở khóa Spam", callback_data="admin_users")
        )
        markup.add(InlineKeyboardButton("🔙 Quay lại Menu Chính", callback_data="back_home"))
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)
        except Exception:
            pass

    elif data == "admin_reload" and uid == ADMIN_ID:
        success, res = load_text_batch(reset=False)
        if success:
            bot.answer_callback_query(call.id, f"Đã nạp thành công: {res} số!", show_alert=True)
        else:
            bot.answer_callback_query(call.id, f"Lỗi: {res}", show_alert=True)

    elif data == "admin_users" and uid == ADMIN_ID:
        spam_data = load_json_db(SPAM_TRACKER_FILE)
        text = f"🛡 <b>Danh sách tài khoản đang vi phạm / bị khóa:</b>\n\n"
        
        markup = InlineKeyboardMarkup(row_width=1)
        if not spam_data:
            text += "<i>Hiện không có user nào bị phạt.</i>"
        else:
            for s_id, info in spam_data.items():
                b_type = "Vĩnh viễn" if info.get('ban_until') == 0 else "Tạm thời"
                text += f"• ID: <code>{s_id}</code> | Tên: {info.get('name')} | Vi phạm: {info.get('count')} lần ({b_type})\n"
                markup.add(InlineKeyboardButton(f"🔓 Mở khóa ID: {s_id}", callback_data=f"unban_{s_id}"))
                
        markup.add(InlineKeyboardButton("🔙 Quay lại Admin Panel", callback_data="admin_panel"))
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)
        except Exception:
            pass

    elif data.startswith("unban_") and uid == ADMIN_ID:
        target_uid = data.replace("unban_", "")
        if unban_user_manual(target_uid):
            bot.answer_callback_query(call.id, f"Đã gỡ khóa thành công cho ID: {target_uid}", show_alert=True)
            call.data = "admin_users"
            handle_callbacks(call)
        else:
            bot.answer_callback_query(call.id, "Không tìm thấy user này trong danh sách phạt!", show_alert=True)

# ==========================================
# 💸 12. XỬ LÝ QUÉT & KIỂM TRA ĐỊNH DẠNG VÍ TON (0% PHÍ)
# ==========================================
@bot.message_handler(func=lambda message: USER_WITHDRAW_STATE.get(message.from_user.id, False))
def handle_withdraw_address(message):
    uid = message.from_user.id
    wallet_addr = message.text.strip()
    
    if wallet_addr.startswith('/'):
        USER_WITHDRAW_STATE.pop(uid, None)
        return
        
    # Regex kiểm tra chính xác ví TON chuẩn (Bắt đầu EQ hoặc UQ, tổng đúng 48 ký tự)
    TON_ADDRESS_REGEX = re.compile(r'^(EQ|UQ)[A-Za-z0-9\-_]{46}$')
    if not TON_ADDRESS_REGEX.match(wallet_addr):
        bot.send_message(
            uid,
            "❌ <b>ĐỊA CHỈ VÍ KHÔNG HỢP LỆ!</b>\n\n"
            "Hệ thống kiểm tra thấy địa chỉ ví bạn vừa nhập <b>không đúng chuẩn mạng TON</b>.\n"
            "• Ví USDT mạng TON phải bắt đầu bằng <b>EQ</b> hoặc <b>UQ</b>.\n"
            "• Tổng chiều dài phải chính xác <b>48 ký tự</b>.\n\n"
            "Vui lòng kiểm tra lại ví của bạn (Tonkeeper, Telegram Wallet...) và gửi lại chính xác:",
            parse_mode="HTML"
        )
        return
        
    # Hợp lệ -> Xóa trạng thái chờ
    USER_WITHDRAW_STATE.pop(uid, None)
    
    settings = load_settings()
    user_info = get_user(uid)
    min_w = settings.get("min_withdraw", 5.0)
    
    users_db = load_json_db(USERS_FILE)
    uid_str = str(uid)
    if uid_str in users_db:
        with_amount = users_db[uid_str]["balance"]
        if with_amount < min_w:
            bot.send_message(uid, f"❌ Số dư hiện tại (${with_amount:.4f}) không đủ hạn mức rút tối thiểu (${min_w:.1f})!")
            return
            
        # Trừ tiền trong ví user
        users_db[uid_str]["balance"] = 0.0
        save_json_db(USERS_FILE, users_db)
        
        # Gửi thông báo chi tiết đến Admin
        admin_text = (
            "💸 <b>YÊU CẦU RÚT TIỀN THÀNH CÔNG (0% PHÍ)</b>\n"
            "-----------------------------------\n"
            f"👤 <b>Họ tên:</b> {user_info.get('name')}\n"
            f"🆔 <b>Telegram ID:</b> <code>{uid}</code>\n"
            f"🔗 <b>Username:</b> @{user_info.get('username', 'Không có')}\n"
            f"💵 <b>Số tiền rút:</b> <code>${with_amount:.4f} USDT</code>\n"
            f"💎 <b>Mạng lưới:</b> TON Network (Phí 0%)\n"
            f"📤 <b>Địa chỉ ví đích:</b> <code>{wallet_addr}</code>\n"
            f"⏰ <b>Thời gian:</b> {datetime.datetime.now().strftime('%H:%M:%S - %d/%m/%Y')}"
        )
        
        try:
            bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML")
        except Exception:
            pass
            
        bot.send_message(
            uid,
            "✅ <b>GỬI YÊU CẦU RÚT TIỀN THÀNH CÔNG!</b>\n"
            "-----------------------------------\n"
            f"💵 Số tiền: <b>${with_amount:.4f} USDT</b>\n"
            f"⚡ Phí giao dịch: <b>0% (Miễn phí)</b>\n"
            f"📤 Ví nhận (Mạng TON): <code>{wallet_addr}</code>\n\n"
            "⏳ Địa chỉ ví của bạn đã vượt qua bộ lọc chuẩn mạng TON. Yêu cầu đã được gửi đến Admin để thanh toán!",
            parse_mode="HTML"
        )

# ==========================================
# 🚀 13. KHỞI ĐỘNG HỆ THỐNG SONG SONG 24/7
# ==========================================
if __name__ == "__main__":
    t_scanner = threading.Thread(target=background_sms_scanner, daemon=True)
    t_scanner.start()
    
    t_web = threading.Thread(target=run_web, daemon=True)
    t_web.start()
    
    print("🤖 Bot Telegram IVASMS (Auto Thu Hồi 5p + Quét Ví TON 0% Phí + Full 195+ Quốc Gia) đang chạy...")
    bot.infinity_polling(skip_pending=True)
