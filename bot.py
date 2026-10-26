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
import random
import websocket  # Thư viện yêu cầu: pip install websocket-client
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

try:
    bot.remove_webhook()
except Exception as e:
    print(f"Xử lý Webhook: {e}")

# ==========================================
# ⚙️ 3. QUẢN LÝ DỮ LIỆU & CẤU HÌNH TÀI CHÍNH
# ==========================================
session = requests.Session()
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest'
}

USER_ACTIVE_PHONES = {}      # {chat_id: {"phone": phone_num, "expire": time_luyen_tap, "code": country_code, "msg_id": message_id}}
OTP_ACTIVE_SESSIONS = {}     # Các số đang chờ SMS hoặc đã có OTP
PHONE_CREATION_TIME = {}     # {phone: timestamp}
LAST_SEEN_OTPS = {}          
COUNTRY_CACHE = {}           
CURRENT_FILE_POSITION = 0    
USER_WITHDRAW_STATE = {}     
USER_PENDING_WALLET = {}     
USER_WSS_STATE = {}          

USERS_FILE = "users_log.json"
STATS_FILE = "otp_stats.json"
SPAM_TRACKER_FILE = "spam_tracker.json"
SETTINGS_FILE = "settings.json"
WITHDRAW_HISTORY_FILE = "withdraw_history.json"
USER_LAST_ACTION = {}        

DEFAULT_SETTINGS = {
    "min_withdraw": 5.0,        
    "max_withdraw": 100.0,
    "otp_reward": 0.009,        
    "refer_bonus": 0.01,
    "ivas_ws_url": "",        
}

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        save_json_db(SETTINGS_FILE, DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS
    s = load_json_db(SETTINGS_FILE)
    if "ivas_ws_url" not in s:
        s["ivas_ws_url"] = ""
        save_json_db(SETTINGS_FILE, s)
    return s

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

# Dán nguyên đoạn Cookie mới nhất của bro vào đây:
IVAS_USER_COOKIE = (
    "_fbp=fb.1.1792741985965.809745508754196298; "
    "cf_clearance=oeZZoXwByuCZVg6ldEh_aNnpLXzJVIWj.mmmm.ZdF7o-1792981612-1.2.1.1-3XyzKxYQeb7R3C15mmachgcwp1zrSyh4BTzdZ1O8Zt0PhR757heOaUZuPwtx5pwMj6LFQZhYKynCTVd1by5zgmfKFcMO4ASiwEPLKSRz9Fsj1UzowStsSekVo1omnzZDHD4ZmzfmfcaPvIGDSmbyzK3vhby5vq1hvpDO3_WUyUPtH9RO0T_.geWSfGHlFbZhIjXpUNxXVfavgc7U0PvFJVqaKzIHSIh7x9byMCEdk4C1PgvV9XT5FTc.8PUbUHcjnsP7XYoZamnBl0D7dVJaf771a2170Y8X2b8CCVPYkFCVqEIQV6USKtKyCG39bwdybCZL_D7c3n1jz_gK9pYdgKVLwhalt3dHe9QmZ2qKcJBcyPodBVZrMlWMeytkINihAgaire0QWFCdqO8IXyJQrs_svDEMUSclfnyE9sv.YW_puTvfwyDduJUaTodWvgS.TOYs5HzbiTzZNdmv0MSu2Ws31bD9Le9Ax_Uzpn7XI7cIb_wqNQxLxRYFihX2U46h9pdZd1E1jX16E5D_OUC.lg; "
    "XSRF-TOKEN=eyJpdiI6IkE1RWJGWEI3RngwTHFBRFBqSnkwYXc9PSIsInZhbHVlIjoiOEVTd0pMcDY5VmxKc1RkSllhSmZNYU5VVnJpd05LMExtcUN5YU5aeGVqRHB4REk1MHprelBDeHd0cWMxNzNEeXlRNDdpeXFNNUl2UExKMDA3WkdGR1FFNDZmNFdXRXE2T1E3a0h4ZEJVWWlwdGhrcVFBcno4NmJ3K3Q0eUh4ZFYiLCJtYWMiOiI0YmQwNzJmMDVmYzdjNzkwMjNjYzBkYmI1YWU1NzI0YzQxNTI2MjE5OTdiYWY0ZjVmN2QzOGQyNmEyNzRkNTYzIiwidGFnIjoiIn0=; "
    "ivas_sms_session=eyJpdiI6InF3cFNvZ0FVbG5wVDhSeHg4NXhUb3c9PSIsInZhbHVlIjoilklVWkozZGhaM3FLOFVqQy9Kdm1EQlhTVWhvZHJJN09iM2JiZUtIUEJxVkpmOWF3RkRKY0pGbUFqUHc4dFF6ZzJ1Y25HbmdwVWFZL1RGblBsanhrTlZ1QjdqQVBCdXpscDNOeUI2d2V3N3kySWwxYWpjTk56dTMzSHhCbmpTNFkiLCJtYWMiOiJmMDNjMGJjMjE5NDdmYTBlZjdiMGQ5N2YwODMyNzk4ZGMzNWU2MTFmOGVhOTM3OWYyN2MzMDViZWIxNGNhMjk0IiwidGFnIjoiIn0="
)

def sync_numbers_from_ivas_web():
    """Tự động cào danh sách số điện thoại từ trang portal iVASMS thay cho numbers.txt thủ công"""
    global COUNTRY_CACHE
    headers_sync = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Cookie': IVAS_USER_COOKIE
    }
    try:
        response = requests.get(IVAS_WEB_URL, headers=headers_sync, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            scraped_numbers = set()
            
            # Quét toàn bộ các đoạn text hoặc bảng có chứa số điện thoại dạng định dạng quốc tế
            for text_elem in soup.find_all(text=True):
                found_nums = re.findall(r'\+?\d{8,15}', text_elem)
                for num in found_nums:
                    digits_only = re.sub(r'\D', '', num)
                    if len(digits_only) >= 8:
                        formatted = "+" + digits_only
                        scraped_numbers.add(formatted)
            
            if scraped_numbers:
                temp_cache = {}
                for formatted in scraped_numbers:
                    if formatted not in PHONE_CREATION_TIME:
                        PHONE_CREATION_TIME[formatted] = time.time()
                    
                    name, code = get_country_info(formatted)
                    if code not in temp_cache:
                        temp_cache[code] = {"name": name, "numbers": []}
                    if formatted not in temp_cache[code]["numbers"]:
                        temp_cache[code]["numbers"].append(formatted)
                
                COUNTRY_CACHE = temp_cache
                print(f"[Auto-Sync]: Đã đồng bộ thành công {len(scraped_numbers)} số từ iVASMS Web!")
                return True, len(scraped_numbers)
        print(f"[Auto-Sync]: Không thể lấy dữ liệu, mã phản hồi: {response.status_code}")
        return False, f"HTTP Status {response.status_code}"
    except Exception as e:
        print(f"[Auto-Sync Error]: {e}")
        return False, str(e)

# ==========================================
# 🗑️ HÀM XÓA HẲN SỐ KHI DÙNG XONG
# ==========================================
def remove_number_from_file(target_phone):
    # Đồng thời hỗ trợ xóa khỏi file numbers.txt (nếu có tồn tại)
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
    else:
        get_user(uid)
        return update_balance(uid, amount)

def mask_phone_number(phone):
    p = phone.strip()
    if len(p) > 6:
        return p[:4] + "***" + p[-2:]
    return p

# ==========================================
# 🛡️ 5. HỆ THỐNG CHỐNG SPAM & UNBAN
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
            ban_until = now + 300  
            msg = "⚠️ <b>Cảnh cáo Spam lần 1:</b> Bạn thao tác quá nhanh nên đã bị tạm khóa <b>5 phút</b>."
        elif count == 2:
            ban_until = now + 1800 
            msg = "⚠️ <b>Cảnh cáo Spam lần 2:</b> Nâng mức phạt tạm khóa <b>30 phút</b>."
        else:
            ban_until = 0          
            msg = "⛔ <b>Khóa vĩnh viễn (Lần 3):</b> Tài khoản đã bị khóa vĩnh viễn do spam liên tục!"
            
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
    "265": ("🇲🇼 Malawi (+265)", "MW"), "239": ("🇸🇹 São Tomé & Príncipe (+239)", "ST"),
    "240": ("🇬🇶 Guinea Xích Đạo (+240)", "GQ"), "236": ("🇨🇫 CH Trung Phi (+236)", "CF"),
    "222": ("🇲🇷 Mauritania (+222)", "MR"), "211": ("🇸🇸 Nam Sudan (+211)", "SS"),
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

# ==========================================
# 📢 7. HÀM BROADCAST THÔNG BÁO (KHÔNG GẮN NÚT)
# ==========================================
def broadcast_stock_updated(added_count, total_stock):
    text = (
        "✅ <b>Stock Updated!</b>\n"
        "__________________________________\n\n"
        "🌐 <b>Country:</b> GLOBAL / ALL COUNTRY 🌍\n"
        f"⏩ <b>Added:</b> {added_count}\n"
        f"📊 <b>Total Stock:</b> {total_stock}\n"
        "👤 <b>Uploaded by:</b> A D M I N\n"
        "__________________________________\n\n"
        "💡 <i>Vui lòng vào bot riêng để chọn quốc gia và lấy số nhận mã OTP tự động!</i>"
    )
    try:
        bot.send_message(GROUP_CHAT_ID, text, parse_mode="HTML")
    except Exception:
        pass

# ==========================================
# 🧹 8. TỰ ĐỘNG XÓA HẲN SỐ & AN TOÀN TUYỆT ĐỐI
# ==========================================
def clean_expired_sessions():
    try:
        now = time.time()
        expired_phones = []
        for phone, create_time in list(PHONE_CREATION_TIME.items()):
            if now - create_time > 900:
                expired_phones.append(phone)

        for phone in expired_phones:
            remove_number_from_file(phone)
            if phone in PHONE_CREATION_TIME:
                del PHONE_CREATION_TIME[phone]
            if phone in OTP_ACTIVE_SESSIONS:
                del OTP_ACTIVE_SESSIONS[phone]
            
            for cid, info in list(USER_ACTIVE_PHONES.items()):
                if info.get("phone") == phone:
                    msg_id = info.get("msg_id")
                    del USER_ACTIVE_PHONES[cid]
                    try:
                        if msg_id:
                            bot.edit_message_text(
                                f"⏰ <b>SỐ ĐIỆN THOẠI <code>{phone}</code> ĐÃ HẾT HẠN!</b>\n"
                                "Số này đã quá thời hạn 15 phút tồn tại và bị xóa vĩnh viễn khỏi hệ thống.",
                                cid, msg_id, parse_mode="HTML", reply_markup=None
                            )
                    except Exception:
                        pass

        expired_otps = []
        for phone, info in list(OTP_ACTIVE_SESSIONS.items()):
            if now > info.get("expire", 0):
                expired_otps.append(phone)
                
        for p in expired_otps:
            remove_number_from_file(p)
            if p in PHONE_CREATION_TIME:
                del PHONE_CREATION_TIME[p]
            if p in OTP_ACTIVE_SESSIONS:
                del OTP_ACTIVE_SESSIONS[p]
            for cid, active_info in list(USER_ACTIVE_PHONES.items()):
                if active_info.get("phone") == p:
                    msg_id = active_info.get("msg_id")
                    del USER_ACTIVE_PHONES[cid]
                    try:
                        if msg_id:
                            bot.edit_message_text(
                                f"✅ <b>SỐ ĐIỆN THOẠI <code>{p}</code> ĐÃ HOÀN TẤT NHẬN OTP!</b>",
                                cid, msg_id, parse_mode="HTML", reply_markup=None
                            )
                    except Exception:
                        pass
    except Exception as e:
        print(f"Lỗi trong clean_expired_sessions: {e}")

def load_text_batch(reset=False):
    # Thay thế phần load file cũ bằng việc gọi hàm Auto-Sync trực tiếp từ web iVASMS
    clean_expired_sessions()
    success, count_or_msg = sync_numbers_from_ivas_web()
    if success:
        return True, count_or_msg
    else:
        # Nếu gọi web lỗi, dự phòng đọc file local numbers.txt nếu có
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
        return False, str(count_or_msg)

# Khởi chạy nạp stock lần đầu
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
        all_nums = [n for n in COUNTRY_CACHE[category_code]["numbers"] if not is_phone_busy(n)]
        start = page * limit
        end = start + limit
        return all_nums[start:end], len(all_nums)
    return [], 0

def get_available_countries():
    clean_expired_sessions()
    valid_countries = {}
    for code, data in COUNTRY_CACHE.items():
        active_nums = [n for n in data["numbers"] if not is_phone_busy(n)]
        if active_nums:
            valid_countries[code] = f"{data['name']} — [{len(active_nums)} Số]"
    return valid_countries

# ==========================================
# ⚡ 9. GỬI OTP, CỘNG THƯỞNG & XÓA SỐ VĨNH VIỄN KHI HOÀN TẤT
# ==========================================
def send_auto_otp(chat_id, number, otp_code, full_msg="", user_id=None, user_name=None, msg_id=None):
    try:
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

        remove_number_from_file(number)
        if number in PHONE_CREATION_TIME:
            del PHONE_CREATION_TIME[number]
        if number in OTP_ACTIVE_SESSIONS:
            del OTP_ACTIVE_SESSIONS[number]
        for cid, info in list(USER_ACTIVE_PHONES.items()):
            if info.get("phone") == number:
                del USER_ACTIVE_PHONES[cid]

        if msg_id:
            try:
                bot.edit_message_reply_markup(chat_id, msg_id, reply_markup=None)
            except Exception:
                pass

        text = (
            "⚡️ <b>HỆ THỐNG XÁC THỰC TỰ ĐỘNG</b> ⚡️\n"
            "-----------------------------------\n"
            f"📞 <b>Số điện thoại:</b> <code>{number}</code>\n"
            f"🔑 <b>Mã OTP:</b> <code>{otp_code}</code>\n"
            f"💰 <b>Thưởng nhận OTP:</b> +<code>${reward:.3f}</code>\n"
        )
        if full_msg:
            text += f"💬 <b>Nội dung:</b> <i>{full_msg[:100]}</i>\n"
        text += "\n⏳ <b>Trạng thái:</b> <i>Đã nhận OTP thành công, cộng tiền vào ví và số này đã tự động xóa vĩnh viễn khỏi hệ thống!</i>"

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(f"📋 COPY OTP • {otp_code}", callback_data=f"copy_{otp_code}"))
        bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)
    except Exception as e:
        print(f"Lỗi gửi OTP tới {chat_id}: {e}")

def process_incoming_sms_content(text_content):
    try:
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
                            target_msg_id = None
                            for cid, info in USER_ACTIVE_PHONES.items():
                                if info.get("phone") == phone:
                                    target_cid = cid
                                    target_msg_id = info.get("msg_id")
                                    break
                            if target_cid:
                                user_info = get_user(target_cid)
                                send_auto_otp(target_cid, phone, otp, text_content, user_id=target_cid, user_name=user_info.get("name"), msg_id=target_msg_id)
    except Exception as e:
        print(f"Lỗi process_incoming_sms_content: {e}")

def fetch_and_parse_otps():
    clean_expired_sessions()
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
                    process_incoming_sms_content(text_content)
        except Exception as e:
            print(f"Lỗi quét SMS từ {url}: {e}")

def background_sms_scanner():
    while True:
        try:
            fetch_and_parse_otps()
        except Exception as e:
            print(f"Lỗi background scanner: {e}")
        time.sleep(3)

# ==========================================
# 🔗 9.1. LUỒNG NGẦM WEBSOCKET (WSS LISTENER)
# ==========================================
def ivas_websocket_listener():
    while True:
        try:
            settings = load_settings()
            ws_url = settings.get("ivas_ws_url", "").strip()
            if not ws_url:
                time.sleep(5)
                continue
                
            def on_message(ws, message):
                try:
                    print(f"[WSS Real-time Received]: {message}")
                    process_incoming_sms_content(str(message))
                except Exception as e:
                    print(f"Lỗi xử lý message từ WebSocket: {e}")

            def on_error(ws, error):
                print(f"Lỗi kết nối WebSocket: {error}")

            def on_close(ws, close_status_code, close_msg):
                print("Kết nối WebSocket đã đóng, đang thử kết nối lại sau 5 giây...")

            def on_open(ws):
                print("✅ Đã kết nối thành công tới WebSocket iVASMS real-time!")

            ws = websocket.WebSocketApp(
                ws_url,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            ws.run_forever(ping_interval=30, ping_timeout=10)
        except Exception as e:
            print(f"Ngoại lệ luồng WebSocket: {e}")
        time.sleep(5)

# ==========================================
# 🛠️ 10. CÁC LỆNH ADMIN
# ==========================================
@bot.message_handler(commands=['adminhelp'])
def cmd_admin_help(message):
    if message.from_user.id != ADMIN_ID:
        return
    help_text = (
        "👑 <b>BẢNG LỆNH ADMIN</b>\n"
        "-----------------------------------\n"
        "💰 <b>/addmoney [số tiền]</b>\n"
        "✏️ <b>/setbal [ID_User] [số tiền]</b>\n"
        "🔍 <b>/userinfo [ID_User]</b>"
    )
    bot.send_message(message.chat.id, help_text, parse_mode="HTML")

@bot.message_handler(commands=['addmoney'])
def cmd_admin_add_money(message):
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split()
    target_uid = ADMIN_ID
    amount = 10.0
    try:
        if len(args) == 2:
            amount = float(args[1])
        elif len(args) >= 3:
            target_uid = int(args[1])
            amount = float(args[2])
        new_bal = update_balance(target_uid, amount)
        bot.send_message(message.chat.id, f"✅ Đã cộng <code>${amount:.4f}</code> cho ID <code>{target_uid}</code>. Số dư mới: <code>${new_bal:.4f}</code>", parse_mode="HTML")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Lỗi: {e}")

@bot.message_handler(commands=['setbal'])
def cmd_admin_set_balance(message):
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split()
    try:
        if len(args) < 3:
            return
        target_uid = str(args[1])
        amount = float(args[2])
        users = load_json_db(USERS_FILE)
        if target_uid in users:
            users[target_uid]["balance"] = round(amount, 4)
            save_json_db(USERS_FILE, users)
            bot.send_message(message.chat.id, f"✅ Đã đặt lại số dư ID <code>{target_uid}</code> thành <code>${amount:.4f}</code>", parse_mode="HTML")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Lỗi: {e}")

@bot.message_handler(commands=['userinfo'])
def cmd_admin_user_info(message):
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split()
    try:
        target_uid = str(args[1]) if len(args) >= 2 else str(message.from_user.id)
        users = load_json_db(USERS_FILE)
        if target_uid in users:
            u = users[target_uid]
            text = (
                f"📌 <b>Tên:</b> {u.get('name')}\n"
                f"🆔 <b>ID:</b> <code>{u.get('id')}</code>\n"
                f"💵 <b>Số dư:</b> <code>${u.get('balance', 0.0):.4f}</code>\n"
                f"📅 <b>Đăng ký:</b> {u.get('joined_at')}"
            )
            bot.send_message(message.chat.id, text, parse_mode="HTML")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Lỗi: {e}")

# ==========================================
# 📲 11. LỆNH /START & GIAO DIỆN CHÍNH
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
        "⏳ Mỗi số có tổng thời hạn tối đa 15 phút tồn tại trên hệ thống."
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
# 🔄 12. XỬ LÝ SỰ KIỆN CALLBACK QUERY
# ==========================================
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
                bot.answer_callback_query(call.id, f"Bạn đang giữ số {curr_p}. Vui lòng hoàn thành hoặc Đổi số mới!", show_alert=True)
                return

            countries = get_available_countries()
            if not countries:
                bot.answer_callback_query(call.id, "Kho số hiện tại đang trống hoặc đang cập nhật!", show_alert=True)
                return
                
            markup = InlineKeyboardMarkup(row_width=1)
            for code, label in countries.items():
                markup.add(InlineKeyboardButton(label, callback_data=f"country_{code}_0"))
            markup.add(InlineKeyboardButton("🔙 Quay lại", callback_data="back_home"))
            
            try:
                bot.edit_message_text("🌍 <b>Chọn Quốc Gia Cần Lấy Số:</b>", chat_id, msg_id, parse_mode="HTML", reply_markup=markup)
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
                bot.edit_message_text(f"📋 <b>Danh sách số sẵn sàng ({code}):</b>", chat_id, msg_id, parse_mode="HTML", reply_markup=markup)
            except Exception:
                pass

        elif data.startswith("getnum_"):
            parts = data.split("_")
            code = parts[1]
            phone = parts[3]

            if is_phone_busy(phone):
                bot.answer_callback_query(call.id, "❌ Số này vừa có người khác lấy mất rồi! Vui lòng chọn số khác.", show_alert=True)
                return
            
            if chat_id in USER_ACTIVE_PHONES:
                del USER_ACTIVE_PHONES[chat_id]

            if phone not in PHONE_CREATION_TIME:
                PHONE_CREATION_TIME[phone] = time.time()

            elapsed = time.time() - PHONE_CREATION_TIME[phone]
            remaining_time = 900 - elapsed
            if remaining_time <= 0:
                remove_number_from_file(phone)
                bot.answer_callback_query(call.id, "⚠️ Số này đã hết thời hạn 15 phút tồn tại!", show_alert=True)
                return

            expire_time = time.time() + remaining_time
            USER_ACTIVE_PHONES[chat_id] = {
                "phone": phone,
                "expire": expire_time,
                "code": code,
                "msg_id": msg_id
            }
            
            text = (
                "✅ <b>ĐÃ CẤP SỐ ĐỘC QUYỀN THÀNH CÔNG!</b>\n"
                "-----------------------------------\n"
                f"📞 <b>Số điện thoại:</b> <code>{phone}</code>\n"
                "💬 <b>Trạng thái:</b> Đang chờ mã OTP từ dịch vụ...\n"
                f"⏳ <i>Số này còn lại khoảng {int(remaining_time/60)} phút tổng thời gian sống. Nếu bạn hủy, số sẽ được trả về kho cho người khác lụm!</i>"
            )
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(InlineKeyboardButton("🔄 Kiểm tra tin nhắn ngay", callback_data=f"checksms_{phone}"))
            markup.add(InlineKeyboardButton("🔄 Đổi số mới ngay", callback_data=f"nextnum_{code}_{phone}"))
            markup.add(InlineKeyboardButton("❌ Hủy số / Về Menu", callback_data=f"cancelnum_{phone}"))
            
            try:
                bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)
                bot.answer_callback_query(call.id, "Đã lấy số thành công!", show_alert=False)
            except Exception:
                pass

        elif data.startswith("nextnum_"):
            parts = data.split("_")
            code = parts[1]
            old_phone = parts[2]

            if chat_id in USER_ACTIVE_PHONES:
                del USER_ACTIVE_PHONES[chat_id]
            if old_phone in OTP_ACTIVE_SESSIONS:
                del OTP_ACTIVE_SESSIONS[old_phone]

            available_nums, _ = get_numbers_by_category(code, page=0, limit=50)
            available_nums = [n for n in available_nums if n != old_phone]

            if not available_nums:
                bot.answer_callback_query(call.id, "⚠️ Đã hết số khác trong danh mục này rồi!", show_alert=True)
                call.data = "open_countries"
                handle_callbacks(call)
                return

            new_phone = random.choice(available_nums)

            if new_phone not in PHONE_CREATION_TIME:
                PHONE_CREATION_TIME[new_phone] = time.time()

            elapsed = time.time() - PHONE_CREATION_TIME[new_phone]
            remaining_time = 900 - elapsed
            if remaining_time <= 0:
                remove_number_from_file(new_phone)
                bot.answer_callback_query(call.id, "⚠️ Số này đã hết hạn!", show_alert=True)
                return

            expire_time = time.time() + remaining_time
            USER_ACTIVE_PHONES[chat_id] = {
                "phone": new_phone,
                "expire": expire_time,
                "code": code,
                "msg_id": msg_id
            }

            text = (
                "✅ <b>ĐÃ ĐỔI SỐ MỚI THÀNH CÔNG!</b>\n"
                "-----------------------------------\n"
                f"📞 <b>Số điện thoại mới:</b> <code>{new_phone}</code>\n"
                "💬 <b>Trạng thái:</b> Đang chờ mã OTP từ dịch vụ...\n"
                f"⏳ <i>Số này còn lại khoảng {int(remaining_time/60)} phút tổng thời gian sống.</i>"
            )
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(InlineKeyboardButton("🔄 Kiểm tra tin nhắn ngay", callback_data=f"checksms_{new_phone}"))
            markup.add(InlineKeyboardButton("🔄 Đổi số mới ngay", callback_data=f"nextnum_{code}_{new_phone}"))
            markup.add(InlineKeyboardButton("❌ Hủy số / Về Menu", callback_data=f"cancelnum_{new_phone}"))

            try:
                bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)
                bot.answer_callback_query(call.id, "Đã đổi sang số mới thành công!", show_alert=False)
            except Exception:
                pass

        elif data.startswith("cancelnum_"):
            phone = data.replace("cancelnum_", "")
            if chat_id in USER_ACTIVE_PHONES:
                del USER_ACTIVE_PHONES[chat_id]
            if phone in OTP_ACTIVE_SESSIONS:
                del OTP_ACTIVE_SESSIONS[phone]

            bot.answer_callback_query(call.id, "Đã hủy số và trả lại kho chung cho người khác.", show_alert=False)
            
            text = "👋 Bạn đã hủy số thành công. Số này đã được trả về kho chung. Chào mừng bạn quay lại menu chính!"
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
                bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)
            except Exception:
                pass

        elif data.startswith("checksms_"):
            phone = data.replace("checksms_", "")
            if phone in OTP_ACTIVE_SESSIONS and OTP_ACTIVE_SESSIONS[phone]["otp"] != "PENDING":
                info = OTP_ACTIVE_SESSIONS[phone]
                send_auto_otp(chat_id, phone, info["otp"], user_id=uid, user_name=call.from_user.first_name, msg_id=msg_id)
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
                InlineKeyboardButton("📜 Lịch sử & Trạng thái rút", callback_data="withdraw_history"),
                InlineKeyboardButton("🔙 Quay lại Menu Chính", callback_data="back_home")
            )
            try:
                bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)
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
                USER_WITHDRAW_STATE[uid] = True
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton("❌ Hủy bỏ & Quay lại", callback_data="cancel_withdraw"))
                try:
                    bot.edit_message_text(
                        "📥 <b>HỆ THỐNG RÚT TIỀN TỰ ĐỘNG</b>\n"
                        "-----------------------------------\n"
                        "💎 <b>Loại tài sản:</b> USDT (Mạng TON)\n"
                        "💸 <b>Phí rút tiền:</b> <code>0% (Miễn phí hoàn toàn)</code>\n\n"
                        "👇 <b>HÀNH ĐỘNG CẦN LÀM:</b>\n"
                        "Vui lòng nhập trực tiếp địa chỉ ví <b>USDT mạng TON</b> của bạn vào ô chat bên dưới:\n"
                        "<i>(Ví chuẩn TON phải bắt đầu bằng <b>EQ</b> hoặc <b>UQ</b> và có đúng <b>48 ký tự</b>).</i>",
                        chat_id, msg_id, parse_mode="HTML", reply_markup=markup
                    )
                except Exception:
                    pass

        elif data == "cancel_withdraw":
            USER_WITHDRAW_STATE.pop(uid, None)
            USER_PENDING_WALLET.pop(uid, None)
            bot.answer_callback_query(call.id, "Đã hủy yêu cầu rút tiền.", show_alert=False)
            call.data = "my_wallet"
            handle_callbacks(call)

        elif data == "confirm_withdraw_action":
            wallet_addr = USER_PENDING_WALLET.pop(uid, None)
            USER_WITHDRAW_STATE.pop(uid, None)
            
            if not wallet_addr:
                bot.answer_callback_query(call.id, "Phiên giao dịch đã hết hạn, vui lòng thao tác lại!", show_alert=True)
                return
                
            settings = load_settings()
            users_db = load_json_db(USERS_FILE)
            uid_str = str(uid)
            min_w = settings.get("min_withdraw", 5.0)
            
            if uid_str in users_db:
                with_amount = users_db[uid_str]["balance"]
                if with_amount < min_w:
                    bot.answer_callback_query(call.id, f"Số dư không đủ hạn mức rút tối thiểu (${min_w:.1f})!", show_alert=True)
                    return
                    
                users_db[uid_str]["balance"] = 0.0
                save_json_db(USERS_FILE, users_db)
                
                current_time_str = datetime.datetime.now().strftime('%H:%M:%S - %d/%m/%Y')
                history_db = load_json_db(WITHDRAW_HISTORY_FILE)
                if uid_str not in history_db:
                    history_db[uid_str] = []
                    
                history_db[uid_str].append({
                    "amount": with_amount,
                    "wallet": wallet_addr,
                    "status": "⏳ Đang chờ duyệt",
                    "time": current_time_str
                })
                save_json_db(WITHDRAW_HISTORY_FILE, history_db)
                
                user_info = get_user(uid)
                admin_text = (
                    "💸 <b>YÊU CẦU RÚT TIỀN MỚI (0% PHÍ)</b>\n"
                    "-----------------------------------\n"
                    f"👤 <b>Họ tên người rút:</b> {user_info.get('name')}\n"
                    f"🆔 <b>Telegram ID:</b> <code>{uid}</code>\n"
                    f"🔗 <b>Username:</b> @{user_info.get('username', 'Không có')}\n"
                    f"💵 <b>Số tiền rút:</b> <code>${with_amount:.4f} USDT</code>\n"
                    f"💎 <b>Mạng lưới:</b> TON Network\n"
                    f"📤 <b>Địa chỉ ví TON:</b> <code>{wallet_addr}</code>\n"
                    f"⏰ <b>Thời gian thực:</b> {current_time_str}"
                )
                
                markup_admin = InlineKeyboardMarkup()
                markup_admin.add(InlineKeyboardButton("💸 Vào Menu Duyệt Lệnh", callback_data="admin_view_withdraws"))
                try:
                    bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML", reply_markup=markup_admin)
                except Exception as e:
                    print(f"Lỗi gửi thông báo cho Admin: {e}")
                    
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton("📜 Xem Lịch sử & Trạng thái rút", callback_data="withdraw_history"))
                markup.add(InlineKeyboardButton("🔙 Về Menu Chính", callback_data="back_home"))
                
                try:
                    bot.edit_message_text(
                        "✅ <b>GỬI YÊU CẦU RÚT TIỀN THÀNH CÔNG!</b>\n"
                        "-----------------------------------\n"
                        f"💵 Số tiền: <b>${with_amount:.4f} USDT</b>\n"
                        f"⚡ Phí giao dịch: <b>0% (Miễn phí)</b>\n"
                        f"📤 Ví nhận (TON): <code>{wallet_addr}</code>\n"
                        f"📌 Trạng thái: <b>⏳ Đang chờ duyệt</b>\n"
                        f"⏰ Thời điểm: <i>{current_time_str}</i>\n\n"
                        "⏳ Yêu cầu của bạn đã được gửi trực tiếp đến Admin để xử lý!",
                        chat_id, msg_id, parse_mode="HTML", reply_markup=markup
                    )
                except Exception:
                    pass

        elif data == "withdraw_history":
            history_db = load_json_db(WITHDRAW_HISTORY_FILE)
            uid_str = str(uid)
            user_histories = history_db.get(uid_str, [])
            
            text = (
                "📜 <b>LỊCH SỬ & TRẠNG THÁI RÚT TIỀN</b>\n"
                "-----------------------------------\n"
            )
            if not user_histories:
                text += "<i>Bạn chưa có lịch sử yêu cầu rút tiền nào.</i>"
            else:
                for idx, item in enumerate(user_histories[::-1], 1):
                    text += (
                        f"<b>#{idx}. Số tiền:</b> <code>${item.get('amount'):.4f} USDT</code>\n"
                        f"📤 <b>Ví TON:</b> <code>{item.get('wallet')}</code>\n"
                        f"📌 <b>Trạng thái:</b> <b>{item.get('status')}</b>\n"
                        f"⏰ <b>Thời gian:</b> <i>{item.get('time')}</i>\n"
                        "-----------------------------------\n"
                    )
                    
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔙 Quay lại Ví", callback_data="my_wallet"))
            try:
                bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)
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
                bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)
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
                bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)
            except Exception:
                pass

        elif data == "back_home":
            USER_WITHDRAW_STATE.pop(uid, None)
            USER_PENDING_WALLET.pop(uid, None)
            USER_WSS_STATE.pop(uid, None)
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
                bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)
            except Exception:
                pass

        elif data == "admin_panel" and uid == ADMIN_ID:
            users = load_json_db(USERS_FILE)
            spam_data = load_json_db(SPAM_TRACKER_FILE)
            settings = load_settings()
            wss_status = "🟢 Đã kết nối" if settings.get("ivas_ws_url") else "🔴 Chưa cài"
            
            text = (
                "👑 <b>BẢNG ĐIỀU KHIỂN ADMIN TỐI CAO</b>\n"
                "-----------------------------------\n"
                f"👥 Tổng số user: <b>{len(users)}</b>\n"
                f"📊 Tổng số stock: <b>{sum(len(d['numbers']) for d in COUNTRY_CACHE.values())}</b>\n"
                f"🔗 Trạng thái IVAS WSS: <b>{wss_status}</b>\n"
                f"🛡 Tài khoản bị phạt/khóa: <b>{len(spam_data)}</b>\n"
            )
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                InlineKeyboardButton("🔗 Cấu hình IVAS WebSocket (WSS)", callback_data="admin_set_wss"),
                InlineKeyboardButton("🏆 Top Số Dư User (Kiểm tra gian lận)", callback_data="admin_top_balances"),
                InlineKeyboardButton("👥 Danh sách User Đăng Ký", callback_data="admin_view_users"),
                InlineKeyboardButton("💸 Duyệt Lệnh Rút Tiền", callback_data="admin_view_withdraws"),
                InlineKeyboardButton("🔄 Sync Batch Số Mới (Web iVASMS)", callback_data="admin_reload"),
                InlineKeyboardButton("🛡 Quản lý & Mở khóa Spam", callback_data="admin_users"),
                InlineKeyboardButton("🔙 Quay lại Menu Chính", callback_data="back_home")
            )
            try:
                bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)
            except Exception:
                pass

        elif data == "admin_set_wss" and uid == ADMIN_ID:
            USER_WSS_STATE[uid] = True
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("❌ Hủy bỏ", callback_data="admin_panel"))
            try:
                bot.edit_message_text(
                    "<b>🔗 CẤU HÌNH WEBSOCKET URL (WSS)</b>\n"
                    "-----------------------------------\n"
                    "Vui lòng gửi đường dẫn WebSocket (`wss://...`) lấy từ trình duyệt (như Mises Browser) vào đây để bot lắng nghe OTP real-time:",
                    chat_id, msg_id, parse_mode="HTML", reply_markup=markup
                )
            except Exception:
                pass

        elif data == "admin_top_balances" and uid == ADMIN_ID:
            users_db = load_json_db(USERS_FILE)
            text = "🏆 <b>BẢNG TOP SỐ DƯ NGƯỜI DÙNG (KIỂM TRA GIAN LẬN):</b>\n\n"
            if not users_db:
                text += "<i>Chưa có dữ liệu người dùng.</i>"
            else:
                sorted_users = sorted(users_db.values(), key=lambda x: x.get('balance', 0.0), reverse=True)
                for idx, u_info in enumerate(sorted_users[:15], 1):
                    text += (
                        f"<b>#{idx}</b> | 👤 <b>{u_info.get('name')}</b> (@{u_info.get('username')})\n"
                        f"🆔 ID: <code>{u_info.get('id')}</code>\n"
                        f"💵 <b>Số dư:</b> <code>${u_info.get('balance', 0.0):.4f}</code>\n"
                        "-----------------------------------\n"
                    )
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔙 Quay lại Admin Panel", callback_data="admin_panel"))
            try:
                bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)
            except Exception:
                pass

        elif data == "admin_view_users" and uid == ADMIN_ID:
            users_db = load_json_db(USERS_FILE)
            text = "👥 <b>DANH SÁCH NGƯỜI DÙNG ĐĂNG KÝ:</b>\n\n"
            if not users_db:
                text += "<i>Chưa có người dùng nào đăng ký.</i>"
            else:
                for u_id, u_info in list(users_db.items())[-10:]:
                    text += (
                        f"👤 <b>Tên:</b> {u_info.get('name')}\n"
                        f"🆔 <b>ID:</b> <code>{u_info.get('id')}</code>\n"
                        f"🔗 <b>Username:</b> @{u_info.get('username')}\n"
                        f"💵 <b>Số dư:</b> <code>${u_info.get('balance', 0.0):.4f}</code>\n"
                        f"📅 <b>Đăng ký lúc:</b> {u_info.get('joined_at')}\n"
                        "-----------------------------------\n"
                    )
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔙 Quay lại Admin Panel", callback_data="admin_panel"))
            try:
                bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)
            except Exception:
                pass

        elif data == "admin_view_withdraws" and uid == ADMIN_ID:
            history_db = load_json_db(WITHDRAW_HISTORY_FILE)
            pending_items = []
            for u_id, items in history_db.items():
                for idx, it in enumerate(items):
                    if "⏳" in it.get("status", ""):
                        pending_items.append((u_id, idx, it))

            if not pending_items:
                bot.answer_callback_query(call.id, "Hiện không có lệnh rút tiền nào đang chờ duyệt!", show_alert=True)
                return

            text = "💸 <b>DANH SÁCH LỆNH RÚT ĐANG CHỜ DUYỆT:</b>\n\n"
            markup = InlineKeyboardMarkup(row_width=1)
            for u_id, idx, it in pending_items[:5]:
                text += f"• ID: <code>{u_id}</code> | <b>${it.get('amount'):.4f}</b> | <code>{it.get('wallet')[:10]}...</code>\n"
                markup.add(InlineKeyboardButton(f"✅ Duyệt thanh toán ID {u_id} (${it.get('amount')})", callback_data=f"done_w_{u_id}_{idx}"))

            markup.add(InlineKeyboardButton("🔙 Quay lại Admin Panel", callback_data="admin_panel"))
            try:
                bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)
            except Exception:
                pass

        elif data.startswith("done_w_") and uid == ADMIN_ID:
            parts = data.split("_")
            target_uid = parts[2]
            item_idx = int(parts[3])
            
            history_db = load_json_db(WITHDRAW_HISTORY_FILE)
            if target_uid in history_db and len(history_db[target_uid]) > item_idx:
                history_db[target_uid][item_idx]["status"] = "✅ Đã thanh toán thành công"
                save_json_db(WITHDRAW_HISTORY_FILE, history_db)
                
                try:
                    bot.send_message(
                        int(target_uid),
                        f"🎉 <b>YÊU CẦU RÚT TIỀN ĐÃ ĐƯỢC DUYỆT!</b>\n"
                        f"💵 Số tiền: <b>${history_db[target_uid][item_idx]['amount']:.4f} USDT</b>\n"
                        f"📤 Ví nhận: <code>{history_db[target_uid][item_idx]['wallet']}</code>\n"
                        f"📌 Trạng thái: <b>✅ Đã chuyển tiền thành công qua mạng TON!</b>",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass

                bot.answer_callback_query(call.id, "Đã duyệt và cập nhật trạng thái thành công!", show_alert=True)
                call.data = "admin_view_withdraws"
                handle_callbacks(call)
            else:
                bot.answer_callback_query(call.id, "Không tìm thấy dữ liệu lệnh rút này!", show_alert=True)

        elif data == "admin_reload" and uid == ADMIN_ID:
            success, res = load_text_batch(reset=True)
            if success:
                bot.answer_callback_query(call.id, f"Đã đồng bộ thành công: {res} số từ iVASMS!", show_alert=True)
            else:
                bot.answer_callback_query(call.id, f"Lỗi đồng bộ: {res}", show_alert=True)

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
                bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)
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
    except Exception as e:
        print(f"Lỗi trong handle_callbacks: {e}")

# ==========================================
# 💸 13. XỬ LÝ NHẬP VÍ & NHẬP WSS URL
# ==========================================
@bot.message_handler(func=lambda message: USER_WITHDRAW_STATE.get(message.from_user.id, False) or USER_WSS_STATE.get(message.from_user.id, False))
def handle_text_inputs(message):
    uid = message.from_user.id
    text_val = message.text.strip()
    
    if text_val.startswith('/'):
        USER_WITHDRAW_STATE.pop(uid, None)
        USER_PENDING_WALLET.pop(uid, None)
        USER_WSS_STATE.pop(uid, None)
        return

    # Xử lý nhập WebSocket URL từ Admin
    if USER_WSS_STATE.get(uid, False):
        if uid != ADMIN_ID:
            USER_WSS_STATE.pop(uid, None)
            return
        
        settings = load_settings()
        settings["ivas_ws_url"] = text_val
        save_settings(settings)
        USER_WSS_STATE.pop(uid, None)
        
        bot.send_message(
            uid,
            f"✅ <b>Đã lưu WebSocket URL thành công!</b>\n<code>{text_val}</code>\n\nLuồng ngầm WSS sẽ tự động kết nối để nhận OTP real-time.",
            parse_mode="HTML"
        )
        return

    # Xử lý nhập ví rút tiền
    if USER_WITHDRAW_STATE.get(uid, False):
        wallet_addr = text_val
        TON_ADDRESS_REGEX = re.compile(r'^(EQ|UQ)[A-Za-z0-9\-_]{46}$')
        if not TON_ADDRESS_REGEX.match(wallet_addr):
            bot.send_message(
                uid,
                "❌ <b>ĐỊA CHỈ VÍ KHÔNG HỢP LỆ!</b>\n\n"
                "Ví USDT mạng TON phải bắt đầu bằng <b>EQ</b> hoặc <b>UQ</b> và có đúng <b>48 ký tự</b>.\n"
                "Vui lòng kiểm tra lại và gửi lại chính xác:",
                parse_mode="HTML"
            )
            return
            
        USER_PENDING_WALLET[uid] = wallet_addr
        
        settings = load_settings()
        user_info = get_user(uid)
        min_w = settings.get("min_withdraw", 5.0)
        current_bal = user_info.get("balance", 0.0)
        
        if current_bal < min_w:
            USER_WITHDRAW_STATE.pop(uid, None)
            USER_PENDING_WALLET.pop(uid, None)
            bot.send_message(uid, f"❌ Số dư hiện tại (${current_bal:.4f}) không đủ hạn mức rút tối thiểu (${min_w:.1f})!")
            return
            
        confirm_text = (
            "🔍 <b>XÁC NHẬN THÔNG TIN RÚT TIỀN</b>\n"
            "-----------------------------------\n"
            f"💵 <b>Số tiền rút:</b> <code>${current_bal:.4f} USDT</code>\n"
            f"⚡ <b>Phí giao dịch:</b> <code>0% (Miễn phí)</code>\n"
            f"💎 <b>Mạng lưới:</b> TON Network\n"
            f"📤 <b>Địa chỉ ví nhận:</b> <code>{wallet_addr}</code>\n"
            "-----------------------------------\n"
            "⚠️ <i>Vui lòng kiểm tra kỹ địa chỉ ví. Bấm Xác nhận để gửi đơn hoặc Hủy bỏ nếu muốn thay đổi!</i>"
        )
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("✅ Xác Nhận Rút", callback_data="confirm_withdraw_action"),
            InlineKeyboardButton("❌ Hủy Bỏ", callback_data="cancel_withdraw")
        )
        
        bot.send_message(uid, confirm_text, parse_mode="HTML", reply_markup=markup)

# ==========================================
# 🚀 14. KHỞI ĐỘNG HỆ THỐNG AN TOÀN TUYỆT ĐỐI
# ==========================================
if __name__ == "__main__":
    # Luồng quét HTTP dự phòng định kỳ
    t_scanner = threading.Thread(target=background_sms_scanner, daemon=True)
    t_scanner.start()
    
    # Luồng ngầm WebSocket lắng nghe real-time wss://
    t_wss = threading.Thread(target=ivas_websocket_listener, daemon=True)
    t_wss.start()
    
    # Web server giữ bot online trên Render
    t_web = threading.Thread(target=run_web, daemon=True)
    t_web.start()
    
    print("🤖 Bot Telegram IVASMS + WebSocket Real-time + Auto-Sync Web đang chạy mượt mà...")
    
    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"⚠️ Mất kết nối Telegram: {e}")
            print("⏳ Đang tự động kết nối lại sau 5 giây...")
            time.sleep(5)
