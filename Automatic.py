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
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
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

# Thống kê Top Applications Access & Top Ranges (Tự reset sau 24h)
app_stats = {
    "WhatsApp": 23961, "ClickBank": 10036, "Apple": 8077, "Shopee": 8059, "Facebook": 6523,
    "TikTok": 6598, "AUTHMSG": 5115, "TALAPH": 4989, "Uber": 4185, "SPayLaterPH": 1992,
    "Telegram": 4500, "Google": 3800, "Instagram": 3400, "Discord": 2100, "Zalo": 1800
}
top_ranges_data = [
    {"country": "Indonesia", "range": "149072", "flag": "🇮🇩"},
    {"country": "Indonesia", "range": "52520", "flag": "🇮🇩"},
    {"country": "Indonesia", "range": "77749", "flag": "🇮🇩"},
    {"country": "Indonesia", "range": "168111", "flag": "🇮🇩"},
    {"country": "Mozambique", "range": "1671", "flag": "🇲🇿"}
]
last_reset_time = time.time()

# --- COMPLETE OFFICIAL ISO COUNTRY DATABASE (Chuẩn 195+ Quốc gia) ---
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
    "998": ("Uzbekistan", "UZ"), "678": ("Vanuatu", "🇻🇺"), "379": ("Vatican City", "🇻🇦"), "58": ("Venezuela", "🇻🇪"),
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

# --- HÀM THÔNG MINH NHẬN DIỆN PLATFORM / SERVICE TỪ NỘI DUNG TIN NHẮN (Chuẩn code của bro) ---
def parse_service_name(msg_text):
    text_upper = str(msg_text).upper()
    service_name = "Other Service"
    
    if "WHATSAPP" in text_upper:
        service_name = "WhatsApp"
    elif "TELEGRAM" in text_upper:
        service_name = "Telegram"
    elif "FACEBOOK" in text_upper or "MA FACEBOOK" in text_upper or "FB" in text_upper:
        service_name = "Facebook"
    elif "TIKTOK" in text_upper:
        service_name = "TikTok"
    elif "SHOPEE" in text_upper:
        service_name = "Shopee"
    elif "PAYPAL" in text_upper:
        service_name = "PayPal"
    elif "UBER" in text_upper:
        service_name = "Uber"
    elif "APPLE" in text_upper or "ICLOUD" in text_upper:
        service_name = "Apple"
    elif "YANGO" in text_upper:
        service_name = "Yango"
    elif "MICROSOFT" in text_upper or "MS" in text_upper:
        service_name = "Microsoft"
    elif "AUTHMSG" in text_upper:
        service_name = "AUTHMSG"
    elif "TENCENT" in text_upper:
        service_name = "Tencent"
    elif "AMAZON" in text_upper:
        service_name = "Amazon"
    elif "LALAMOVE" in text_upper:
        service_name = "Lalamove"
    elif "PTAK" in text_upper:
        service_name = "PTAK"
    elif "NETFLIX" in text_upper:
        service_name = "Netflix"
    elif "MELBET" in text_upper:
        service_name = "Melbet"
    elif "TWVERIFY" in text_upper or "TWITTER" in text_upper or "X.COM" in text_upper:
        service_name = "TWverify"
    elif "MSVERIFY" in text_upper:
        service_name = "MSVERIFY"
    elif "NCSOFT" in text_upper:
        service_name = "NCSOFT"
    elif "GOOGLE" in text_upper or "G-" in text_upper:
        service_name = "Google"
    elif "INSTAGRAM" in text_upper or "IG" in text_upper:
        service_name = "Instagram"
    elif "DISCORD" in text_upper:
        service_name = "Discord"
    elif "ZALO" in text_upper:
        service_name = "Zalo"
    elif "VERIFY" in text_upper:
        service_name = "VERIFY"
        
    return service_name

def get_menu_keyboard(user_id):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🚀 MỞ GIAO DIỆN WEB APP", web_app=WebAppInfo(url=WEBAPP_URL))
    )
    kb.add(
        InlineKeyboardButton("📦 KHO SỐ (195+)", callback_data="menu_live_number"),
        InlineKeyboardButton("📈 TRẠNG THÁI", callback_data="menu_live_traffic")
    )
    if user_id in ADMIN_IDS:
        kb.add(
            InlineKeyboardButton("⚙️ TẠO WSS CONFIG", callback_data="menu_create_config"),
            InlineKeyboardButton("📂 CẤU HÌNH CỦA TÔI", callback_data="menu_my_configs")
        )
        kb.add(
            InlineKeyboardButton("👑 BẢNG ĐIỀU KHIỂN (OWNER)", callback_data="menu_owner")
        )
    return kb

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "🔥 <b>FAST NODE • IVAS OTP GATEWAY</b>\n\n"
        "Chào mừng bạn đến với hệ thống quản lý OTP & Stock số 195+ quốc gia!"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="HTML", reply_markup=get_menu_keyboard(message.from_user.id))

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    if call.data == "menu_live_number":
        available_total = sum(1 for data in inventory_numbers.values() for item in data["numbers"] if not item.get("locked_by"))
        text = f"🌍 <b>KHO SỐ KHẢ DỤNG (195+ Quốc Gia):</b>\n\n📦 Tổng số lượng số: <code>{available_total}</code> số.\nHãy mở Web App để chọn số!"
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔙 QUAY LẠI MENU", callback_data="menu_back"))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode="HTML", reply_markup=kb)

    elif call.data == "menu_live_traffic":
        traffic_text = (
            "📈 <b>GIÁM SÁT LƯU LƯỢNG TRỰC TIẾP</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "Hệ thống hoạt động bình thường qua Fast Node Gateway API."
        )
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔙 QUAY LẠI MENU", callback_data="menu_back"))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=traffic_text, parse_mode="HTML", reply_markup=kb)

    elif call.data == "menu_create_config":
        if user_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "⛔ Bạn không có quyền này!", show_alert=True)
            return
        admin_state[user_id] = "waiting_for_ws"
        text = (
            "🔮 <b>Cài đặt cấu hình WSS / Cookie</b>\n\n"
            "🔗 Gửi URL WebSocket hoặc cURL/Cookie vào đây để trích xuất token tự động."
        )
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("❌ HỦY", callback_data="menu_back"))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode="HTML", reply_markup=kb)

    elif call.data == "menu_my_configs":
        if user_id not in ADMIN_IDS:
            return
        cfg = user_configs.get(user_id)
        if not cfg:
            text = "⚙️ Bạn chưa có cấu hình WSS nào. Hãy bấm 'Tạo WSS Config' để thiết lập!"
        else:
            text = (
                f"⚙️ <b>Cấu hình hiện tại:</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"🌐 <b>WSS:</b> <code>{cfg.get('ws_url', 'N/A')}</code>\n"
                f"🔑 <b>Token:</b> <code>{cfg.get('token', 'N/A')[:15]}...</code>\n"
                f"💰 <b>Số dư:</b> <code>250,000 VND</code>\n"
            )
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔄 LÀM MỚI", callback_data="config_refresh"),
               InlineKeyboardButton("❌ XÓA", callback_data="config_delete"))
        kb.add(InlineKeyboardButton("🔙 QUAY LẠI MENU", callback_data="menu_back"))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode="HTML", reply_markup=kb)

    elif call.data == "config_refresh":
        bot.answer_callback_query(call.id, "Đang làm mới kết nối...")

    elif call.data == "config_delete":
        user_configs.pop(user_id, None)
        bot.answer_callback_query(call.id, "Đã xóa cấu hình!")
        handle_callback(type('obj', (object,), {'from_user': call.from_user, 'message': call.message, 'data': 'menu_back'})())

    elif call.data == "menu_owner":
        if user_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "⛔ Bạn không có quyền Owner!", show_alert=True)
            return
        owner_text = "👑 <b>BẢNG ĐIỀU KHIỂN OWNER</b>\n\nChọn chức năng quản lý:"
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(
            InlineKeyboardButton("➕ Thêm số hàng loạt", callback_data="admin_add_mode"),
            InlineKeyboardButton("📊 Báo cáo kho tổng", callback_data="admin_stock"),
            InlineKeyboardButton("🔙 QUAY LẠI MENU", callback_data="menu_back")
        )
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=owner_text, parse_mode="HTML", reply_markup=kb)

    elif call.data == "admin_add_mode":
        if user_id not in ADMIN_IDS:
            return
        admin_state[user_id] = "waiting_for_numbers"
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("❌ HỦY", callback_data="menu_owner"))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="📥 Gửi danh sách số điện thoại vào đây để phân loại tự động vào 195+ quốc gia.", parse_mode="HTML", reply_markup=kb)

    elif call.data == "admin_stock":
        if user_id not in ADMIN_IDS:
            return
        report = "📊 <b>BÁO CÁO KHO TỔNG</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        total_all = 0
        for key, data in inventory_numbers.items():
            count = sum(1 for item in data["numbers"] if not item.get("locked_by"))
            if count > 0:
                total_all += count
                report += f"🌍 <b>{key}</b>: <code>{count}</code> số\n"
        report += f"\n🔥 Tổng số khả dụng: <code>{total_all}</code> số"
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔙 QUAY LẠI", callback_data="menu_owner"))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=report, parse_mode="HTML", reply_markup=kb)

    elif call.data == "menu_back":
        admin_state.pop(user_id, None)
        welcome_text = "🔥 <b>FAST NODE • IVAS OTP GATEWAY</b>\n\nChào mừng bạn đến với hệ thống!"
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
            "balance": "250,000 VND"
        }
        admin_state.pop(user_id, None)
        bot.send_message(chat_id, "✅ Cấu hình thành công!", parse_mode="HTML")
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
        bot.send_message(chat_id, f"✅ Thêm thành công {total_added} số vào kho!", parse_mode="HTML")

@bot.message_handler(commands=['thue'])
def handle_rent_number(message):
    parts = message.text.split()
    if len(parts) < 2:
        return
    phone_to_rent = parts[1].replace("+", "").strip()
    user_id = message.chat.id
    user_rentals[phone_to_rent] = user_id
    
    for key, data in inventory_numbers.items():
        for item in data["numbers"]:
            if item["phone"] == phone_to_rent:
                item["expires"] = time.time() + 900
                item["locked_by"] = user_id
                break
    bot.reply_to(message, f"✅ Đã thuê số <code>{phone_to_rent}</code> trong 15 phút. OTP sẽ bắn riêng về inbox bạn!", parse_mode="HTML")

def background_cleanup_and_wss():
    global last_reset_time, app_stats
    while True:
        current_time = time.time()
        # Reset thống kê OTP Top Applications sau mỗi 24 giờ (86400 giây)
        if current_time - last_reset_time > 86400:
            for k in app_stats:
                app_stats[k] = random.randint(100, 1500)
            last_reset_time = current_time

        for key, data in inventory_numbers.items():
            for item in list(data["numbers"]):
                if item["expires"] > 0 and item["expires"] <= current_time:
                    user_rentals.pop(item["phone"], None)
                    data["numbers"].remove(item)
        time.sleep(30)

async def dispatch_update(service, phone, msg, timestamp, country, flag, is_test=False):
    global app_stats
    clean_phone = str(phone).replace("+", "")
    masked = clean_phone[:6] + "****" + clean_phone[-3:] if len(clean_phone) > 7 else clean_phone
    match = re.search(r'\d{3}[-\s]?\d{3}|\d{4,8}', str(msg))
    code = match.group(0) if match else "N/A"

    # Tự động nhận diện dịch vụ chuẩn xác qua bộ điều kiện của bro
    detected_service = parse_service_name(f"{service} {msg}")
    if detected_service in app_stats:
        app_stats[detected_service] += 1
    else:
        app_stats["AUTHMSG"] = app_stats.get("AUTHMSG", 0) + 1

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
    except Exception as e: 
        print(f"Lỗi gửi tin nhắn vào Group: {e}")

    if clean_phone in user_rentals:
        owner_id = user_rentals[clean_phone]
        private_caption = f"🔔 <b>[PRIVATE EXCLUSIVE OTP FOR YOUR NUMBER]</b>\n\n" + caption
        try:
            await asyncio.to_thread(bot.send_message, chat_id=owner_id, text=private_caption, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)
        except Exception as e:
            print(f"Lỗi gửi riêng user {owner_id}: {e}")

def websocket_worker():
    def on_message(ws, message):
        try:
            data = json.loads(message)
            phone = data.get("phone", "84939168914")
            service = data.get("service", "WhatsApp")
            msg = data.get("message", "Your WhatsApp verification code is 790-937")
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            cname, flag, _ = detect_country_info(phone)
            asyncio.run(dispatch_update(service, phone, msg, timestamp, cname, flag, is_test=False))
        except:
            pass
    def on_error(ws, error): pass
    def on_close(ws, c, m): time.sleep(10)
    def on_open(ws): print("🟢 WebSocket Connected!")

    while True:
        for uid, cfg in user_configs.items():
            ws_url = cfg.get("ws_url")
            if ws_url and ws_url.startswith("wss://"):
                try:
                    wsapp = websocket.WebSocketApp(ws_url, on_open=on_open, on_message=on_message, on_error=on_error, on_close=on_close)
                    wsapp.run_forever()
                except:
                    pass
        time.sleep(15)

# --- FLASK SERVER & WEB APP (IVAS SMS DASHBOARD DESIGN STYLE) ---
app = Flask(__name__)

@app.route('/')
def home():
    countries_data = []
    for key, data in inventory_numbers.items():
        available_numbers = [{"phone": item["phone"], "expires": item["expires"]} for item in data["numbers"] if not item.get("locked_by")]
        countries_data.append({
            "key": key, "name": data["name"], "flag": data["flag"], "numbers": available_numbers
        })
    
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>IVAS SMS Portal • Dashboard</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            :root { --bg: #0f172a; --card: #1e293b; --orange-bar: #f59e0b; --border: #334155; --text: #f8fafc; --muted: #94a3b8; --green: #22c55e; }
            body { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 10px; }
            .top-bar { background: var(--orange-bar); color: #000; padding: 10px 14px; border-radius: 8px; font-weight: bold; display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
            
            .sidebar-menu { background: var(--card); border: 1px solid var(--border); border-radius: 10px; margin-bottom: 12px; overflow: hidden; }
            .sidebar-header { padding: 12px 16px; background: #273548; font-weight: bold; display: flex; justify-content: space-between; align-items: center; cursor: pointer; color: #38bdf8; }
            .sidebar-dropdown { max-height: 0; overflow: hidden; transition: max-height 0.3s ease-out; background: #131c2e; padding: 0 16px; }
            .sidebar-dropdown.open { max-height: 350px; padding: 10px 16px; }
            .menu-item { display: block; width: 100%; background: transparent; border: none; color: var(--text); padding: 10px; text-align: left; font-weight: bold; font-size: 14px; cursor: pointer; border-bottom: 1px solid var(--border); }
            .menu-item:hover { color: #38bdf8; }

            .dashboard-section { display: grid; grid-template-columns: 2fr 1fr; gap: 10px; margin-bottom: 12px; }
            @media(max-width: 600px) { .dashboard-section { grid-template-columns: 1fr; } }

            .widget-card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 14px; }
            .widget-title { font-size: 14px; font-weight: bold; color: #f59e0b; margin-bottom: 10px; border-bottom: 1px solid var(--border); padding-bottom: 6px; }

            .apps-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
            .app-box { background: #131c2e; border: 1px solid var(--border); border-radius: 8px; padding: 8px; text-align: center; font-size: 11px; }
            .app-box b { display: block; font-size: 12px; color: #38bdf8; margin-top: 2px; }

            .range-item { display: flex; align-items: center; justify-content: space-between; background: #131c2e; border: 1px solid var(--border); padding: 8px; border-radius: 6px; margin-bottom: 6px; font-size: 12px; }

            .grid-countries { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; }
            .country-pill { background: #131c2e; border: 1px solid var(--border); border-radius: 6px; padding: 6px 2px; text-align: center; cursor: pointer; font-size: 10px; }
            .country-pill:hover { border-color: #38bdf8; }

            .number-item { display: flex; justify-content: space-between; align-items: center; background: #131c2e; border: 1px solid var(--border); padding: 8px; border-radius: 6px; margin-bottom: 6px; font-size: 13px; }
            .btn { background: var(--green); color: white; border: none; border-radius: 6px; padding: 6px 12px; font-size: 12px; font-weight: bold; cursor: pointer; }
            .btn-red { background: #ef4444; }
            .btn-gray { background: #475569; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="top-bar">
                <span>IVAS SMS • Portal Dashboard</span>
                <span>Balance: 250,000 VND</span>
            </div>

            <div class="sidebar-menu">
                <div class="sidebar-header" onclick="toggleSidebar()">
                    <span>📁 Dashboard Navigation</span>
                    <span id="arrowIcon">▼</span>
                </div>
                <div class="sidebar-dropdown" id="sidebarDropdown">
                    <button class="menu-item" onclick="scrollToSection('dashboardSection')">📊 Dashboard</button>
                    <button class="menu-item" onclick="scrollToSection('clientActiveSection')">📥 Client Active SMS</button>
                    <button class="menu-item" onclick="scrollToSection('marketplaceSection')">🌍 Get Number (195+)</button>
                    <button class="menu-item" onclick="window.open('https://t.me/LIVEOTPIVAS', '_blank')">📢 Official Channel</button>
                    <button class="menu-item btn-red" style="color:#ef4444;" onclick="exitApp()">❌ Exit App</button>
                </div>
            </div>

            <div class="dashboard-section" id="dashboardSection">
                <div class="widget-card">
                    <div class="widget-title">Top Applications Access (24h Auto-Reset)</div>
                    <div class="apps-grid" id="appsGrid"></div>
                </div>
                <div class="widget-card">
                    <div class="widget-title">🔥 Top Ranges (80%+ OTP Rate)</div>
                    <div id="topRangesContainer"></div>
                </div>
            </div>

            <div class="widget-card" id="clientActiveSection" style="margin-bottom: 12px;">
                <div class="widget-title" style="display:flex; justify-content:space-between; align-items:center;">
                    <span>Client Active SMS & Numbers</span>
                    <button class="btn" onclick="toggleClientDropdown()">▼ Toggle Live Feed</button>
                </div>
                <div id="clientDropdownContent" style="max-height:0; overflow:hidden; transition:max-height 0.3s;">
                    <p style="font-size:12px; color:var(--muted); text-align:center;">Real-time incoming OTP sessions active for rented numbers.</p>
                </div>
            </div>

            <div class="widget-card" id="marketplaceSection">
                <div class="widget-title">Get Number • 195+ Countries Marketplace</div>
                <div class="grid-countries" id="countryGrid"></div>
            </div>

            <div class="widget-card" id="detailCard" style="display:none; margin-top: 12px;">
                <h3 id="detailTitleText" style="color:#38bdf8; font-size:14px; margin-bottom:8px;">Number Details</h3>
                <div id="numberListContainer"></div>
                <div style="display:flex; gap:6px; margin-top:10px;">
                    <button class="btn btn-gray" onclick="goBackToGrid()">🔙 Back</button>
                    <button class="btn" onclick="location.reload()">🔄 Refresh</button>
                </div>
            </div>
        </div>

        <script>
            let tg = window.Telegram.WebApp;
            tg.expand();

            let appStats = {{ app_stats | tojson }};
            let topRanges = {{ top_ranges_data | tojson }};
            let countriesData = {{ countries_data | tojson }};
            let currentSelectedCountry = null;

            function toggleSidebar() {
                let drop = document.getElementById('sidebarDropdown');
                let arrow = document.getElementById('arrowIcon');
                drop.classList.toggle('open');
                arrow.innerText = drop.classList.contains('open') ? '▲' : '▼';
            }

            function toggleClientDropdown() {
                let content = document.getElementById('clientDropdownContent');
                content.style.maxHeight = content.style.maxHeight === '200px' ? '0px' : '200px';
            }

            function scrollToSection(id) {
                document.getElementById(id).scrollIntoView({ behavior: 'smooth' });
                toggleSidebar();
            }

            function exitApp() {
                tg.close();
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
                topRanges.forEach(r => {
                    let div = document.createElement('div');
                    div.className = 'range-item';
                    div.innerHTML = `<span>${r.flag} <b>${r.country}</b></span> <span style="color:var(--green); font-weight:bold;">${r.range}</span>`;
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
                    row.innerHTML = `<span><b>${item.phone}</b></span> <button class="btn" onclick="rentNumber('${item.phone}')">Rent 15m</button>`;
                    container.appendChild(row);
                });
            }

            function goBackToGrid() {
                document.getElementById('detailCard').style.display = 'none';
                currentSelectedCountry = null;
            }

            function rentNumber(phone) {
                tg.sendData(`/thue ${phone}`);
                tg.showAlert(`Successfully rented number ${phone} for 15 minutes! Hidden from others.`);
                tg.close();
            }

            renderApps();
            renderTopRanges();
            renderCountries();
        </script>
    </body>
    </html>
    """, app_stats=app_stats, top_ranges_data=top_ranges_data, countries_data=countries_data)

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def run_bot_polling():
    try:
        bot.remove_webhook()
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset=-1")
        time.sleep(1)
    except:
        pass
    print("🚀 Telegram Bot Polling Started Successfully!")
    bot.infinity_polling(skip_pending=True, interval=0, timeout=20)

if __name__ == "__main__":
    t_web = threading.Thread(target=run_web, daemon=True)
    t_web.start()
    
    t_wss = threading.Thread(target=websocket_worker, daemon=True)
    t_wss.start()

    t_clean = threading.Thread(target=background_cleanup_and_wss, daemon=True)
    t_clean.start()
    
    run_bot_polling()
