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
# Configuration (IVASMS Direct Engine)
# ==========================================
BOT_TOKEN = "9139656226:AAF3G3Kll7E0DipP80mnXGWvex4BMdEVCzc"
ADMIN_ID = 6726769296
TARGET_CHAT = '-1004341368656'
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"
BOT_USERNAME = ""

IVASMS_GET_SMS_URL = "https://www.ivasms.com/portal/sms/getsms"

user_cache = {} 
daily_stats = {"date": "", "numbers": 0, "otps": 0} 
bot_settings = {"withdraw_on": True, "min_withdraw": 5.0}
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

# Kho Mạng xã hội & Ứng dụng đầy đủ cho anh em đăng ký mọi thể loại
PREMIUM_APPS = {
    "Facebook": {"emoji": "📘", "id": "5429172110520003976"},
    "WhatsApp": {"emoji": "💬", "id": "5429612632430654504"},
    "Telegram": {"emoji": "✈️", "id": "5429136513831057777"},
    "Instagram": {"emoji": "📸", "id": "5429478178479447442"},
    "Google": {"emoji": "🔍", "id": "5429558795015593080"},
    "Microsoft": {"emoji": "🪟", "id": "5979047775470358891"},
    "TikTok": {"emoji": "🎵", "id": "5429132656950419591"},
    "Shopee": {"emoji": "🛍️", "id": "5429558795015593080"},
    "Lazada": {"emoji": "📦", "id": "5429438106434575354"},
    "Zalo": {"emoji": "💬", "id": "5429612632430654504"},
    "Twitter": {"emoji": "🐦", "id": "5429136513831057777"},
    "Binance": {"emoji": "💱", "id": "5429438106434575354"},
    "Discord": {"emoji": "🎬", "id": "5429594374524676604"},
    "Other": {"emoji": "📶", "id": "5429353834881261942"}
}

# Đầy đủ 195+ quốc gia chuẩn quốc tế kèm cờ
country_db = {
    "1": ("USA/Canada", "🇺🇸"), "7": ("Russia/Kazakhstan", "🇷🇺"), "20": ("Egypt", "🇪🇬"), "27": ("South Africa", "🇿🇦"),
    "30": ("Greece", "🇬🇷"), "31": ("Netherlands", "🇳🇱"), "32": ("Belgium", "🇧🇪"), "33": ("France", "🇫🇷"),
    "34": ("Spain", "🇪🇸"), "36": ("Hungary", "🇭🇺"), "39": ("Italy", "🇮🇹"), "40": ("Romania", "🇷🇴"),
    "41": ("Switzerland", "🇨🇭"), "43": ("Austria", "🇦🇹"), "44": ("UK", "🇬🇧"), "45": ("Denmark", "🇩🇰"),
    "46": ("Sweden", "🇸🇪"), "47": ("Norway", "🇳🇴"), "48": ("Poland", "🇵🇱"), "49": ("Germany", "🇩🇪"),
    "51": ("Peru", "🇵🇪"), "52": ("Mexico", "🇲🇽"), "53": ("Cuba", "🇨🇺"), "54": ("Argentina", "🇦🇷"),
    "55": ("Brazil", "🇧🇷"), "56": ("Chile", "🇨🇱"), "57": ("Colombia", "🇨🇴"), "58": ("Venezuela", "🇻🇪"),
    "60": ("Malaysia", "🇲🇾"), "61": ("Australia", "🇦🇺"), "62": ("Indonesia", "🇮🇩"), "63": ("Philippines", "🇵🇭"),
    "64": ("New Zealand", "🇳🇿"), "65": ("Singapore", "🇸🇬"), "66": ("Thailand", "🇹🇭"), "81": ("Japan", "🇯🇵"),
    "82": ("South Korea", "🇰🇷"), "84": ("Vietnam", "🇻🇳"), "86": ("China", "🇨🇳"), "90": ("Turkey", "🇹🇷"),
    "91": ("India", "🇮🇳"), "92": ("Pakistan", "🇵🇰"), "93": ("Afghanistan", "🇦🇫"), "94": ("Sri Lanka", "🇱🇰"),
    "95": ("Myanmar", "🇲🇲"), "98": ("Iran", "🇮🇷"), "212": ("Morocco", "🇲🇦"), "213": ("Algeria", "🇩🇿"),
    "216": ("Tunisia", "🇹🇳"), "218": ("Libya", "🇱🇾"), "220": ("Gambia", "🇬🇲"), "221": ("Senegal", "🇸🇳"),
    "222": ("Mauritania", "🇲🇷"), "223": ("Mali", "🇲🇱"), "224": ("Guinea", "🇬🇳"), "225": ("Ivory Coast", "🇨🇮"),
    "226": ("Burkina Faso", "🇧🇫"), "227": ("Niger", "🇳🇪"), "228": ("Togo", "🇹🇬"), "229": ("Benin", "🇧🇯"),
    "230": ("Mauritius", "🇲🇺"), "231": ("Liberia", "🇱🇷"), "232": ("Sierra Leone", "🇸🇱"), "233": ("Ghana", "🇬🇭"),
    "234": ("Nigeria", "🇳🇬"), "235": ("Chad", "🇹🇩"), "236": ("CAR", "🇨🇫"), "237": ("Cameroon", "🇨🇲"),
    "238": ("Cape Verde", "🇨🇻"), "239": ("Sao Tome", "🇸🇹"), "240": ("Equatorial Guinea", "🇬🇶"), "241": ("Gabon", "🇬🇦"),
    "242": ("Congo", "🇨🇬"), "243": ("DRC", "🇨🇩"), "244": ("Angola", "🇦🇴"), "245": ("Guinea-Bissau", "🇬🇼"),
    "246": ("Diego Garcia", "🇮🇴"), "248": ("Seychelles", "🇸🇨"), "249": ("Sudan", "🇸🇩"), "250": ("Rwanda", "🇷🇼"),
    "251": ("Ethiopia", "🇪🇹"), "252": ("Somalia", "🇸🇴"), "253": ("Djibouti", "🇩🇯"), "254": ("Kenya", "🇰🇪"),
    "255": ("Tanzania", "🇹🇿"), "256": ("Uganda", "🇺🇬"), "257": ("Burundi", "🇧🇮"), "258": ("Mozambique", "🇲🇿"),
    "260": ("Zambia", "🇿🇲"), "261": ("Madagascar", "🇲🇬"), "262": ("Reunion", "🇷🇪"), "263": ("Zimbabwe", "🇿🇼"),
    "264": ("Namibia", "🇳🇦"), "265": ("Malawi", "🇲🇼"), "266": ("Lesotho", "🇱🇸"), "267": ("Botswana", "🇧🇼"),
    "268": ("Swaziland", "🇸🇿"), "269": ("Comoros", "🇰🇲"), "291": ("Eritrea", "🇪🇷"), "297": ("Aruba", "🇦🇼"),
    "298": ("Faroe Islands", "🇫🇴"), "299": ("Greenland", "🇬🇱"), "350": ("Gibraltar", "🇬🇮"), "351": ("Portugal", "🇵🇹"),
    "352": ("Luxembourg", "🇱🇺"), "353": ("Ireland", "🇮🇪"), "354": ("Iceland", "🇮🇸"), "355": ("Albania", "🇦🇱"),
    "356": ("Malta", "🇲🇹"), "357": ("Cyprus", "🇨🇾"), "358": ("Finland", "🇫🇮"), "359": ("Bulgaria", "🇧🇬"),
    "370": ("Lithuania", "🇱🇹"), "371": ("Latvia", "🇱🇻"), "372": ("Estonia", "🇪🇪"), "373": ("Moldova", "🇲🇩"),
    "374": ("Armenia", "🇦🇲"), "375": ("Belarus", "🇧🇾"), "376": ("Andorra", "🇦🇩"), "377": ("Monaco", "🇲🇨"),
    "378": ("San Marino", "🇸🇲"), "380": ("Ukraine", "🇺🇦"), "381": ("Serbia", "🇷🇸"), "382": ("Montenegro", "🇲🇪"),
    "383": ("Kosovo", "🇽🇰"), "385": ("Croatia", "🇭🇷"), "386": ("Slovenia", "🇸🇮"), "387": ("Bosnia", "🇧🇦"),
    "389": ("Macedonia", "🇲🇰"), "420": ("Czech Republic", "🇨🇿"), "421": ("Slovakia", "🇸🇰"), "423": ("Liechtenstein", "🇱🇮"),
    "500": ("Falkland Islands", "🇫🇰"), "501": ("Belize", "🇧🇿"), "502": ("Guatemala", "🇬🇹"), "503": ("El Salvador", "🇸🇻"),
    "504": ("Honduras", "🇭🇳"), "505": ("Nicaragua", "🇳🇮"), "506": ("Costa Rica", "🇨🇷"), "507": ("Panama", "🇵🇦"),
    "508": ("St Pierre & Miquelon", "pm"), "509": ("Haiti", "🇭🇹"), "590": ("Guadeloupe", "🇬🇵"), "591": ("Bolivia", "🇧🇴"),
    "592": ("Guyana", "🇬🇾"), "593": ("Ecuador", "🇪🇨"), "594": ("French Guiana", "🇬🇫"), "595": ("Paraguay", "🇵🇾"),
    "597": ("Suriname", "🇸🇷"), "598": ("Uruguay", "🇺🇾"), "599": ("Curacao", "🇨🇼"), "670": ("East Timor", "🇹🇱"),
    "673": ("Brunei", "🇧🇳"), "674": ("Nauru", "🇳🇷"), "675": ("Papua New Guinea", "🇵🇬"), "676": ("Tonga", "🇹🇴"),
    "677": ("Solomon Islands", "🇸🇧"), "678": ("Vanuatu", "🇻🇺"), "679": ("Fiji", "🇫🇯"), "680": ("Palau", "🇵🇼"),
    "681": ("Wallis & Futuna", "🇼🇫"), "682": ("Cook Islands", "🇨🇰"), "683": ("Niue", "🇳🇺"), "685": ("Samoa", "🇼🇸"),
    "686": ("Kiribati", "🇰🇮"), "687": ("New Caledonia", "🇳🇨"), "688": ("Tuvalu", "🇹🇻"), "689": ("French Polynesia", "🇵🇫"),
    "690": ("Tokelau", "🇹🇰"), "691": ("Micronesia", "🇫🇲"), "692": ("Marshall Islands", "🇲🇭"), "850": ("North Korea", "🇰🇵"),
    "852": ("Hong Kong", "🇭🇰"), "853": ("Macau", "🇲🇴"), "855": ("Cambodia", "🇰🇭"), "856": ("Laos", "🇱🇦"),
    "880": ("Bangladesh", "🇧🇩"), "886": ("Taiwan", "🇹🇼"), "960": ("Maldives", "🇲🇻"), "961": ("Lebanon", "🇱🇧"),
    "962": ("Jordan", "🇯🇴"), "963": ("Syria", "🇸🇾"), "964": ("Iraq", "🇮🇶"), "965": ("Kuwait", "🇰🇼"),
    "966": ("Saudi Arabia", "🇸🇦"), "967": ("Yemen", "🇾🇪"), "968": ("Oman", "🇴🇲"), "970": ("Palestine", "🇵🇸"),
    "971": ("UAE", "🇦🇪"), "972": ("Israel", "🇮🇱"), "973": ("Bahrain", "🇧🇭"), "974": ("Qatar", "🇶🇦"),
    "975": ("Bhutan", "🇧🇹"), "976": ("Mongolia", "🇲🇳"), "977": ("Nepal", "🇳🇵"), "992": ("Tajikistan", "🇹🇯"),
    "993": ("Turkmenistan", "🇹🇲"), "994": ("Azerbaijan", "🇦🇿"), "995": ("Georgia", "🇬🇪"), "996": ("Kyrgyzstan", "🇰🇬"),
    "998": ("Uzbekistan", "🇺🇿")
}

def detect_service(message_text):
    msg_lower = str(message_text).lower()
    for service, info in PREMIUM_APPS.items():
        if service.lower() in msg_lower:
            return service
    return "Other"

def update_daily_stat(key, amount=1):
    global daily_stats
    today = time.strftime("%Y-%m-%d")
    if daily_stats.get("date") != today:
        daily_stats = {"date": today, "numbers": 0, "otps": 0}
    daily_stats[key] = daily_stats.get(key, 0) + amount

def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "text": apply_emojis(text), "parse_mode": parse_mode}
    if reply_markup: payload["reply_markup"] = reply_markup
    try: return requests.post(BASE_URL + "sendMessage", json=payload).json()
    except Exception: return None

def dispatch_otp_alert(bot_obj, service, phone, msg, timestamp, country, flag):
    clean_phone = str(phone).replace("+", "")
    masked = clean_phone[:6] + "****" + clean_phone[-3:] if len(clean_phone) > 7 else clean_phone
    match = re.search(r'\d{3}[-\s]?\d{3}', str(msg))
    code = match.group(0) if match else "N/A"

    caption = (f"💐 <b>『 IVASMS NEW OTP RECEIVED 』</b> ✨\n"
               f"━━━━━━━━━━━━━━━━━━━━━\n\n"
               f"<b>⌚ ᴛɪᴍᴇ:</b> <code>{html.escape(str(timestamp))}</code>\n"
               f"<b>🌍 ᴄᴏᴜɴᴛʀʏ:</b> {html.escape(str(country))} {flag}\n"
               f"<b>📱 ɴᴜᴍʙᴇ🇷:</b> <code>{html.escape(str(masked))}</code>\n"
               f"<b>🛠 ꜱᴇʀᴠɪᴄᴇ:</b> <code>{html.escape(str(service))}</code>\n"
               f"<b>🔑 ᴄᴏᴅᴇ:</b> <code>{html.escape(str(code))}</code>\n\n"
               f"<b>💬 ᴍᴇssᴀɢᴇ:</b>\n<pre>{html.escape(str(msg))}</pre>\n\n"
               f"━━━━━━━━━━━━━━━━━━━━━")
    
    try:
        requests.post(BASE_URL + "sendMessage", json={
            "chat_id": TARGET_CHAT,
            "text": apply_emojis(caption),
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        })
    except Exception as e: 
        print(f"Error dispatching update: {e}")

def ivasms_polling_loop(bot_obj):
    print("🚀 IVASMS Direct Polling Loop Started Successfully on Termux!")
    last_seen_id = None
    cookie_alert_sent = False
    
    while True:
        try:
            today_str = time.strftime("%Y-%m-%d")
            headers = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 10)",
                "Referer": "https://www.ivasms.com/portal/sms",
                "X-Requested-With": "XMLHttpRequest",
                "Connection": "keep-alive"
            }
            payload = {
                "start_date": today_str,
                "end_date": today_str
            }
            
            # Gán chuỗi cookie của bro vào đây
            cookies = {
                "ivas_sms_session": "DANG_KY_COOKIE_CUA_BRO_O_DAY"
            }
            
            r = requests.post(IVASMS_GET_SMS_URL, data=payload, cookies=cookies, headers=headers, timeout=10)
            
            # Cơ chế phát hiện Cookie chết (401/403) lập tức hú còi báo động qua Telegram cá nhân
            if r.status_code in [401, 403]:
                if not cookie_alert_sent:
                    send_message(ADMIN_ID, "⚠️ <b>CẢNH BÁO:</b> Cookie IVASMS đã bị Cloudflare đá (403 Forbidden)! Bro vui lòng cập nhật lại cookie mới trên điện thoại nhé.")
                    cookie_alert_sent = True
                time.sleep(30)
                continue
            
            if r.status_code == 200:
                cookie_alert_sent = False 
                try:
                    res_json = r.json()
                    sms_list = res_json.get("data", []) if isinstance(res_json, dict) else res_json
                    if isinstance(sms_list, list):
                        for item in sms_list:
                            msg_id = item.get("id", item.get("timestamp", ""))
                            if last_seen_id is None or str(msg_id) > str(last_seen_id):
                                phone = item.get("num", item.get("phone", ""))
                                message_text = item.get("message", item.get("text", ""))
                                ts = item.get("dt", time.strftime("%Y-%m-%d %H:%M:%S"))
                                
                                raw_num = str(phone).lstrip("+")
                                info = ("Global", "🌍")
                                for length in range(4, 0, -1):
                                    if raw_num[:length] in country_db:
                                        info = country_db[raw_num[:length]]
                                        break
                                
                                detected_srv = detect_service(message_text)
                                update_daily_stat("otps", 1)
                                dispatch_otp_alert(bot_obj, detected_srv, phone, message_text, ts, info[0], info[1])
                                last_seen_id = msg_id
                except Exception:
                    pass
        except Exception as e:
            print(f"Polling error: {e}")
            
        time.sleep(3)

def main():
    bot_dummy = Bot(token=BOT_TOKEN)
    threading.Thread(target=ivasms_polling_loop, args=(bot_dummy,), daemon=True).start()
    print("🚀 Termux Background Polling Service Active!")
    while True:
        time.sleep(60)

if __name__ == "__main__":
    main()
