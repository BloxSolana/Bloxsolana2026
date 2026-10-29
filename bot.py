import requests
import time
import os
import re
import html
import json

# ==========================================
# Configuration (Fast Node Full Features)
# ==========================================
BOT_TOKEN = "9139656226:AAF3G3Kll7E0DipP80mnXGWvex4BMdEVCzc"
ADMIN_ID = 6726769296
TARGET_CHAT = '-1004341368656'
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"

IVASMS_GET_SMS_URL = "https://www.ivasms.com/portal/sms/getsms"
CONFIG_FILE = "cookie_config.json"

# Kho Mạng Xã Hội Đầy Đủ
PREMIUM_APPS = {
    "Facebook": "📘 Facebook",
    "WhatsApp": "💬 WhatsApp",
    "Telegram": "✈️ Telegram",
    "Instagram": "📸 Instagram",
    "Google": "🔍 Google",
    "Microsoft": "🪟 Microsoft",
    "TikTok": "🎵 TikTok",
    "Shopee": "🛍️ Shopee",
    "Lazada": "📦 Lazada",
    "Zalo": "💬 Zalo",
    "Twitter": "🐦 Twitter",
    "Binance": "💱 Binance",
    "Discord": "🎬 Discord",
    "Other": "📶 Other / General"
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
    "975": ("Bhutan", "🇹🇭"), "976": ("Mongolia", "🇲🇳"), "977": ("Nepal", "🇳🇵"), "992": ("Tajikistan", "🇹🇯"),
    "993": ("Turkmenistan", "🇹🇲"), "994": ("Azerbaijan", "🇦🇿"), "995": ("Georgia", "🇬🇪"), "996": ("Kyrgyzstan", "🇰🇬"),
    "998": ("Uzbekistan", "🇺🇿")
}

def detect_service(msg_text):
    msg_lower = str(msg_text).lower()
    for srv_name in PREMIUM_APPS.keys():
        if srv_name.lower() in msg_lower:
            return PREMIUM_APPS[srv_name]
    return PREMIUM_APPS["Other"]

def load_cookie():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f).get("ivas_sms_session", "")
        except Exception:
            pass
    return ""

def verify_cookie(cookie_val):
    try:
        today = time.strftime("%Y-%m-%d")
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10)",
            "Referer": "https://www.ivasms.com/portal/sms",
            "X-Requested-With": "XMLHttpRequest"
        }
        r = requests.post(IVASMS_GET_SMS_URL, data={"start_date": today, "end_date": today}, cookies={"ivas_sms_session": cookie_val.strip()}, headers=headers, timeout=8)
        return r.status_code == 200
    except Exception:
        return False

def main():
    print("🚀 Fast Node Full Feature Polling Started...")
    last_seen_id = None
    alert_sent = False

    while True:
        cookie = load_cookie()
        if not cookie or not verify_cookie(cookie):
            if not alert_sent:
                requests.post(BASE_URL + "sendMessage", json={
                    "chat_id": ADMIN_ID,
                    "text": "⚠️ <b>CẢNH BÁO:</b> Cookie IVASMS chưa có hoặc đã bị Cloudflare đá (403)! Bro hãy gửi chuỗi cookie mới trực tiếp vào đây để bot tự động lưu nhé.",
                    "parse_mode": "HTML"
                })
                alert_sent = True
            time.sleep(15)
            continue

        alert_sent = False
        try:
            today = time.strftime("%Y-%m-%d")
            headers = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
                "Referer": "https://www.ivasms.com/portal/sms",
                "X-Requested-With": "XMLHttpRequest"
            }
            r = requests.post(IVASMS_GET_SMS_URL, data={"start_date": today, "end_date": today}, cookies={"ivas_sms_session": cookie}, headers=headers, timeout=10)
            
            if r.status_code in [401, 403]:
                requests.post(BASE_URL + "sendMessage", json={
                    "chat_id": ADMIN_ID,
                    "text": "⚠️ <b>CẢNH BÁO 403:</b> Cookie đã chết! Bro hãy gửi ngay chuỗi cookie mới vào đoạn chat này.",
                    "parse_mode": "HTML"
                })
                time.sleep(25)
                continue

            if r.status_code == 200:
                data = r.json()
                sms_list = data.get("data", []) if isinstance(data, dict) else data
                if isinstance(sms_list, list):
                    for item in sms_list:
                        msg_id = item.get("id", item.get("timestamp", ""))
                        if last_seen_id is None or str(msg_id) > str(last_seen_id):
                            phone = item.get("num", item.get("phone", ""))
                            msg_text = item.get("message", item.get("text", ""))
                            ts = item.get("dt", time.strftime("%Y-%m-%d %H:%M:%S"))
                            
                            raw_num = str(phone).lstrip("+")
                            info = ("Global", "🌍")
                            for l in range(4, 0, -1):
                                if raw_num[:l] in country_db:
                                    info = country_db[raw_num[:l]]
                                    break
                            
                            detected_service = detect_service(msg_text)
                            clean_phone = str(phone).replace("+", "")
                            masked = clean_phone[:6] + "****" + clean_phone[-3:] if len(clean_phone) > 7 else clean_phone
                            match = re.search(r'\d{3}[-\s]?\d{3}', str(msg_text))
                            code = match.group(0) if match else "N/A"

                            caption = (f"💐 <b>『 FAST NODE DIRECT OTP 』</b> ✨\n"
                                       f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                                       f"<b>⌚ ᴛɪᴍᴇ:</b> <code>{html.escape(str(ts))}</code>\n"
                                       f"<b>🌍 ᴄᴏᴜɴᴛʀʏ:</b> {html.escape(str(info[0]))} {info[1]}\n"
                                       f"<b>📱 ɴ🇺🇲🇧ᴇ🇷:</b> <code>{html.escape(str(masked))}</code>\n"
                                       f"<b>🛠 ꜱᴇʀᴠɪᴄᴇ:</b> <code>{html.escape(str(detected_service))}</code>\n"
                                       f"<b>🔑 ᴄᴏᴅᴇ:</b> <code>{html.escape(str(code))}</code>\n\n"
                                       f"<b>💬 ᴍᴇssᴀɢᴇ:</b>\n<pre>{html.escape(str(msg_text))}</pre>\n\n"
                                       f"━━━━━━━━━━━━━━━━━━━━━")
                            
                            requests.post(BASE_URL + "sendMessage", json={
                                "chat_id": TARGET_CHAT,
                                "text": caption,
                                "parse_mode": "HTML",
                                "disable_web_page_preview": True
                            })
                            last_seen_id = msg_id
        except Exception as e:
            print(f"Loop error: {e}")
        
        time.sleep(3)

if __name__ == "__main__":
    main()
