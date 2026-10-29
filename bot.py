import asyncio
import requests
import random
import sqlite3
import os
import re
import html
import threading
import time
import json
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters, CallbackContext

# ==========================================
# Configuration (Fast Node Dynamic Engine)
# ==========================================
BOT_TOKEN = "9139656226:AAF3G3Kll7E0DipP80mnXGWvex4BMdEVCzc"
ADMIN_ID = 6726769296
TARGET_CHAT = '-1004341368656'
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"

IVASMS_GET_SMS_URL = "https://www.ivasms.com/portal/sms/getsms"
CONFIG_FILE = "cookie_config.json"

# Quản lý trạng thái nhập cookie động của Admin
admin_state = {"waiting_for_cookie": False}

def load_cookie():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                return data.get("ivas_sms_session", "")
        except Exception:
            pass
    return "DANG_KY_COOKIE_CUA_BRO_O_DAY"

def save_cookie(cookie_val):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"ivas_sms_session": cookie_val}, f)

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
    "Shopee": {"emoji": "🛍️", "id": "5429558795015593080"},
    "Lazada": {"emoji": "📦", "id": "5429438106434575354"},
    "Zalo": {"emoji": "💬", "id": "5429612632430654504"},
    "Twitter": {"emoji": "🐦", "id": "5429136513831057777"},
    "Binance": {"emoji": "💱", "id": "5429438106434575354"},
    "Discord": {"emoji": "🎬", "id": "5429594374524676604"},
    "Other": {"emoji": "📶", "id": "5429353834881261942"}
}

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

def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "text": apply_emojis(text), "parse_mode": parse_mode}
    if reply_markup: payload["reply_markup"] = reply_markup
    try: return requests.post(BASE_URL + "sendMessage", json=payload).json()
    except Exception: return None

def dispatch_otp_alert(service, phone, msg, timestamp, country, flag):
    clean_phone = str(phone).replace("+", "")
    masked = clean_phone[:6] + "****" + clean_phone[-3:] if len(clean_phone) > 7 else clean_phone
    match = re.search(r'\d{3}[-\s]?\d{3}', str(msg))
    code = match.group(0) if match else "N/A"

    caption = (f"💐 <b>『 FAST NODE DIRECT OTP 』</b> ✨\n"
               f"━━━━━━━━━━━━━━━━━━━━━\n\n"
               f"<b>⌚ ᴛɪᴍᴇ:</b> <code>{html.escape(str(timestamp))}</code>\n"
               f"<b>🌍 ᴄᴏᴜɴᴛʀʏ:</b> {html.escape(str(country))} {flag}\n"
               f"<b>📱 ɴ🇺🇲🇧ᴇ🇷:</b> <code>{html.escape(str(masked))}</code>\n"
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

def verify_cookie(cookie_val):
    """Kiểm tra xem cookie có sống hay không bằng cách gọi request thử"""
    try:
        today_str = time.strftime("%Y-%m-%d")
        headers = {
            "Host": "www.ivasms.com",
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": "https://www.ivasms.com/portal/sms",
            "X-Requested-With": "XMLHttpRequest",
            "Connection": "keep-alive"
        }
        payload = {"start_date": today_str, "end_date": today_str}
        cookies = {"ivas_sms_session": cookie_val.strip()}
        r = requests.post(IVASMS_GET_SMS_URL, data=payload, cookies=cookies, headers=headers, timeout=10)
        if r.status_code == 200:
            return True
    except Exception:
        pass
    return False

def ivasms_polling_loop():
    print("🚀 FAST NODE Direct Polling Loop Active on Termux!")
    last_seen_id = None
    cookie_alert_sent = False
    
    while True:
        current_cookie = load_cookie()
        if not current_cookie or current_cookie == "DANG_KY_COOKIE_CUA_BRO_O_DAY":
            if not cookie_alert_sent:
                keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("➕ Thêm Cookie Mới", callback_data="add_new_cookie")]])
                send_message(ADMIN_ID, "⚠️ <b>CHƯA CÓ COOKIE:</b> Hệ thống chưa nhận được cookie chính chủ của bro. Vui lòng bấm nút bên dưới để thêm cookie nhé!", reply_markup=keyboard)
                cookie_alert_sent = True
            time.sleep(10)
            continue

        try:
            today_str = time.strftime("%Y-%m-%d")
            headers = {
                "Host": "www.ivasms.com",
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
                "Referer": "https://www.ivasms.com/portal/sms",
                "X-Requested-With": "XMLHttpRequest",
                "Sec-Ch-Ua": "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Google Chrome\";v=\"120\"",
                "Sec-Ch-Ua-Mobile": "?1",
                "Sec-Ch-Ua-Platform": "\"Android\"",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "Connection": "keep-alive"
            }
            payload = {"start_date": today_str, "end_date": today_str}
            cookies = {"ivas_sms_session": current_cookie}
            
            r = requests.post(IVASMS_GET_SMS_URL, data=payload, cookies=cookies, headers=headers, timeout=10)
            
            if r.status_code in [401, 403]:
                if not cookie_alert_sent:
                    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("➕ Thêm Cookie Mới", callback_data="add_new_cookie")]])
                    send_message(ADMIN_ID, "⚠️ <b>CẢNH BÁO BẢO MẬT:</b> Cookie IVASMS đã bị Cloudflare đá (403 Forbidden)! Bro bấm nút bên dưới để cập nhật lại cookie mới ngay nhé.", reply_markup=keyboard)
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
                                dispatch_otp_alert(detected_srv, phone, message_text, ts, info[0], info[1])
                                last_seen_id = msg_id
                except Exception:
                    pass
        except Exception as e:
            print(f"Polling error: {e}")
            
        time.sleep(3)

# Xử lý tương tác Telegram Bot (Nút bấm & Tin nhắn nhập cookie)
def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    if query.from_user.id != ADMIN_ID:
        return
    if query.data == "add_new_cookie":
        admin_state["waiting_for_cookie"] = True
        query.message.reply_text("📥 Bro hãy gửi chuỗi giá trị cookie (`ivas_sms_session`) mới vào đây để hệ thống tự check và cập nhật nhé:")

def handle_admin_message(update: Update, context: CallbackContext):
    global admin_state
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    
    if admin_state.get("waiting_for_cookie"):
        new_cookie = update.message.text.strip()
        send_message(ADMIN_ID, "⏳ Đang kiểm tra tính hợp lệ của cookie...")
        
        if verify_cookie(new_cookie):
            save_cookie(new_cookie)
            admin_state["waiting_for_cookie"] = False
            send_message(ADMIN_ID, "✅ <b>THÀNH CÔNG!</b> Cookie mới đã hoạt động mượt mà. Hệ thống tự động khôi phục quét OTP bình thường! 🚀")
        else:
            send_message(ADMIN_ID, "❌ <b>THẤT BẠI:</b> Cookie này không hợp lệ hoặc đã bị Cloudflare từ chối. Bro kiểm tra lại và gửi lại chuỗi cookie chính xác nhé!")

def start_command(update: Update, context: CallbackContext):
    text = (
        "🔥 <b>FAST NODE • LIVE OTP GATEWAY</b>\n\n"
        "Welcome, choose an option from the menu:"
    )
    keyboard = [
        [InlineKeyboardButton("LIVE NUMBER", callback_data="live_num"), InlineKeyboardButton("LIVE TRAFFIC", callback_data="live_traf")],
        [InlineKeyboardButton("INVITE FRIEND", callback_data="invite"), InlineKeyboardButton("WALLET", callback_data="wallet")],
        [InlineKeyboardButton("LEADERBOARD", callback_data="leaderboard")],
        [InlineKeyboardButton("OWNER PANEL", callback_data="owner")]
    ]
    update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

def main():
    # Khởi động vòng lặp cào số ngầm
    threading.Thread(target=ivasms_polling_loop, daemon=True).start()
    
    # Khởi động Telegram Bot Handler nhận lệnh & nút bấm
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start_command))
    dp.add_handler(CallbackQueryHandler(button_callback))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_admin_message))
    
    updater.start_polling()
    print("🚀 Telegram Bot Client Handler Active!")
    updater.idle()

if __name__ == "__main__":
    main()
