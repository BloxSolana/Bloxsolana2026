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

# 👑 CẤU HÌNH ADMIN TỐI CAO & BOT
ADMIN_ID = 6726769296
TOKEN = "8622066775:AAE0XAWu7N5RXK_2FQIGc37rjqIILXQolac"
GROUP_CHAT_ID = "-1004341368656"
GROUP_OTP_LINK = "https://t.me/LIVEOTPIVAS"

bot = telebot.TeleBot(TOKEN)

# 🌐 FLASK WEB SERVER (Giúp Render giữ bot online 24/7 không bị ngủ đông)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot IVASMS OTP Global đang chạy mượt mà 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# 🧹 Tắt Webhook cũ & xả kẹt hàng chờ Telegram
try:
    bot.remove_webhook()
except Exception:
    pass

# --- CẤU HÌNH PHIÊN LÀM VIỆC NGẦM ---
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

# 📂 HỆ THỐNG LƯU TRỮ DỮ LIỆU
USERS_FILE = "users_log.json"
STATS_FILE = "otp_stats.json"
SPAM_TRACKER_FILE = "spam_tracker.json"
USER_LAST_ACTION = {}        # Dùng để check thời gian spam của user

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

# 🔒 HÀM CHE SỐ ĐIỆN THOẠI (GIỮ ĐẦU, GIỮA ***, CUỐI 2 SỐ)
def mask_phone_number(phone):
    p = phone.strip()
    if len(p) > 6:
        return p[:4] + "***" + p[-2:]
    return p

# --- 🛡️ HỆ THỐNG CHỐNG SPAM 3 CẤP ĐỘ THÔNG MINH ---
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
            
        spam_data[uid] = {"name": name, "count": count}
        
        if count == 1:
            spam_data[uid]["ban_until"] = now + 300
            spam_data[uid]["banned_at"] = datetime.datetime.now().strftime('%H:%M:%S - %d/%m/%Y')
            save_json_db(SPAM_TRACKER_FILE, spam_data)
            return False, "⚠️ <b>Cảnh cáo Spam lần 1:</b> Bạn thao tác quá nhanh nên đã bị tạm khóa <b>5 phút</b>."
            
        elif count == 2:
            spam_data[uid]["ban_until"] = now + 1800
            spam_data[uid]["banned_at"] = datetime.datetime.now().strftime('%H:%M:%S - %d/%m/%Y')
            save_json_db(SPAM_TRACKER_FILE, spam_data)
            return False, "⚠️ <b>Cảnh cáo Spam lần 2:</b> Nâng mức phạt tạm khóa <b>30 phút</b>."
            
        else:
            spam_data[uid]["ban_until"] = 0
            spam_data[uid]["banned_at"] = datetime.datetime.now().strftime('%H:%M:%S - %d/%m/%Y')
            save_json_db(SPAM_TRACKER_FILE, spam_data)
            return False, "⛔ <b>Khóa vĩnh viễn (Lần 3):</b> Tài khoản đã bị khóa vĩnh viễn!"

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

def log_new_user(message):
    users = load_json_db(USERS_FILE)
    uid = str(message.from_user.id)
    if uid not in users:
        users[uid] = {
            "id": message.from_user.id,
            "name": message.from_user.first_name or "Ẩn danh",
            "username": message.from_user.username or "Không có",
            "joined_at": datetime.datetime.now().strftime('%H:%M:%S - %d/%m/%Y')
        }
        save_json_db(USERS_FILE, users)

def add_otp_stat(user_id, name):
    stats = load_json_db(STATS_FILE)
    uid = str(user_id)
    if uid not in stats:
        stats[uid] = {"name": name, "count": 0}
    stats[uid]["count"] += 1
    save_json_db(STATS_FILE, stats)

# 🌍 BỘ TỪ ĐIỂN ĐỊNH DANH FULL 195+ QUỐC GIA
GLOBAL_COUNTRY_PREFIXES = {
    "1": ("🇺🇸 Mỹ / Canada (+1)", "US"), "52": ("🇲🇽 Mexico (+52)", "MX"), "53": ("🇨🇺 Cuba (+53)", "CU"),
    "509": ("🇭🇹 Haiti (+509)", "HT"), "1809": ("🇩🇴 CH Dominica (+1-809)", "DO"), "502": ("🇬🇹 Guatemala (+502)", "GT"),
    "504": ("🇭🇳 Honduras (+504)", "HN"), "505": ("🇳🇮 Nicaragua (+505)", "NI"), "506": ("🇨🇷 Costa Rica (+506)", "CR"),
    "507": ("🇵🇦 Panama (+507)", "PA"), "503": ("🇸🇻 El Salvador (+503)", "SV"), "501": ("🇧🇿 Belize (+501)", "BZ"),
    "1876": ("🇯🇲 Jamaica (+1-876)", "JM"), "55": ("🇧🇷 Brazil (+55)", "BR"), "54": ("🇦🇷 Argentina (+54)", "AR"),
    "57": ("🇨🇴 Colombia (+57)", "CO"), "51": ("🇵🇪 Peru (+51)", "PE"), "58": ("🇻🇪 Venezuela (+58)", "VE"),
    "56": ("🇨🇱 Chile (+56)", "CL"), "593": ("🇪🇨 Ecuador (+593)", "EC"), "591": ("🇧🇴 Bolivia (+591)", "BO"),
    "595": ("🇵🇾 Paraguay (+595)", "PY"), "598": ("🇺🇾 Uruguay (+598)", "UY"), "592": ("🇬🇾 Guyana (+592)", "GY"),
    "597": ("🇸🇷 Suriname (+597)", "SR"), "44": ("🇬🇧 Vương Quốc Anh (+44)", "UK"), "33": ("🇫🇷 Pháp (+33)", "FR"),
    "49": ("🇩🇪 Đức (+49)", "DE"), "39": ("🇮🇹 Ý (+39)", "IT"), "34": ("🇪🇸 Tây Ban Nha (+34)", "ES"),
    "7": ("🇷🇺 Nga / Kazakhstan (+7)", "RU"), "380": ("🇺🇦 Ukraine (+380)", "UA"), "48": ("🇵🇱 Ba Lan (+48)", "PL"),
    "31": ("🇳🇱 Hà Lan (+31)", "NL"), "32": ("🇧🇪 Bỉ (+32)", "BE"), "41": ("🇨🇭 Thụy Sĩ (+41)", "CH"),
    "43": ("🇦🇹 Áo (+43)", "AT"), "46": ("🇸🇪 Thụy Điển (+46)", "SE"), "47": ("🇳🇴 Na Uy (+47)", "NO"),
    "45": ("🇩🇰 Đan Mạch (+45)", "DK"), "358": ("🇫🇮 Phần Lan (+358)", "FI"), "353": ("🇮🇪 Ai-len (+353)", "IE"),
    "351": ("🇵🇹 Bồ Đào Nha (+351)", "PT"), "30": ("🇬🇷 Hy Lạp (+30)", "GR"), "420": ("🇨🇿 Séc (+420)", "CZ"),
    "36": ("🇭🇺 Hungary (+36)", "HU"), "40": ("🇷🇴 Romania (+40)", "RO"), "359": ("🇧🇬 Bulgaria (+359)", "BG"),
    "385": ("🇭🇷 Croatia (+385)", "HR"), "386": ("🇸🇮 Slovenia (+386)", "SI"), "421": ("🇸🇰 Slovakia (+421)", "SK"),
    "370": ("🇱🇹 Lithuania (+370)", "LT"), "371": ("🇱🇻 Latvia (+371)", "LV"), "372": ("🇪🇪 Estonia (+372)", "EE"),
    "354": ("🇮🇸 Iceland (+354)", "IS"), "373": ("🇲🇩 Moldova (+373)", "MD"), "375": ("🇧🇾 Belarus (+375)", "BY"),
    "381": ("🇷🇸 Serbia (+381)", "RS"), "387": ("🇧🇦 Bosnia (+387)", "BA"), "382": ("🇲🇪 Montenegro (+382)", "ME"),
    "355": ("🇦🇱 Albania (+355)", "AL"), "356": ("🇲🇹 Malta (+356)", "MT"), "352": ("🇱🇺 Luxembourg (+352)", "LU"),
    "377": ("🇲🇨 Monaco (+377)", "MC"), "378": ("🇸🇲 San Marino (+378)", "SM"), "379": ("🇻🇦 Vatican (+379)", "VA"),
    "423": ("🇱🇮 Liechtenstein (+423)", "LI"), "350": ("🇬🇮 Gibraltar (+350)", "GI"), "84": ("🇻🇳 Việt Nam (+84)", "VN"),
    "86": ("🇨🇳 Trung Quốc (+86)", "CN"), "81": ("🇯🇵 Nhật Bản (+81)", "JP"), "82": ("🇰🇷 Hàn Quốc (+82)", "KR"),
    "91": ("🇮🇳 Ấn Độ (+91)", "IN"), "62": ("🇮🇩 Indonesia (+62)", "ID"), "92": ("🇵🇰 Pakistan (+92)", "PK"),
    "880": ("🇧🇩 Bangladesh (+880)", "BD"), "63": ("🇵🇭 Philippines (+63)", "PH"), "66": ("🇹🇭 Thái Lan (+66)", "TH"),
    "60": ("🇲🇾 Malaysia (+60)", "MY"), "65": ("🇸🇬 Singapore (+65)", "SG"), "95": ("🇲🇲 Myanmar (+95)", "MM"),
    "855": ("🇰🇭 Campuchia (+855)", "KH"), "856": ("🇱🇦 Lào (+856)", "LA"), "94": ("🇱🇰 Sri Lanka (+94)", "LK"),
    "977": ("🇳🇵 Nepal (+977)", "NP"), "93": ("🇦🇫 Afghanistan (+93)", "AF"), "98": ("🇮🇷 Iran (+98)", "IR"),
    "964": ("🇮🇶 Iraq (+964)", "IQ"), "90": ("🇹🇷 Thổ Nhĩ Kỳ (+90)", "TR"), "972": ("🇮🇱 Israel (+972)", "IL"),
    "962": ("🇯🇴 Jordan (+962)", "JO"), "961": ("🇱🇧 Lebanon (+961)", "LB"), "963": ("🇸🇾 Syria (+963)", "SY"),
    "965": ("🇰🇼 Kuwait (+965)", "KW"), "966": ("🇸🇦 Ả Rập Xê Út (+966)", "SA"), "971": ("🇦🇪 UAE (+971)", "AE"),
    "974": ("🇶🇦 Qatar (+974)", "QA"), "973": ("🇧🇭 Bahrain (+973)", "BH"), "968": ("🇴🇲 Oman (+968)", "OM"),
    "967": ("🇾🇪 Yemen (+967)", "YE"), "886": ("🇹🇼 Đài Loan (+886)", "TW"), "852": ("🇭🇰 Hồng Kong (+852)", "HK"),
    "853": ("🇲🇦 Ma Cao (+853)", "MO"), "976": ("🇲🇳 Mông Cổ (+976)", "MN"), "998": ("🇺🇿 Uzbekistan (+998)", "UZ"),
    "77": ("🇰🇿 Kazakhstan (+7)", "KZ"), "993": ("🇹🇲 Turkmenistan (+993)", "TM"), "992": ("🇹🇯 Tajikistan (+992)", "TJ"),
    "996": ("🇰🇬 Kyrgyzstan (+996)", "KG"), "994": ("🇦🇿 Azerbaijan (+994)", "AZ"), "374": ("🇦🇲 Armenia (+374)", "AM"),
    "995": ("🇬🇪 Georgia (+995)", "GE"), "673": ("🇧🇳 Brunei (+673)", "BN"), "670": ("🇹🇱 Đông Timor (+670)", "TL"),
    "960": ("🇲🇻 Maldives (+960)", "MV"), "970": ("🇵🇸 Palestine (+970)", "PS"), "975": ("🇧🇹 Bhutan (+975)", "BT"),
    "61": ("🇦🇺 Úc (+61)", "AU"), "64": ("🇳🇿 New Zealand (+64)", "NZ"), "675": ("🇵🇬 Papua New Guinea (+675)", "PG"),
    "679": ("🇫🇯 Fiji (+679)", "FJ"), "685": ("🇼🇸 Samoa (+685)", "WS"), "676": ("🇹🇴 Tonga (+676)", "TO"),
    "678": ("🇻🇺 Vanuatu (+678)", "VU"), "677": ("🇸🇧 Quần đảo Solomon (+677)", "SB"), "686": ("🇰🇮 Kiribati (+686)", "KI"),
    "691": ("🇫🇲 Micronesia (+691)", "FM"), "692": ("🇲🇭 Quần đảo Marshall (+692)", "MH"), "680": ("🇵🇼 Palau (+680)", "PW"),
    "688": ("🇹🇻 Tuvalu (+688)", "TV"), "674": ("🇳🇷 Nauru (+674)", "NR"), "20": ("🇪🇬 Ai Cập (+20)", "EG"),
    "27": ("🇿🇦 Nam Phi (+27)", "ZA"), "234": ("🇳🇬 Nigeria (+234)", "NG"), "254": ("🇰🇪 Kenya (+254)", "KE"),
    "251": ("🇪🇹 Ethiopia (+251)", "ET"), "212": ("🇲🇦 Maroc (+212)", "MA"), "213": ("🇩🇿 Algeria (+213)", "DZ"),
    "216": ("🇹🇳 Tunisia (+216)", "TN"), "218": ("🇱🇾 Libya (+218)", "LY"), "233": ("🇬🇭 Ghana (+233)", "GH"),
    "225": ("🇨🇮 Bờ Biển Ngà (+225)", "CI"), "237": ("🇨🇲 Cameroon (+237)", "CM"), "255": ("🇹🇿 Tanzania (+255)", "TZ"),
    "256": ("🇺🇬 Uganda (+256)", "UG"), "250": ("🇷🇼 Rwanda (+250)", "RW"), "260": ("🇿🇲 Zambia (+260)", "ZM"),
    "263": ("🇿🇼 Zimbabwe (+263)", "ZW"), "258": ("🇲ℤ Mozambique (+258)", "MZ"), "244": ("🇦🇴 Angola (+244)", "AO"),
    "261": ("🇲🇬 Madagascar (+261)", "MG"), "249": ("🇸🇩 Sudan (+249)", "SD"), "221": ("🇸🇳 Senegal (+221)", "SN"),
    "223": ("🇲🇱 Mali (+223)", "ML"), "226": ("🇧🇫 Burkina Faso (+226)", "BF"), "227": ("🇳🇪 Niger (+227)", "NE"),
    "228": ("🇹🇬 Togo (+228)", "TG"), "229": ("🇧🇯 Benin (+229)", "BJ"), "235": ("🇹🇩 Chad (+235)", "TD"),
    "241": ("🇬🇦 Gabon (+241)", "GA"), "242": ("🇨🇬 Congo (+242)", "CG"), "243": ("🇨🇩 CHDC Congo (+243)", "CD"),
    "257": ("🇧🇮 Burundi (+257)", "BI"), "253": ("🇩🇯 Djibouti (+253)", "DJ"), "252": ("🇸🇴 Somalia (+252)", "SO"),
    "291": ("🇪🇷 Eritrea (+291)", "ER"), "232": ("🇸🇱 Sierra Leone (+232)", "SL"), "231": ("🇱🇷 Liberia (+231)", "LR"),
    "224": ("🇬🇳 Guinea (+224)", "GN"), "245": ("🇬🇼 Guinea-Bissau (+245)", "GW"), "220": ("🇬🇲 Gambia (+220)", "GM"),
    "230": ("🇲🇺 Mauritius (+230)", "MU"), "248": ("🇸🇨 Seychelles (+248)", "SC"), "269": ("🇰🇲 Comoros (+269)", "KM"),
    "268": ("🇸🇿 Eswatini (+268)", "SZ"), "266": ("🇱🇸 Lesotho (+266)", "LS"), "267": ("🇧🇼 Botswana (+267)", "BW"),
    "264": ("🇳🇦 Namibia (+264)", "NA"), "265": ("🇲🇼 Malawi (+265)", "MW"), "239": ("🇸🇹 São Tomé & Príncipe (+239)", "ST"),
    "240": ("🇬🇶 Guinea Xích Đạo (+240)", "GQ"), "236": ("🇨🇫 CH Trung Phi (+236)", "CF"), "222": ("🇲🇷 Mauritania (+222)", "MR"),
    "290": ("🇸🇭 Saint Helena (+290)", "SH"),
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

# 📢 HÀM BROADCAST THÔNG BÁO STOCK UPDATED
def broadcast_stock_updated(added_count, total_stock):
    text = (
        "✅ <b>Stock Updated!</b>\n"
        "__________________________________\n\n"
        "🌐 <b>Country:</b> GLOBAL / ALL COUNTRY 🌍\n"
        "💬 <b>Service:</b> WhatsApp / Telegram / All SMS 🟢\n"
        f"⏩ <b>Added:</b> {added_count}\n"
        f"📊 <b>Total Stock:</b> {total_stock}\n"
        "👤 <b>Uploaded by:</b> A D M I N\n"
        "__________________________________"
    )
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📲 Get Number", callback_data="open_countries"))

    try:
        bot.send_message(GROUP_CHAT_ID, text, parse_mode="HTML", reply_markup=markup)
    except Exception as e:
        print(f"Lỗi broadcast group: {e}")

    users = load_json_db(USERS_FILE)
    for uid in users:
        try:
            bot.send_message(int(uid), text, parse_mode="HTML", reply_markup=markup)
            time.sleep(0.05)
        except Exception:
            pass

def load_text_batch(reset=False):
    global COUNTRY_CACHE, CURRENT_FILE_POSITION
    if reset:
        CURRENT_FILE_POSITION = 0
        
    file_path = "numbers.txt"
    if not os.path.exists(file_path):
        COUNTRY_CACHE = {}
        return False, "Không tìm thấy file numbers.txt trên server!"
    
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
                        is_expired_or_used = (formatted in OTP_ACTIVE_SESSIONS)
                        if formatted not in batch_numbers and not is_expired_or_used:
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
    if category_code in COUNTRY_CACHE:
        all_nums = [n for n in COUNTRY_CACHE[category_code]["numbers"] if n not in OTP_ACTIVE_SESSIONS]
        start = page * limit
        end = start + limit
        return all_nums[start:end], len(all_nums)
    return [], 0

def get_available_countries():
    valid_countries = {}
    for code, data in COUNTRY_CACHE.items():
        active_nums = [n for n in data["numbers"] if n not in OTP_ACTIVE_SESSIONS]
        if active_nums:
            valid_countries[code] = f"{data['name']} [{len(active_nums)} Stock]"
    return valid_countries

def send_auto_otp(chat_id, number, otp_code, full_msg="", user_id=None, user_name=None):
    if user_id:
        add_otp_stat(user_id, user_name)
    text = (
        "⚡️ <b>HỆ THỐNG XÁC THỰC TỰ ĐỘNG</b> ⚡️\n"
        "-----------------------------------\n"
        f"📞 <b>Số điện thoại:</b> <code>{number}</code>\n"
        f"🔑 <b>Mã OTP:</b> <code>{otp_code}</code>\n"
    )
    if full_msg:
        text += f"💬 <b>Nội dung:</b> <i>{full_msg[:100]}</i>\n"
    text += "\n⏳ <b>Trạng thái:</b> <i>Số đã nhận OTP và sẽ tự động thu hồi sau 5 phút!</i>"

    markup = InlineKeyboardMarkup()
    btn_copy = InlineKeyboardButton(f"📋 COPY OTP • {otp_code}", callback_data=f"copy_{otp_code}")
    markup.add(btn_copy)
    try:
        bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)
    except Exception as e:
        print(f"Lỗi gửi tin nhắn auto tới {chat_id}: {e}")

def fetch_and_parse_otps():
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
                                        found_otps.append({
                                            'chat_id': target_cid,
                                            'phone': phone,
                                            'otp': otp,
                                            'raw_text': text_content
                                        })
        except Exception:
            pass
    return found_otps

def background_otp_scanner():
    while True:
        try:
            now = time.time()
            expired_phones = []
            for phone, session_data in list(OTP_ACTIVE_SESSIONS.items()):
                if now > session_data["expire"]:
                    expired_phones.append(phone)
            
            if expired_phones:
                for phone in expired_phones:
                    for code in COUNTRY_CACHE:
                        if phone in COUNTRY_CACHE[code]["numbers"]:
                            COUNTRY_CACHE[code]["numbers"].remove(phone)
                    for cid, p in list(USER_ACTIVE_PHONES.items()):
                        if p == phone:
                            USER_ACTIVE_PHONES.pop(cid, None)

            otps_data = fetch_and_parse_otps()
            for item in otps_data:
                phone = item['phone']
                otp = item['otp']
                sig = f"{phone}_{otp}"
                if LAST_SEEN_OTPS.get(phone) != sig:
                    LAST_SEEN_OTPS[phone] = sig
                    if item['chat_id']:
                        send_auto_otp(item['chat_id'], phone, otp, item['raw_text'], item['chat_id'], "Thành viên")
                    masked_phone = mask_phone_number(phone)
                    try:
                        bot.send_message(
                            GROUP_CHAT_ID, 
                            f"⚡️ <b>BẮT ĐƯỢC MÃ XÁC THỰC</b>\n📞 Số: <code>{masked_phone}</code>\n🔑 OTP: <code>{otp}</code>", 
                            parse_mode="HTML"
                        )
                    except Exception:
                        pass
        except Exception:
            pass
        time.sleep(5)

# 🔄 ĐỊNH NGHĨA HÀM GIÁM SÁT LUỒNG NGẦM (ĐÃ ĐƯA LÊN TRƯỚC KHI GỌI)
scanner_thread = None

def ensure_scanner_running():
    global scanner_thread
    while True:
        try:
            if scanner_thread is None or not scanner_thread.is_alive():
                scanner_thread = threading.Thread(target=background_otp_scanner, daemon=True)
                scanner_thread.start()
        except Exception:
            pass
        time.sleep(10)

# 📱 GIAO DIỆN USER (CHIA 2 CỘT)
def get_user_markup(chat_id):
    phone = USER_ACTIVE_PHONES.get(chat_id, "Chưa chọn số")
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(f"🌍 Chọn Số (Đang dùng: {phone})", callback_data="open_countries"))
    markup.row(
        InlineKeyboardButton("🔄 Kiểm tra", callback_data="check_active"),
        InlineKeyboardButton("🏆 Xếp Hạng", callback_data="open_leaderboard")
    )
    markup.add(InlineKeyboardButton("👥 Group OTP", url=GROUP_OTP_LINK))
    return markup

# 👑 GIAO DIỆN ADMIN (CHIA 2 CỘT)
def get_admin_markup(chat_id):
    total_working = len(OTP_ACTIVE_SESSIONS)
    total_banned = len(load_json_db(SPAM_TRACKER_FILE))
    phone = USER_ACTIVE_PHONES.get(chat_id, "Chưa chọn số")
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(f"🌍 Chọn Số (Đang dùng: {phone})", callback_data="open_countries"))
    markup.row(
        InlineKeyboardButton("🔄 Kiểm tra", callback_data="check_active"),
        InlineKeyboardButton("🏆 Xếp Hạng", callback_data="open_leaderboard")
    )
    markup.row(
        InlineKeyboardButton(f"📋 Số Sống ({total_working})", callback_data="admin_working_nums"),
        InlineKeyboardButton(f"🛡️ Khóa/Mở ({total_banned})", callback_data="admin_banned_list")
    )
    markup.row(
        InlineKeyboardButton("👑 Thống Kê", callback_data="admin_stats"),
        InlineKeyboardButton("👥 Thành Viên", callback_data="admin_users")
    )
    markup.row(
        InlineKeyboardButton("🔄 Đổi Lô 100 Số", callback_data="admin_sync"),
        InlineKeyboardButton("⏪ Reset Kho Số", callback_data="admin_reset")
    )
    markup.add(InlineKeyboardButton("👥 Group OTP", url=GROUP_OTP_LINK))
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    uid = message.from_user.id
    uname = message.from_user.first_name or "Ẩn danh"
    
    ok, msg = check_user_status(uid, uname)
    if not ok:
        bot.reply_to(message, msg, parse_mode="HTML")
        return

    log_new_user(message)
    is_admin = (uid == ADMIN_ID)
    
    text = f"Chào {uname}! 👋\n👑 **Hệ thống Kho Số Toàn Cầu & Nhận OTP Tự Động** đã sẵn sàng."
    
    if is_admin:
        text += "\n\n👑 *[ADMIN MẸO]:* Sử dụng các nút quản trị bên dưới để theo dõi hệ thống."
        markup = get_admin_markup(message.chat.id)
    else:
        markup = get_user_markup(message.chat.id)
        
    bot.reply_to(message, text, parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(commands=['menu', 'danhsach'])
def menu_command(message):
    uid = message.from_user.id
    ok, msg = check_user_status(uid, message.from_user.first_name)
    if not ok:
        bot.reply_to(message, msg, parse_mode="HTML")
        return
    show_countries_menu(message.chat.id, message.id)

def show_countries_menu(chat_id, message_id=None):
    countries = get_available_countries()
    markup = InlineKeyboardMarkup()
    
    if countries:
        for code, name in countries.items():
            markup.add(InlineKeyboardButton(name, callback_data=f"country_{code}_0"))
        text = "🌍 <b>CHỌN VÙNG QUỐC GIA TRÊN TOÀN CẦU:</b>"
    else:
        text = "⚠️ **Lô hiện tại đã hết số khả dụng!** Vui lòng đổi lô mới hoặc reset."
        
    markup.add(InlineKeyboardButton("🔙 Quay lại Menu chính", callback_data="main_menu"))
    
    if message_id:
        try:
            bot.edit_message_text(text, chat_id, message_id, parse_mode="HTML", reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)

def show_numbers_by_country(chat_id, country_code, page=0, message_id=None):
    numbers, total = get_numbers_by_category(country_code, page, limit=6)
    markup = InlineKeyboardMarkup()
    
    if numbers:
        for num in numbers:
            markup.add(InlineKeyboardButton(f"📞 {num}", callback_data=f"select_{num}"))
        text = f"📋 <b>KHO SỐ (Trang {page+1} / Tổng {total} số):</b>\n<i>Chọn số để hệ thống theo dõi nhận mã xác thực:</i>"
        
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Trang trước", callback_data=f"country_{country_code}_{page-1}"))
        if (page + 1) * 6 < total:
            nav_buttons.append(InlineKeyboardButton("Trang sau ➡️", callback_data=f"country_{country_code}_{page+1}"))
        if nav_buttons:
            markup.row(*nav_buttons)
    else:
        text = "⚠️ Không tìm thấy số nào trong vùng này."
        
    markup.add(InlineKeyboardButton("🌍 Chọn quốc gia khác", callback_data="open_countries"))
    markup.add(InlineKeyboardButton("🔙 Quay lại Menu chính", callback_data="main_menu"))
    
    if message_id:
        try:
            bot.edit_message_text(text, chat_id, message_id, parse_mode="HTML", reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)

@bot.message_handler(commands=['admin', 'lenhadmin', 'helpadmin'])
def admin_help_command(message):
    uid = message.from_user.id
    ok, msg = check_user_status(uid, message.from_user.first_name)
    if not ok:
        bot.reply_to(message, msg, parse_mode="HTML")
        return
    if uid != ADMIN_ID:
        bot.reply_to(message, "⚠️ Bạn không có quyền sử dụng lệnh này!")
        return
    
    admin_text = f"👑 <b>BẢNG ĐIỀU KHIỂN ADMIN</b> 👑"
    markup = get_admin_markup(message.chat.id)
    bot.reply_to(message, admin_text, parse_mode="HTML", reply_markup=markup)

@bot.message_handler(commands=['sync', 'dongbo'])
def sync_command(message):
    uid = message.from_user.id
    ok, msg = check_user_status(uid, message.from_user.first_name)
    if not ok:
        bot.reply_to(message, msg, parse_mode="HTML")
        return
    if uid != ADMIN_ID:
        bot.reply_to(message, "⛔ Bạn không có quyền sử dụng lệnh này!")
        return
    
    bot.reply_to(message, "🔄 Đang chuyển sang lô 100 số tiếp theo...")
    success, count_or_err = load_text_batch(reset=False)
    if success:
        bot.send_message(message.chat.id, f"✅ **Đổi lô thành công!** Đã nạp <code>{count_or_err}</code> số mới.", parse_mode="HTML")
    else:
        bot.send_message(message.chat.id, f"❌ Lỗi đổi lô: {count_or_err}")

@bot.message_handler(commands=['resetfile'])
def reset_file_command(message):
    uid = message.from_user.id
    ok, msg = check_user_status(uid, message.from_user.first_name)
    if not ok:
        bot.reply_to(message, msg, parse_mode="HTML")
        return
    if uid != ADMIN_ID:
        bot.reply_to(message, "⛔ Bạn không có quyền sử dụng lệnh này!")
        return
    
    success, count_or_err = load_text_batch(reset=True)
    if success:
        bot.reply_to(message, f"⏪ **Đã reset kho số thành công!** Đã nạp lại <code>{count_or_err}</code> số đầu tiên.", parse_mode="HTML")
    else:
        bot.reply_to(message, f"❌ Lỗi reset: {count_or_err}")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    user_id = call.from_user.id
    user_name = call.from_user.first_name or "Ẩn danh"
    is_admin = (user_id == ADMIN_ID)
    
    ok, msg = check_user_status(user_id, user_name)
    if not ok:
        try:
            bot.answer_callback_query(call.id, "⛔ Tài khoản của bạn đang bị khóa!", show_alert=True)
            bot.send_message(chat_id, msg, parse_mode="HTML")
        except:
            pass
        return

    if call.data.startswith("copy_"):
        code = call.data.split("_")[1]
        bot.answer_callback_query(call.id, f"Đã copy mã: {code}", show_alert=True)
        
    elif call.data == "main_menu":
        bot.answer_callback_query(call.id, "Đã về Menu chính")
        phone = USER_ACTIVE_PHONES.get(chat_id, "Chưa chọn số")
        text = f"🤖 <b>MENU CHÍNH QUẢN LÝ XÁC THỰC</b>\n📱 Số bạn đang dùng: <code>{phone}</code>\n<i>(Hệ thống đang tự động lắng nghe mã...)</i>"
        markup = get_admin_markup(chat_id) if is_admin else get_user_markup(chat_id)
        try:
            bot.edit_message_text(text, chat_id, message_id, parse_mode="HTML", reply_markup=markup)
        except Exception:
            bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)

    elif call.data == "open_countries":
        bot.answer_callback_query(call.id, "Đang tải danh sách quốc gia...")
        show_countries_menu(chat_id, message_id)

    elif call.data.startswith("country_"):
        parts = call.data.split("_", 2)
        country_code = parts[1]
        page = int(parts[2])
        bot.answer_callback_query(call.id, f"Đang tải kho số...")
        show_numbers_by_country(chat_id, country_code, page, message_id)
            
    elif call.data == "open_leaderboard":
        bot.answer_callback_query(call.id, "Đang tải bảng xếp hạng...")
        stats = load_json_db(STATS_FILE)
        sorted_stats = sorted(stats.values(), key=lambda x: x['count'], reverse=True)[:10]
        
        text = "🏆 <b>BẢNG XẾP HẠNG THÀNH VIÊN</b> 🏆\n-----------------------------------\n"
        if sorted_stats:
            for idx, item in enumerate(sorted_stats, 1):
                medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"<b>{idx}.</b>"
                text += f"{medal} 👤 <b>{item['name']}</b> ➔ <b>{item['count']}</b> mã\n"
        else:
            text += "Chưa có dữ liệu xếp hạng."
            
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Quay lại Menu chính", callback_data="main_menu"))
        try:
            bot.edit_message_text(text, chat_id, message_id, parse_mode="HTML", reply_markup=markup)
        except Exception:
            bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)

    elif call.data == "admin_working_nums":
        if not is_admin:
            bot.answer_callback_query(call.id, "⛔ Bạn không có quyền!", show_alert=True)
            return
        bot.answer_callback_query(call.id, "Đang tải chi tiết số hoạt động...")
        
        total_working = len(OTP_ACTIVE_SESSIONS)
        text = f"📋 <b>CHI TIẾT SỐ HOẠT ĐỘNG TỐT (Tổng: {total_working} số):</b>\n<i>(Bấm vào số điện thoại dạng <code>code</code> để copy làm việc ngay)</i>\n-----------------------------------\n"
        if OTP_ACTIVE_SESSIONS:
            for idx, (phone, info) in enumerate(list(OTP_ACTIVE_SESSIONS.items())[-20:], 1):
                remaining_mins = max(0, int((info['expire'] - time.time()) / 60))
                text += f"<b>{idx}.</b> 📱 <code>{phone}</code>\n   🔑 Mã OTP: <b>{info['otp']}</b>\n   🕒 Nhận lúc: {info['time']} (Còn {remaining_mins}p hiệu lực)\n-----------------------------------\n"
        else:
            text += "Chưa có số điện thoại nào hoạt động nhận OTP."

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Quay lại Menu chính", callback_data="main_menu"))
        try:
            bot.edit_message_text(text, chat_id, message_id, parse_mode="HTML", reply_markup=markup)
        except Exception:
            bot.send_message(text, chat_id, message_id, parse_mode="HTML", reply_markup=markup)

    elif call.data == "admin_banned_list":
        if not is_admin:
            bot.answer_callback_query(call.id, "⛔ Bạn không có quyền!", show_alert=True)
            return
        bot.answer_callback_query(call.id, "Đang tải danh sách user vi phạm...")
        
        spam_users = load_json_db(SPAM_TRACKER_FILE)
        text = f"🛡️ <b>QUẢN LÝ KHÓA / MỞ KHÓA USER (Tổng: {len(spam_users)} người):</b>\n-----------------------------------\n"
        
        markup = InlineKeyboardMarkup()
        if spam_users:
            now = time.time()
            for uid, info in list(spam_users.items())[-10:]:
                ban_until = info.get('ban_until', 0)
                status_str = "🔒 Vĩnh viễn" if ban_until == 0 else f"⏳ Còn lại {max(0, int((ban_until - now)/60))} phút"
                text += f"🆔 <code>{uid}</code> | 👤 <b>{info.get('name', 'Ẩn danh')}</b>\n   Trạng thái: <b>{status_str}</b>\n-----------------------------------\n"
                markup.add(InlineKeyboardButton(f"🔓 Mở Khóa ID: {uid}", callback_data=f"unban_{uid}"))
        else:
            text += "Hiện tại không có user nào bị ghi nhận khóa."

        markup.add(InlineKeyboardButton("🔙 Quay lại Menu chính", callback_data="main_menu"))
        try:
            bot.edit_message_text(text, chat_id, message_id, parse_mode="HTML", reply_markup=markup)
        except Exception:
            bot.send_message(text, chat_id, message_id, parse_mode="HTML", reply_markup=markup)

    elif call.data.startswith("unban_"):
        if not is_admin:
            bot.answer_callback_query(call.id, "⛔ Bạn không có quyền!", show_alert=True)
            return
        target_uid = call.data.replace("unban_", "")
        if unban_user_manual(target_uid):
            bot.answer_callback_query(call.id, f"✅ Đã mở khóa thành công cho ID: {target_uid}", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "⚠️ Không tìm thấy user này!", show_alert=True)
            
        spam_users = load_json_db(SPAM_TRACKER_FILE)
        text = f"🛡️ <b>QUẢN LÝ KHÓA / MỞ KHÓA USER (Tổng: {len(spam_users)} người):</b>\n-----------------------------------\n"
        markup = InlineKeyboardMarkup()
        if spam_users:
            now = time.time()
            for uid, info in list(spam_users.items())[-10:]:
                ban_until = info.get('ban_until', 0)
                status_str = "🔒 Vĩnh viễn" if ban_until == 0 else f"⏳ Còn lại {max(0, int((ban_until - now)/60))} phút"
                text += f"🆔 <code>{uid}</code> | 👤 <b>{info.get('name', 'Ẩn danh')}</b>\n   Trạng thái: <b>{status_str}</b>\n-----------------------------------\n"
                markup.add(InlineKeyboardButton(f"🔓 Mở Khóa ID: {uid}", callback_data=f"unban_{uid}"))
        else:
            text += "Hiện tại không có user nào bị ghi nhận khóa."
        markup.add(InlineKeyboardButton("🔙 Quay lại Menu chính", callback_data="main_menu"))
        try:
            bot.edit_message_text(text, chat_id, message_id, parse_mode="HTML", reply_markup=markup)
        except Exception:
            bot.send_message(text, chat_id, message_id, parse_mode="HTML", reply_markup=markup)

    elif call.data == "admin_stats":
        if not is_admin:
            bot.answer_callback_query(call.id, "⛔ Bạn không có quyền!", show_alert=True)
            return
        bot.answer_callback_query(call.id, "Đang lấy dữ liệu thống kê...")
        
        total_working = len(OTP_ACTIVE_SESSIONS)
        total_banned = len(load_json_db(SPAM_TRACKER_FILE))
        stats_text = "📊 <b>THỐNG KÊ HỆ THỐNG</b> 📊\n-----------------------------------\n"
        stats_text += f"📂 <b>Vị trí con trỏ đọc file:</b> dòng thứ <code>{CURRENT_FILE_POSITION}</code>\n"
        stats_text += f"📞 <b>Tổng số số đã hoạt động (Sống):</b> {total_working}\n"
        stats_text += f"🛡️ <b>Số user đang trong danh sách khóa:</b> {total_banned}\n"
        stats_text += "🌐 <b>Trạng thái hệ thống:</b> ✅ Hoạt động ổn định (Render Server)\n"

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Quay lại Menu chính", callback_data="main_menu"))
        try:
            bot.edit_message_text(stats_text, chat_id, message_id, parse_mode="HTML", reply_markup=markup)
        except Exception:
            bot.send_message(stats_text, chat_id, message_id, parse_mode="HTML", reply_markup=markup)

    elif call.data == "admin_users":
        if not is_admin:
            bot.answer_callback_query(call.id, "⛔ Bạn không có quyền!", show_alert=True)
            return
        bot.answer_callback_query(call.id, "Đang tải danh sách user...")
        users = load_json_db(USERS_FILE)
        text = f"👥 <b>DANH SÁCH THÀNH VIÊN ({len(users)} người):</b>\n-----------------------------------\n"
        
        recent_users = list(users.values())[-15:]
        for u in recent_users:
            text += f"🆔 <code>{u['id']}</code> | 👤 <b>{u['name']}</b> (@{u['username']})\n🕒 <i>Thời gian: {u['joined_at']}</i>\n-----------------------------------\n"
            
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Quay lại Menu chính", callback_data="main_menu"))
        try:
            bot.edit_message_text(text, chat_id, message_id, parse_mode="HTML", reply_markup=markup)
        except Exception:
            bot.send_message(text, chat_id, text, message_id, parse_mode="HTML", reply_markup=markup)

    elif call.data == "admin_sync":
        if not is_admin:
            bot.answer_callback_query(call.id, "⛔ Bạn không có quyền!", show_alert=True)
            return
        bot.answer_callback_query(call.id, "Đang chuyển lô số mới...")
        success, count_or_err = load_text_batch(reset=False)
        if success:
            text = f"✅ <b>Đổi lô thành công!</b> Đã nạp <code>{count_or_err}</code> số mới."
        else:
            text = f"❌ <b>Lỗi đổi lô:</b> {count_or_err}"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Quay lại Menu chính", callback_data="main_menu"))
        try:
            bot.edit_message_text(text, chat_id, message_id, parse_mode="HTML", reply_markup=markup)
        except Exception:
            bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)

    elif call.data == "admin_reset":
        if not is_admin:
            bot.answer_callback_query(call.id, "⛔ Bạn không có quyền!", show_alert=True)
            return
        bot.answer_callback_query(call.id, "Đang reset kho...")
        success, count_or_err = load_text_batch(reset=True)
        if success:
            text = f"⏪ <b>Reset thành công!</b> Đã nạp lại <code>{count_or_err}</code> số đầu tiên."
        else:
            text = f"❌ <b>Lỗi reset:</b> {count_or_err}"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Quay lại Menu chính", callback_data="main_menu"))
        try:
            bot.edit_message_text(text, chat_id, message_id, parse_mode="HTML", reply_markup=markup)
        except Exception:
            bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)
            
    elif call.data.startswith("select_"):
        selected_phone = call.data.replace("select_", "")
        USER_ACTIVE_PHONES[chat_id] = selected_phone
        
        bot.answer_callback_query(call.id, f"Đã chọn: {selected_phone}", show_alert=True)
        text = (
            f"✅ <b>Đã chọn số thành công:</b> <code>{selected_phone}</code>\n\n"
            "🎯 **Hệ thống Auto-Push đã bật:** Cứ có mã xác thực gửi đến số này, hệ thống sẽ tự động bắt, kích hoạt hiệu lực 5 phút và tự động thu hồi vĩnh viễn!"
        )
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔄 Kiểm tra thủ công", callback_data="check_active"))
        markup.add(InlineKeyboardButton("🌍 Chọn quốc gia khác", callback_data="open_countries"))
        markup.add(InlineKeyboardButton("🔙 Quay lại Menu chính", callback_data="main_menu"))
        try:
            bot.edit_message_text(text, chat_id, message_id, parse_mode="HTML", reply_markup=markup)
        except Exception:
            bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)
        
    elif call.data == "check_active":
        bot.answer_callback_query(call.id, "Đang quét tìm mã xác thực...")
        current_phone = USER_ACTIVE_PHONES.get(chat_id, "")
        if not current_phone:
            bot.answer_callback_query(call.id, "Bạn chưa chọn số nào!", show_alert=True)
            return
        try:
            otps_data = fetch_and_parse_otps()
            found = False
            for item in otps_data:
                if item['phone'] == current_phone:
                    send_auto_otp(chat_id, current_phone, item['otp'], item['raw_text'], user_id, user_name)
                    found = True
                    break
            if not found:
                bot.answer_callback_query(call.id, "Chưa có tin nhắn mới cho số này!", show_alert=True)
        except Exception:
            bot.answer_callback_query(call.id, "Lỗi kết nối kiểm tra!", show_alert=True)

# 🚀 KHỞI CHẠY CÁC LUỒNG NGẦM & WEB SERVER
threading.Thread(target=run_web, daemon=True).start()
threading.Thread(target=ensure_scanner_running, daemon=True).start()

print("🚀 Bot Kho Số Toàn Cầu đang chạy trên Render (Không Proxy)...")
bot.infinity_polling(timeout=20, long_polling_timeout=10)
