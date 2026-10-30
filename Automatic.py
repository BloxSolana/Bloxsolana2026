import asyncio
import random
import re
import html
import time
import os
import threading
import json
import requests
import websocket
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
from flask import Flask, render_template_string, request, jsonify

# --- CONFIGURATION ---
BOT_TOKEN = "9139656226:AAF3G3Kll7E0DipP80mnXGWvex4BMdEVCzc"
TARGET_CHAT = -1004341368656  # ID Group chính xác của bro
ADMIN_IDS = [6726769296]       # ID Admin tối cao của bro
WEBAPP_URL = "https://bloxsolana2026.onrender.com"  # Link WebApp trên Render

bot = telebot.TeleBot(token=BOT_TOKEN)

# --- DATABASE QUẢN LÝ ---
user_rentals = {}          # {"số_điện_thoại": user_id}
inventory_numbers = {}     # Kho chứa số toàn cầu
admin_state = {}           # Trạng thái chờ nhập của Admin
user_configs = {}          # Cấu hình WSS

user_wallets = {}          # {user_id: {"balance": 0.0, "ref_count": 0, "ref_earnings": 0.0}}
withdrawal_requests = []   # Danh sách đơn rút tiền chờ duyệt

app_stats = {
    "WhatsApp": 0, "ClickBank": 0, "Apple": 0, "Shopee": 0, "Facebook": 0,
    "TikTok": 0, "AUTHMSG": 0, "TALAPH": 0, "Uber": 0, "SPayLaterPH": 0,
    "Telegram": 0, "Google": 0, "Instagram": 0, "Discord": 0, "Zalo": 0
}
top_ranges_data = []
last_reset_time = time.time()

# --- COMPLETE OFFICIAL ISO COUNTRY DATABASE (195+ Quốc gia) ---
country_db = {
    "1": ("USA/Canada", "🇺🇸"), "93": ("Afghanistan", "🇦🇫"), "355": ("Albania", "🇦🇱"), "213": ("Algeria", "🇩🇿"), 
    "376": ("Andorra", "🇦🇩"), "244": ("Angola", "🇦🇴"), "1264": ("Anguilla", "🇦🇮"), "1268": ("Antigua & Barbuda", "🇦🇬"),
    "54": ("Argentina", "🇦🇷"), "374": ("Armenia", "🇦🇲"), "297": ("Aruba", "🇦🇼"), "61": ("Australia", "🇦🇺"),
    "43": ("Austria", "🇦🇹"), "994": ("Azerbaijan", "🇦🇿"), "1242": ("Bahamas", "🇧🇸"), "973": ("Bahrain", "🇧🇭"),
    "880": ("Bangladesh", "🇧🇩"), "1246": ("Barbados", "🇧🇧"), "375": ("Belarus", "🇧🇾"), "32": ("Belgium", "🇧🇪"),
    "501": ("Belize", "🇧🇿"), "229": ("Benin", "🇧🇯"), "1441": ("Bermuda", "🇧🇲"), "975": ("Bhutan", "🇧🇹"),
    "591": ("Bolivia", "🇧🇴"), "387": ("Bosnia", "🇧🇦"), "267": ("Botswana", "🇧🇼"), "55": ("Brazil", "🇧🇷"),
    "673": ("Brunei", "🇧🇳"), "359": ("Bulgaria", "🇧🇬"), "226": ("Burkina Faso", "🇧🇫"), "257": ("Burundi", "🇧🇮"),
    "855": ("Cambodia", "🇰🇭"), "237": ("Cameroon", "🇨🇲"), "238": ("Cape Verde", "🇨🇻"), "1345": ("Cayman Islands", "🇰🇾"),
    "236": ("Central African Rep", "🇨🇫"), "235": ("Chad", "🇹🇩"), "56": ("Chile", "🇨🇱"), "86": ("China", "🇨🇳"),
    "57": ("Colombia", "🇨🇴"), "269": ("Comoros", "🇰🇲"), "242": ("Congo", "🇨🇬"), "243": ("DR Congo", "🇨🇩"),
    "506": ("Costa Rica", "🇨🇷"), "385": ("Croatia", "🇭🇷"), "53": ("Cuba", "🇨🇺"), "357": ("Cyprus", "🇨🇾"),
    "420": ("Czech Republic", "🇨🇿"), "45": ("Denmark", "🇩🇰"), "253": ("Djibouti", "🇩🇯"), "1767": ("Dominica", "🇩🇲"),
    "1849": ("Dominican Rep", "🇩🇴"), "593": ("Ecuador", "🇪🇨"), "20": ("Egypt", "🇪🇬"), "503": ("El Salvador", "🇸🇻"),
    "240": ("Equatorial Guinea", "🇬🇶"), "291": ("Eritrea", "🇪🇷"), "372": ("Estonia", "🇪🇪"), "251": ("Ethiopia", "🇪🇹"),
    "679": ("Fiji", "🇫🇯"), "358": ("Finland", "🇫🇮"), "33": ("France", "🇫🇷"), "594": ("French Guiana", "🇬🇫"),
    "689": ("French Polynesia", "🇵🇫"), "241": ("Gabon", "🇬🇦"), "220": ("Gambia", "🇬🇲"), "995": ("Georgia", "🇬🇪"),
    "49": ("Germany", "🇩🇪"), "233": ("Ghana", "🇬🇭"), "350": ("Gibraltar", "🇬🇮"), "30": ("Greece", "🇬🇷"),
    "299": ("Greenland", "🇬🇱"), "1473": ("Grenada", "🇬🇩"), "590": ("Guadeloupe", "🇬🇵"), "1671": ("Guam", "🇬🇺"),
    "502": ("Guatemala", "🇬🇹"), "224": ("Guinea", "🇬🇳"), "245": ("Guinea-Bissau", "🇬🇼"), "592": ("Guyana", "🇬🇾"),
    "509": ("Haiti", "🇭🇹"), "504": ("Honduras", "🇭🇳"), "852": ("Hong Kong", "🇭🇰"), "36": ("Hungary", "🇭🇺"),
    "354": ("Iceland", "🇮🇸"), "91": ("India", "🇮🇳"), "62": ("Indonesia", "🇮🇩"), "98": ("Iran", "🇮🇷"),
    "964": ("Iraq", "🇮🇶"), "353": ("Ireland", "🇮🇪"), "972": ("Israel", "🇮🇱"), "39": ("Italy", "🇮🇹"),
    "1876": ("Jamaica", "🇯🇲"), "81": ("Japan", "🇯🇵"), "962": ("Jordan", "🇯🇴"), "7": ("Kazakhstan", "🇰🇿"),
    "254": ("Kenya", "🇰🇪"), "686": ("Kiribati", "🇰🇮"), "383": ("Kosovo", "🇽🇰"), "965": ("Kuwait", "🇰🇼"),
    "996": ("Kyrgyzstan", "🇰🇬"), "856": ("Laos", "🇱🇦"), "371": ("Latvia", "🇱🇻"), "961": ("Lebanon", "🇱🇧"),
    "266": ("Lesotho", "🇱🇸"), "231": ("Liberia", "🇱🇷"), "218": ("Libya", "🇱🇾"), "423": ("Liechtenstein", "🇱🇮"),
    "370": ("Lithuania", "🇱🇹"), "352": ("Luxembourg", "🇱🇺"), "853": ("Macau", "🇲🇴"), "389": ("Macedonia", "🇲🇰"),
    "261": ("Madagascar", "🇲🇬"), "265": ("Malawi", "🇲🇼"), "60": ("Malaysia", "🇲🇾"), "960": ("Maldives", "🇲🇻"),
    "223": ("Mali", "🇲🇱"), "356": ("Malta", "🇲🇹"), "692": ("Marshall Islands", "🇲🇭"), "596": ("Martinique", "🇲🇶"),
    "222": ("Mauritania", "🇲🇷"), "230": ("Mauritius", "🇲🇺"), "262": ("Mayotte", "🇾🇹"), "52": ("Mexico", "🇲🇽"),
    "691": ("Micronesia", "🇫🇲"), "373": ("Moldova", "🇲🇩"), "377": ("Monaco", "🇲🇨"), "976": ("Mongolia", "🇲🇳"),
    "382": ("Montenegro", "🇲🇪"), "1664": ("Montserrat", "🇲🇸"), "212": ("Morocco", "🇲🇦"), "258": ("Mozambique", "🇲🇿"),
    "95": ("Myanmar", "🇲🇲"), "264": ("Namibia", "🇳🇦"), "674": ("Nauru", "🇳🇷"), "977": ("Nepal", "🇳🇵"),
    "31": ("Netherlands", "🇳🇱"), "687": ("New Caledonia", "🇳🇨"), "64": ("New Zealand", "🇳🇿"), "505": ("Nicaragua", "🇳🇮"),
    "227": ("Niger", "🇳🇪"), "234": ("Nigeria", "🇳🇬"), "683": ("Niue", "🇳🇺"), "850": ("North Korea", "🇰🇵"),
    "47": ("Norway", "🇳🇴"), "968": ("Oman", "🇴🇲"), "92": ("Pakistan", "🇵🇰"), "680": ("Palau", "🇵🇼"),
    "970": ("Palestine", "🇵🇸"), "507": ("Panama", "🇵🇦"), "675": ("Papua New Guinea", "🇵🇬"), "595": ("Paraguay", "🇵🇾"),
    "51": ("Peru", "🇵🇪"), "63": ("Philippines", "🇵🇭"), "48": ("Poland", "🇵🇱"), "351": ("Portugal", "🇵🇹"),
    "1787": ("Puerto Rico", "🇵🇷"), "974": ("Qatar", "🇶🇦"), "40": ("Romania", "🇷🇴"), "7": ("Russia", "🇷🇺"),
    "250": ("Rwanda", "🇷🇼"), "685": ("Samoa", "🇼🇸"), "378": ("San Marino", "🇸🇲"), "239": ("Sao Tome & Principe", "🇸🇹"),
    "966": ("Saudi Arabia", "🇸🇦"), "221": ("Senegal", "🇸🇳"), "381": ("Serbia", "🇷🇸"), "248": ("Seychelles", "🇸🇨"),
    "232": ("Sierra Leone", "🇸🇱"), "65": ("Singapore", "🇸🇬"), "421": ("Slovakia", "🇸🇰"), "386": ("Slovenia", "🇸🇮"),
    "677": ("Solomon Islands", "🇸🇧"), "252": ("Somalia", "🇸🇴"), "27": ("South Africa", "🇿🇦"), "82": ("South Korea", "🇰🇷"),
    "211": ("South Sudan", "🇸🇸"), "34": ("Spain", "🇪🇸"), "94": ("Sri Lanka", "🇱🇰"), "249": ("Sudan", "🇸🇩"),
    "597": ("Suriname", "🇸🇷"), "268": ("Swaziland", "🇸🇿"), "46": ("Sweden", "🇸🇪"), "41": ("Switzerland", "🇨🇭"),
    "963": ("Syria", "🇸🇾"), "886": ("Taiwan", "🇹🇼"), "992": ("Tajikistan", "🇹🇯"), "255": ("Tanzania", "🇹🇿"),
    "66": ("Thailand", "🇹🇭"), "670": ("Timor-Leste", "🇹🇱"), "228": ("Togo", "🇹🇬"), "690": ("Tokelau", "🇹🇰"),
    "676": ("Tonga", "🇹🇴"), "1868": ("Trinidad & Tobago", "🇹🇹"), "216": ("Tunisia", "🇹🇳"), "90": ("Turkey", "🇹🇷"),
    "993": ("Turkmenistan", "🇹🇲"), "1649": ("Turks & Caicos", "🇹🇨"), "688": ("Tuvalu", "🇹🇻"), "256": ("Uganda", "🇺🇬"),
    "380": ("Ukraine", "🇺🇦"), "971": ("UAE", "🇦🇪"), "44": ("United Kingdom", "🇬🇧"), "598": ("Uruguay", "🇺🇾"),
    "998": ("Uzbekistan", "🇺🇿"), "678": ("Vanuatu", "🇻🇺"), "379": ("Vatican City", "🇻🇦"), "58": ("Venezuela", "🇻🇪"),
    "84": ("Vietnam", "🇻🇳"), "1284": ("Virgin Islands (UK)", "🇻🇬"), "1340": ("Virgin Islands (US)", "🇻🇮"),
    "967": ("Yemen", "🇾🇪"), "260": ("Zambia", "🇿🇲"), "263": ("Zimbabwe", "🇿🇼")
}

for code, (cname, flag) in country_db.items():
    full_key = f"{cname} {flag}"
    if full_key not in inventory_numbers:
        inventory_numbers[full_key] = {"flag": flag, "name": cname, "numbers": []}

def detect_country_info(phone_str):
    clean = re.sub(r'\D', '', phone_str)
    for length in range(4, 0, -1):
        prefix = clean[:length]
        if prefix in country_db:
            cname, flag = country_db[prefix]
            return cname, flag, f"{cname} {flag}"
    return "Unknown", "🌐", "Unknown 🌐"

def parse_service_name(msg_text):
    text_upper = str(msg_text).upper()
    if "WHATSAPP" in text_upper: return "WhatsApp"
    elif "TELEGRAM" in text_upper: return "Telegram"
    elif "FACEBOOK" in text_upper or "FB" in text_upper: return "Facebook"
    elif "TIKTOK" in text_upper: return "TikTok"
    elif "SHOPEE" in text_upper: return "Shopee"
    elif "PAYPAL" in text_upper: return "PayPal"
    elif "UBER" in text_upper: return "Uber"
    elif "APPLE" in text_upper or "ICLOUD" in text_upper: return "Apple"
    elif "GOOGLE" in text_upper or "G-" in text_upper: return "Google"
    elif "INSTAGRAM" in text_upper or "IG" in text_upper: return "Instagram"
    elif "DISCORD" in text_upper: return "Discord"
    elif "ZALO" in text_upper: return "Zalo"
    return "AUTHMSG"

def get_reply_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("LIVE NUMBER"), KeyboardButton("LIVE TRAFFIC"))
    markup.add(KeyboardButton("INVITE FRIEND"), KeyboardButton("WALLET"))
    markup.add(KeyboardButton("LEADERBOARD"))
    return markup

def get_menu_keyboard(user_id):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("🚀 OPEN WEB APP PORTAL", web_app=WebAppInfo(url=WEBAPP_URL)))
    kb.add(InlineKeyboardButton("📦 LIVE STOCK (195+)", callback_data="menu_live_number"))
    if user_id in ADMIN_IDS:
        kb.add(InlineKeyboardButton("👑 DUYỆT RÚT TIỀN (ADMIN)", callback_data="admin_withdrawals"))
        kb.add(InlineKeyboardButton("⚙️ TẠO WSS CONFIG", callback_data="menu_create_config"))
    return kb

@bot.message_handler(commands=['start'])
def send_welcome(message):
    uid = message.from_user.id
    if uid not in user_wallets:
        user_wallets[uid] = {"balance": 0.0, "ref_count": 0, "ref_earnings": 0.0}
    
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref"):
        try:
            ref_id = int(args[1].replace("ref", ""))
            if ref_id in user_wallets and ref_id != uid:
                user_wallets[ref_id]["ref_count"] += 1
                user_wallets[ref_id]["balance"] += 0.005
                user_wallets[ref_id]["ref_earnings"] += 0.005
        except:
            pass

    welcome_text = (
        "🔥 <b>FAST NODE • IVAS OTP GATEWAY PORTAL</b>\n\n"
        "Welcome to the ultimate real-time secure OTP platform!"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="HTML", reply_markup=get_menu_keyboard(uid))
    bot.send_message(message.chat.id, "👇 Use the quick menu below:", reply_markup=get_reply_keyboard())

@bot.message_handler(func=lambda msg: msg.text in ["LIVE NUMBER", "LIVE TRAFFIC", "INVITE FRIEND", "WALLET", "LEADERBOARD"])
def handle_reply_buttons(message):
    uid = message.from_user.id
    if uid not in user_wallets:
        user_wallets[uid] = {"balance": 0.0, "ref_count": 0, "ref_earnings": 0.0}
        
    text = message.text
    if text == "LIVE NUMBER":
        available_total = sum(1 for data in inventory_numbers.values() for item in data["numbers"] if not item.get("locked_by"))
        bot.reply_to(message, f"🌍 <b>LIVE STOCK (195+ Countries):</b>\n\n📦 Available numbers: <code>{available_total}</code>\nOpen Web App to get numbers!", parse_mode="HTML")
    elif text == "LIVE TRAFFIC":
        bot.reply_to(message, "📈 <b>LIVE TRAFFIC MONITOR:</b>\n\nAll systems operating normally via Fast Node Gateway v3 API.", parse_mode="HTML")
    elif text == "INVITE FRIEND":
        ref_link = f"https://t.me/FastNode_Bot?start=ref{uid}"
        bot.reply_to(message, f"👥 <b>REFERRAL PROGRAM</b>\n\nInvite friends and earn <b>$0.005</b> per referral!\n\n🔗 Your Link:\n<code>{ref_link}</code>\n\n📊 Total Invited: <b>{user_wallets[uid]['ref_count']}</b>\n💰 Total Earned: <b>${user_wallets[uid]['ref_earnings']:.3f}</b>", parse_mode="HTML")
    elif text == "WALLET":
        bal = user_wallets[uid]["balance"]
        bot.reply_to(message, f"💳 <b>YOUR WALLET</b>\n\n💰 Balance: <b>${bal:.3f} USDT</b>\nMin withdraw: $5.00 (TON Network).", parse_mode="HTML")
    elif text == "LEADERBOARD":
        bot.reply_to(message, f"🏆 <b>GLOBAL LEADERBOARD</b>\n\n1. K.Bro - $145.50\n2. FastNode - $98.20\n3. You - ${user_wallets[uid]['balance']:.3f}", parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    if call.data == "menu_live_number":
        available_total = sum(1 for data in inventory_numbers.values() for item in data["numbers"] if not item.get("locked_by"))
        text = f"🌍 <b>LIVE STOCK (195+ Countries):</b>\n\n📦 Available numbers: <code>{available_total}</code>"
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔙 BACK", callback_data="menu_back"))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode="HTML", reply_markup=kb)

    elif call.data == "menu_create_config":
        if user_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "⛔ Access denied!", show_alert=True)
            return
        admin_state[user_id] = "waiting_for_ws"
        text = "🔮 <b>Setup WSS Configuration</b>\n\nSend your WebSocket URL or Cookie string here:"
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("❌ CANCEL", callback_data="menu_back"))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode="HTML", reply_markup=kb)

    elif call.data == "admin_withdrawals":
        if user_id not in ADMIN_IDS: return
        if not withdrawal_requests:
            text = "📂 <b>Không có đơn rút tiền nào đang chờ duyệt!</b>"
        else:
            text = f"📂 <b>DANH SÁCH ĐƠN RÚT TIỀN ({len(withdrawal_requests)} đơn):</b>\n\n"
            for idx, req in enumerate(withdrawal_requests):
                text += f"🆔 <b>STT {idx+1}</b> | User ID: <code>{req['user_id']}</code>\n👤 Tên: {req['name']}\n💵 Số tiền: <b>${req['amount']}</b>\n📬 Ví TON: <code>{req['address']}</code>\n⏰ Lúc: {req['time']}\n━━━━━━━━━━━━━━━━━━━━━\n"
        kb = InlineKeyboardMarkup()
        if withdrawal_requests:
            kb.add(InlineKeyboardButton("✅ DUYỆT ĐƠN ĐẦU TIÊN", callback_data="approve_first_wd"))
        kb.add(InlineKeyboardButton("🔙 QUAY LẠI", callback_data="menu_back"))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode="HTML", reply_markup=kb)

    elif call.data == "approve_first_wd":
        if user_id not in ADMIN_IDS: return
        if withdrawal_requests:
            req = withdrawal_requests.pop(0)
            bot.send_message(req['user_id'], f"🎉 <b>Đơn rút ${req['amount']} USDT (TON) của bạn đã được Admin duyệt thành công!</b>", parse_mode="HTML")
            bot.answer_callback_query(call.id, "Đã duyệt đơn thành công!")
        handle_callback(type('obj', (object,), {'from_user': call.from_user, 'message': call.message, 'data': 'admin_withdrawals'})())

    elif call.data == "menu_back":
        admin_state.pop(user_id, None)
        welcome_text = "🔥 <b>FAST NODE • IVAS OTP GATEWAY PORTAL</b>\n\nWelcome to the ultimate real-time secure OTP platform!"
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=welcome_text, parse_mode="HTML", reply_markup=get_menu_keyboard(user_id))

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    current_state = admin_state.get(user_id)
    chat_id = message.chat.id
    
    if current_state == "waiting_for_ws" and user_id in ADMIN_IDS:
        text_input = message.text.strip()
        ws_match = re.search(r'(wss?://[^\s\'"]+)', text_input)
        token_match = re.search(r'(?:token=|access_token=|key=)([a-zA-Z0-9_\-\.]+)', text_input)
        user_configs[user_id] = {
            "ws_url": ws_match.group(1) if ws_match else "Custom Session",
            "token": token_match.group(1) if token_match else text_input[:20],
            "balance": "$0.00"
        }
        admin_state.pop(user_id, None)
        bot.reply_to(message, "✅ WebSocket WSS Configuration saved successfully!", parse_mode="HTML", reply_markup=get_reply_keyboard())
        return

    if user_id in ADMIN_IDS and current_state == "waiting_for_numbers":
        phones = re.split(r'[\s,\n]+', message.text)
        total_added = 0
        for phone in phones:
            cleaned = phone.replace("+", "").strip()
            if cleaned.isdigit() and len(cleaned) >= 5:
                _, _, full_key = detect_country_info(cleaned)
                if full_key not in inventory_numbers:
                    cname, flag = detect_country_info(cleaned)[:2]
                    inventory_numbers[full_key] = {"flag": flag, "name": cname, "numbers": []}
                if cleaned not in [i["phone"] for i in inventory_numbers[full_key]["numbers"]]:
                    inventory_numbers[full_key]["numbers"].append({"phone": cleaned, "expires": 0, "locked_by": None})
                    total_added += 1
        admin_state.pop(user_id, None)
        bot.reply_to(message, f"✅ Added {total_added} numbers to inventory successfully!", parse_mode="HTML", reply_markup=get_reply_keyboard())

@bot.message_handler(commands=['thue'])
def handle_rent_number(message):
    parts = message.text.split()
    if len(parts) < 2: return
    phone_to_rent = parts[1].replace("+", "").strip()
    user_id = message.chat.id
    user_rentals[phone_to_rent] = user_id
    
    for key, data in inventory_numbers.items():
        for item in data["numbers"]:
            if item["phone"] == phone_to_rent:
                item["expires"] = time.time() + 900
                item["locked_by"] = user_id
                break
    bot.reply_to(message, f"✅ Successfully rented number <code>{phone_to_rent}</code> for 15 minutes! OTP will be delivered here privately.", parse_mode="HTML")

def background_cleanup_and_wss():
    global last_reset_time, app_stats
    while True:
        current_time = time.time()
        if current_time - last_reset_time > 86400:
            for k in app_stats: app_stats[k] = 0
            last_reset_time = current_time

        for key, data in inventory_numbers.items():
            for item in list(data["numbers"]):
                if item["expires"] > 0 and item["expires"] <= current_time:
                    user_rentals.pop(item["phone"], None)
                    data["numbers"].remove(item)
        time.sleep(30)

async def dispatch_update(service, phone, msg, timestamp, country, flag, is_test=False):
    global app_stats, top_ranges_data
    clean_phone = str(phone).replace("+", "")
    masked = clean_phone[:6] + "****" + clean_phone[-3:] if len(clean_phone) > 7 else clean_phone
    match = re.search(r'\d{3}[-\s]?\d{3}|\d{4,8}', str(msg))
    code = match.group(0) if match else "N/A"

    detected_service = parse_service_name(f"{service} {msg}")
    if detected_service in app_stats:
        app_stats[detected_service] += 1
    else:
        app_stats["AUTHMSG"] += 1

    range_prefix = clean_phone[:5]
    existing_range = next((r for r in top_ranges_data if r['range'] == range_prefix), None)
    if existing_range:
        existing_range['count'] += 1
    else:
        top_ranges_data.append({"country": country, "range": range_prefix, "flag": flag, "count": 1})
    top_ranges_data.sort(key=lambda x: x['count'], reverse=True)
    if len(top_ranges_data) > 5: top_ranges_data = top_ranges_data[:5]

    if clean_phone in user_rentals:
        owner_id = user_rentals[clean_phone]
        if owner_id in user_wallets:
            user_wallets[owner_id]["balance"] += 0.008

    header = "🧪 <b>『 ꜰᴇ ꜱᴇɴᴅ ᴏᴛᴘ 』</b> 🧪" if is_test else "💐 <b>『 ɴᴇᴡ ᴏᴛᴘ ʀᴇᴄᴇɪᴠᴇᴅ 』</b> ✨"
    caption = (f"{header}\n"
               f"━━━━━━━━━━━━━━━━━━━━━\n\n"
               f"<b>⌚ TIME:</b> <code>{html.escape(str(timestamp))}</code>\n"
               f"<b>🌍 COUNTRY:</b> {html.escape(str(country))} {flag}\n"
               f"<b>📱 NUMBER:</b> <code>{html.escape(str(masked))}</code>\n"
               f"<b>🛠 SERVICE:</b> <code>{html.escape(str(detected_service))}</code>\n"
               f"<b>🔑 CODE:</b> <code>{html.escape(str(code))}</code>\n\n"
               f"<b>💬 MESSAGE:</b>\n<pre>{html.escape(str(msg))}</pre>\n\n"
               f"━━━━━━━━━━━━━━━━━━━━━")
    
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("✨ YouTube", url="https://youtube.com/@ThoKho_VN"),
        InlineKeyboardButton("👑 Owner", url="https://t.me/Nothavedie")
    )
    kb.row(
        InlineKeyboardButton("📥 OTP Channel", url="https://t.me/LIVEOTPIVAS"),
        InlineKeyboardButton("🎀 Main Channel", url="https://t.me/FastNode_1")
    )
    
    try:
        await asyncio.to_thread(bot.send_message, chat_id=TARGET_CHAT, text=caption, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)
    except Exception as e: pass

    if clean_phone in user_rentals:
        owner_id = user_rentals[clean_phone]
        private_caption = f"🔔 <b>[REAL-TIME PRIVATE EXCLUSIVE OTP ($0.008 EARNED)]</b>\n\n" + caption
        try:
            await asyncio.to_thread(bot.send_message, chat_id=owner_id, text=private_caption, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)
        except Exception as e: pass

def websocket_worker():
    def on_message(ws, message):
        try:
            data = json.loads(message)
            phone = data.get("phone", "84939168914")
            service = data.get("service", "WhatsApp")
            msg = data.get("message", "Your verification code is 790-937")
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            cname, flag, _ = detect_country_info(phone)
            asyncio.run(dispatch_update(service, phone, msg, timestamp, cname, flag, is_test=False))
        except: pass
    def on_error(ws, error): pass
    def on_close(ws, c, m): time.sleep(10)
    def on_open(ws): print("🟢 WebSocket Connected Real-time!")

    while True:
        for uid, cfg in user_configs.items():
            ws_url = cfg.get("ws_url")
            if ws_url and ws_url.startswith("wss://"):
                try:
                    wsapp = websocket.WebSocketApp(ws_url, on_open=on_open, on_message=on_message, on_error=on_error, on_close=on_close)
                    wsapp.run_forever()
                except: pass
        time.sleep(15)

# --- FLASK SERVER & WEB APP ---
app = Flask(__name__)

@app.route('/')
def home():
    countries_data = []
    for key, data in inventory_numbers.items():
        available_numbers = [{"phone": item["phone"], "expires": item["expires"]} for item in data["numbers"] if not item.get("locked_by")]
        countries_data.append({"key": key, "name": data["name"], "flag": data["flag"], "numbers": available_numbers})
    
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Fast Node • Portal Dashboard</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            :root { --bg: #0f172a; --card: #1e293b; --orange-bar: #f59e0b; --border: #334155; --text: #f8fafc; --muted: #94a3b8; --green: #22c55e; --red: #ef4444; }
            body { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 0; }
            
            .top-bar { background: var(--orange-bar); color: #000; padding: 12px 16px; font-weight: bold; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 100; }
            .hamburger-btn { background: none; border: none; font-size: 20px; cursor: pointer; color: #000; font-weight: bold; }
            
            .sidebar { position: fixed; top: 0; left: -260px; width: 250px; height: 100%; background: #131c2e; border-right: 1px solid var(--border); transition: 0.3s ease; z-index: 1000; padding-top: 20px; box-shadow: 4px 0 15px rgba(0,0,0,0.5); }
            .sidebar.open { left: 0; }
            .sidebar-header { padding: 0 16px 15px 16px; border-bottom: 1px solid var(--border); font-size: 16px; font-weight: bold; color: #38bdf8; display: flex; justify-content: space-between; align-items: center; }
            .menu-link { display: block; padding: 14px 16px; color: var(--text); text-decoration: none; font-weight: bold; font-size: 14px; border-bottom: 1px solid var(--border); cursor: pointer; transition: 0.2s; }
            .menu-link:hover { background: #1e293b; color: #38bdf8; }

            .content-container { padding: 12px; }
            .view-section { display: none; }
            .view-section.active { display: block; }

            .dashboard-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 10px; margin-bottom: 12px; }
            @media(max-width: 600px) { .dashboard-grid { grid-template-columns: 1fr; } }

            .widget-card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 14px; margin-bottom: 12px; }
            .widget-title { font-size: 14px; font-weight: bold; color: #f59e0b; margin-bottom: 10px; border-bottom: 1px solid var(--border); padding-bottom: 6px; }

            .apps-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
            .app-box { background: #131c2e; border: 1px solid var(--border); border-radius: 8px; padding: 8px; text-align: center; font-size: 11px; }
            .app-box b { display: block; font-size: 12px; color: #38bdf8; margin-top: 2px; }

            .range-item { display: flex; align-items: center; justify-content: space-between; background: #131c2e; border: 1px solid var(--border); padding: 8px; border-radius: 6px; margin-bottom: 6px; font-size: 12px; }

            .grid-countries { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; }
            .country-pill { background: #131c2e; border: 1px solid var(--border); border-radius: 6px; padding: 6px 2px; text-align: center; cursor: pointer; font-size: 10px; }
            .country-pill:hover { border-color: #38bdf8; }

            .number-item { display: flex; justify-content: space-between; align-items: center; background: #131c2e; border: 1px solid var(--border); padding: 8px; border-radius: 6px; margin-bottom: 6px; font-size: 13px; }
            .btn { background: var(--green); color: white; border: none; border-radius: 6px; padding: 8px 14px; font-size: 13px; font-weight: bold; cursor: pointer; width: 100%; margin-top: 8px; }
            .btn-red { background: var(--red); }
            .btn-gray { background: #475569; }

            .input-box { width: 100%; padding: 10px; background: #0f172a; border: 1px solid var(--border); border-radius: 8px; color: white; margin-bottom: 10px; box-sizing: border-box; font-size: 14px; }
            .warning-box { background: rgba(239, 68, 68, 0.1); border: 1px solid var(--red); padding: 10px; border-radius: 8px; font-size: 12px; color: #fca5a5; margin-bottom: 10px; line-height: 1.4; }
        </style>
    </head>
    <body>
        <div class="top-bar">
            <div style="display:flex; align-items:center; gap:10px;">
                <button class="hamburger-btn" onclick="toggleSidebar()">☰</button>
                <span>Fast Node • Portal</span>
            </div>
            <span id="headerBalance">Balance: $0.000</span>
        </div>

        <div class="sidebar" id="sidebarDrawer">
            <div class="sidebar-header">
                <span>📁 Menu</span>
                <span style="cursor:pointer; font-size:18px;" onclick="toggleSidebar()">✕</span>
            </div>
            <a class="menu-link" onclick="switchView('dashboardView')">📊 Dashboard</a>
            <a class="menu-link" onclick="switchView('getNumberView')">🌍 Get Number (195+)</a>
            <a class="menu-link" onclick="switchView('withdrawView')">💸 Withdraw (TON USDT)</a>
            <a class="menu-link" onclick="switchView('referralView')">👥 Referral Program</a>
            <a class="menu-link" onclick="window.open('https://t.me/LIVEOTPIVAS', '_blank')">📢 Official Channel</a>
            <a class="menu-link" style="color:var(--red);" onclick="exitApp()">❌ Exit App</a>
        </div>

        <div class="content-container">
            
            <div id="dashboardView" class="view-section active">
                <div class="dashboard-grid">
                    <div class="widget-card">
                        <div class="widget-title">Top Applications Access (Real-time & 24h Reset)</div>
                        <div class="apps-grid" id="appsGrid"></div>
                    </div>
                    <div class="widget-card">
                        <div class="widget-title">🔥 Top Ranges (Real-time Active)</div>
                        <div id="topRangesContainer">
                            <p style="font-size:11px; color:var(--muted); text-align:center;">No active ranges yet.</p>
                        </div>
                    </div>
                </div>
            </div>

            <div id="getNumberView" class="view-section">
                <div class="widget-card" id="marketplaceSection">
                    <div class="widget-title">Get Number • 195+ Countries Marketplace</div>
                    <div class="grid-countries" id="countryGrid"></div>
                </div>

                <div class="widget-card" id="detailCard" style="display:none;">
                    <h3 id="detailTitleText" style="color:#38bdf8; font-size:14px; margin-bottom:8px;">Number Details</h3>
                    <div id="numberListContainer"></div>
                    <div style="display:flex; gap:6px; margin-top:10px;">
                        <button class="btn btn-gray" onclick="goBackToGrid()">🔙 Back</button>
                        <button class="btn" onclick="location.reload()">🔄 Refresh</button>
                    </div>
                </div>
            </div>

            <div id="withdrawView" class="view-section">
                <div class="widget-card">
                    <div class="widget-title">💸 Withdraw USDT (TON Network)</div>
                    <div class="warning-box">
                        <b>⚠️ IMPORTANT RULES & REGULATIONS:</b><br>
                        • Minimum withdrawal amount: <b>$5.00</b>.<br>
                        • Only enter a valid <b>TON network USDT address</b> (must start with EQ or UQ).<br>
                        • <b>WARNING:</b> Incorrect network/address means permanent loss of funds!
                    </div>
                    <div style="font-size: 13px; margin-bottom: 6px; color: var(--muted);">Your Balance: <b id="withdrawBalance" style="color:var(--green);">$0.000</b></div>
                    <input type="number" id="withdrawAmount" class="input-box" placeholder="Min $5.00">
                    <input type="text" id="tonAddress" class="input-box" placeholder="TON Address (EQ... / UQ...)">
                    <button class="btn" onclick="requestWithdraw()">Submit Withdrawal Request</button>
                </div>
            </div>

            <div id="referralView" class="view-section">
                <div class="widget-card">
                    <div class="widget-title">👥 Referral Program & Earnings</div>
                    <p style="font-size: 13px; color: var(--muted); line-height: 1.4;">
                        Invite friends using your link. Earn <b>$0.005</b> for every active user!
                    </p>
                    <div style="margin: 12px 0;">
                        <label style="font-size: 12px; color: var(--muted);">Your Referral Link:</label>
                        <input type="text" id="refLinkInput" class="input-box" readonly style="background:#0f172a; color:#38bdf8; margin-top:4px;">
                    </div>
                    <div style="display: flex; gap: 10px; margin-top: 10px;">
                        <div class="widget-card" style="flex:1; text-align:center; margin:0;">
                            <div style="font-size: 11px; color: var(--muted);">Invited Friends</div>
                            <div id="refCountDisplay" style="font-size: 18px; font-weight: bold; color: #38bdf8; margin-top: 4px;">0</div>
                        </div>
                        <div class="widget-card" style="flex:1; text-align:center; margin:0;">
                            <div style="font-size: 11px; color: var(--muted);">Total Earned</div>
                            <div id="refEarningsDisplay" style="font-size: 18px; font-weight: bold; color: var(--green); margin-top: 4px;">$0.000</div>
                        </div>
                    </div>
                </div>
            </div>

        </div>

        <script>
            let tg = window.Telegram.WebApp;
            tg.expand();

            let userBalance = 0.000;
            let refCount = 0;
            let refEarnings = 0.000;
            let userTgId = tg.initDataUnsafe && tg.initDataUnsafe.user ? tg.initDataUnsafe.user.id : "123456";

            document.getElementById('refLinkInput').value = `https://t.me/FastNode_Bot?start=ref${userTgId}`;

            let appStats = {{ app_stats | tojson }};
            let topRanges = {{ top_ranges_data | tojson }};
            let countriesData = {{ countries_data | tojson }};
            let currentSelectedCountry = null;

            function toggleSidebar() {
                document.getElementById('sidebarDrawer').classList.toggle('open');
            }

            function switchView(viewId) {
                document.querySelectorAll('.view-section').forEach(el => el.classList.remove('active'));
                document.getElementById(viewId).classList.add('active');
                toggleSidebar();
            }

            function exitApp() { tg.close(); }

            function updateWalletUI() {
                document.getElementById('headerBalance').innerText = `Balance: $${userBalance.toFixed(3)}`;
                document.getElementById('withdrawBalance').innerText = `$${userBalance.toFixed(3)}`;
                document.getElementById('refCountDisplay').innerText = refCount;
                document.getElementById('refEarningsDisplay').innerText = `$${refEarnings.toFixed(3)}`;
            }

            function renderApps() {
                let grid = document.getElementById('appsGrid');
                grid.innerHTML = '';
                for (let [appName, count] of Object.entries(appStats)) {
                    let div = document.createElement('div');
                    div.className = 'app-box';
                    div.innerHTML = `✉️ <div>${appName}</div><b>${count} msg</b>`;
                    grid.appendChild(div);
                }
            }

            function renderTopRanges() {
                let container = document.getElementById('topRangesContainer');
                container.innerHTML = '';
                if (!topRanges || topRanges.length === 0) {
                    container.innerHTML = '<p style="font-size:11px; color:var(--muted); text-align:center;">No active ranges yet.</p>';
                    return;
                }
                topRanges.forEach(r => {
                    let div = document.createElement('div');
                    div.className = 'range-item';
                    div.innerHTML = `<span>${r.flag} <b>${r.country}</b></span> <span style="color:var(--green); font-weight:bold;">${r.range} (${r.count})</span>`;
                    container.appendChild(div);
                });
            }

            function renderCountries() {
                let grid = document.getElementById('countryGrid');
                grid.innerHTML = '';
                countriesData.forEach(c => {
                    let div = document.createElement('div');
                    div.className = 'country-pill';
                    div.innerHTML = `<span style="font-size:14px; display:block;">${c.flag}</span><div style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${c.name}</div><div style="color:var(--green); font-weight:bold;">${c.numbers.length}</div>`;
                    div.onclick = () => selectCountry(c.key);
                    grid.appendChild(div);
                });
            }

            function selectCountry(key) {
                currentSelectedCountry = countriesData.find(c => c.key === key);
                document.getElementById('detailTitleText').innerText = `${currentSelectedCountry.flag} ${currentSelectedCountry.name} (${currentSelectedCountry.numbers.length} Available)`;
                document.getElementById('detailCard').style.display = 'block';
                renderNumbers();
            }

            function renderNumbers() {
                let container = document.getElementById('numberListContainer');
                container.innerHTML = '';
                if (!currentSelectedCountry || currentSelectedCountry.numbers.length === 0) {
                    container.innerHTML = '<p style="color:var(--muted); text-align:center; font-size:12px;">No available numbers in this country!</p>';
                    return;
                }
                currentSelectedCountry.numbers.forEach(item => {
                    let row = document.createElement('div');
                    row.className = 'number-item';
                    row.innerHTML = `<span><b>${item.phone}</b></span> <button class="btn" style="width:auto; margin:0; padding:6px 12px;" onclick="rentNumber('${item.phone}')">Rent 15m</button>`;
                    container.appendChild(row);
                });
            }

            function goBackToGrid() {
                document.getElementById('detailCard').style.display = 'none';
                currentSelectedCountry = null;
            }

            function rentNumber(phone) {
                tg.sendData(`/thue ${phone}`);
                tg.showAlert(`Successfully rented number ${phone} for 15 minutes!`);
                tg.close();
            }

            function requestWithdraw() {
                let amount = parseFloat(document.getElementById('withdrawAmount').value);
                let address = document.getElementById('tonAddress').value.trim();

                if (isNaN(amount) || amount < 5) {
                    tg.showAlert("Minimum withdrawal amount is $5.00!");
                    return;
                }
                if (amount > userBalance) {
                    tg.showAlert("Insufficient balance!");
                    return;
                }
                if (!address.startsWith("EQ") && !address.startsWith("UQ") || address.length < 40) {
                    tg.showAlert("Invalid TON USDT address! Must start with EQ or UQ.");
                    return;
                }

                tg.showConfirm(`Withdraw $${amount} to TON address:\\n${address}?`, (confirmed) => {
                    if (confirmed) {
                        userBalance -= amount;
                        updateWalletUI();
                        fetch('/api/withdraw', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({user_id: userTgId, amount: amount, address: address})
                        }).then(res => res.json()).then(data => {
                            tg.showAlert("Withdrawal request submitted successfully!");
                        }).catch(() => {
                            tg.showAlert("Withdrawal request recorded!");
                        });
                    }
                });
            }

            renderApps();
            renderTopRanges();
            renderCountries();
            updateWalletUI();
        </script>
    </body>
    </html>
    """, app_stats=app_stats, top_ranges_data=top_ranges_data, countries_data=countries_data)

@app.route('/api/withdraw', methods=['POST'])
def api_withdraw():
    data = request.json
    uid = data.get("user_id")
    amount = data.get("amount")
    address = data.get("address")
    
    withdrawal_requests.append({
        "user_id": uid, "name": f"User_{uid}", "amount": amount, "address": address, "time": time.strftime("%Y-%m-%d %H:%M:%S")
    })
    
    try:
        bot.send_message(ADMIN_IDS[0], f"🚨 <b>CÓ ĐƠN RÚT TIỀN MỚI!</b>\n\n👤 User ID: <code>{uid}</code>\n💵 Số tiền: <b>${amount}</b>\n📬 Ví TON: <code>{address}</code>\n⏰ Lúc: {time.strftime('%Y-%m-%d %H:%M:%S')}", parse_mode="HTML")
    except: pass
    return jsonify({"success": True})

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def run_bot_polling():
    while True:
        try:
            bot.remove_webhook()
            requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset=-1")
            time.sleep(1)
            print("🚀 Telegram Bot Polling Started Successfully!")
            bot.infinity_polling(skip_pending=True, interval=0, timeout=20)
        except Exception as e:
            print(f"⚠️ Bot polling restart due to error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    t_web = threading.Thread(target=run_web, daemon=True)
    t_web.start()
    
    t_wss = threading.Thread(target=websocket_worker, daemon=True)
    t_wss.start()

    t_clean = threading.Thread(target=background_cleanup_and_wss, daemon=True)
    t_clean.start()
    
    run_bot_polling()
