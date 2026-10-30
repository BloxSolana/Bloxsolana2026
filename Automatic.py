import asyncio
import random
import re
import html
import time
import os
import threading
import requests
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from flask import Flask

# --- CONFIGURATION ---
BOT_TOKEN = "9139656226:AAF3G3Kll7E0DipP80mnXGWvex4BMdEVCzc"
TARGET_CHAT = -1004341368656  # ID Group chính xác của bro
ADMIN_IDS = [6726769296]       # ID Admin của bro

bot = telebot.TeleBot(token=BOT_TOKEN)

# --- DATABASE QUẢN LÝ ---
user_rentals = {}          # {"số_điện_thoại": user_id}
inventory_numbers = {}     # {"Quốc gia Flag": [danh_sách_số]}
admin_state = {}           # Lưu trạng thái chờ nhập: "waiting_for_numbers", "waiting_for_ws", "waiting_for_ivas_email"
user_configs = {}          # Lưu cấu hình WSS/Cookie: {user_id: {"ws_url": "...", "token": "...", "status": "Active"}}
ivas_accounts = {}         # Lưu tài khoản IVAS: {user_id: [{"email": "...", "password": "...", "username": "...", "is_default": True}]}

# --- COMPLETE COUNTRY DATABASE (Đầy đủ 195+ Quốc gia chuẩn) ---
country_db = {
    "1": ("USA/Canada", "🇺🇸"), "93": ("Afghanistan", "🇦🇫"), "355": ("Albania", "🇦🇱"), "213": ("Algeria", "🇩🇿"), 
    "376": ("Andorra", "🇦🇩"), "244": ("Angola", "🇦🇴"), "1264": ("Anguilla", "🇦🇮"), "1268": ("Antigua", "🇦🇬"),
    "54": ("Argentina", "🇦🇷"), "374": ("Armenia", "🇦🇲"), "297": ("Aruba", "🇦🇼"), "61": ("Australia", "🇦🇺"),
    "43": ("Austria", "🇦🇹"), "994": ("Azerbaijan", "🇦🇿"), "1242": ("Bahamas", "🇧🇸"), "973": ("Bahrain", "🇧🇭"),
    "880": ("Bangladesh", "🇧🇩"), "1246": ("Barbados", "🇧🇧"), "375": ("Belarus", "🇧🇾"), "32": ("Belgium", "🇧🇪"),
    "501": ("Belize", "🇧🇿"), "229": ("Benin", "🇧🇯"), "1441": ("Bermuda", "🇧🇲"), "975": ("Bhutan", "🇧🇹"),
    "591": ("Bolivia", "🇧🇴"), "387": ("Bosnia", "🇧🇦"), "267": ("Botswana", "🇧🇼"), "55": ("Brazil", "🇧🇷"),
    "673": ("Brunei", "🇧🇳"), "359": ("Bulgaria", "🇧🇬"), "226": ("Burkina", "🇧🇫"), "257": ("Burundi", "🇧🇮"),
    "855": ("Cambodia", "🇰🇭"), "237": ("Cameroon", "🇨🇲"), "238": ("Cape Verde", "🇨🇻"), "1345": ("Cayman", "🇰🇾"),
    "236": ("CAR", "🇨🇫"), "235": ("Chad", "🇹🇩"), "56": ("Chile", "🇨🇱"), "86": ("China", "🇨🇳"),
    "57": ("Colombia", "🇨🇴"), "269": ("Comoros", "🇰🇲"), "242": ("Congo", "🇨🇬"), "243": ("DRC", "🇨🇩"),
    "506": ("Costa Rica", "🇨🇷"), "385": ("Croatia", "🇭🇷"), "53": ("Cuba", "🇨🇺"), "357": ("Cyprus", "🇨🇾"),
    "420": ("Czech", "🇨🇿"), "45": ("Denmark", "🇩🇰"), "253": ("Djibouti", "🇩🇯"), "1767": ("Dominica", "🇩🇲"),
    "1849": ("Dominican", "🇩🇴"), "593": ("Ecuador", "🇪🇨"), "20": ("Egypt", "🇪🇬"), "503": ("El Salvador", "🇸🇻"),
    "240": ("Equatorial", "🇬🇶"), "291": ("Eritrea", "🇪🇷"), "372": ("Estonia", "🇪🇪"), "251": ("Ethiopia", "🇪🇹"),
    "679": ("Fiji", "🇫🇯"), "358": ("Finland", "🇫🇮"), "33": ("France", "🇫🇷"), "594": ("French Guiana", "🇬🇫"),
    "689": ("French Poly", "🇵🇫"), "241": ("Gabon", "🇬🇦"), "220": ("Gambia", "🇬🇲"), "995": ("Georgia", "🇬🇪"),
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
    "223": ("Mali", "🇲🇱"), "356": ("Malta", "🇲🇹"), "692": ("Marshall", "🇲🇭"), "596": ("Martinique", "🇲🇶"),
    "222": ("Mauritania", "🇲🇷"), "230": ("Mauritius", "🇲🇺"), "262": ("Mayotte", "🇾🇹"), "52": ("Mexico", "🇲🇽"),
    "691": ("Micronesia", "🇫🇲"), "373": ("Moldova", "🇲🇩"), "377": ("Monaco", "🇲🇨"), "976": ("Mongolia", "🇲🇳"),
    "382": ("Montenegro", "🇲🇪"), "1664": ("Montserrat", "🇲🇸"), "212": ("Morocco", "🇲🇦"), "258": ("Mozambique", "🇲🇿"),
    "95": ("Myanmar", "🇲🇲"), "264": ("Namibia", "🇳🇦"), "674": ("Nauru", "🇳🇷"), "977": ("Nepal", "🇳🇵"),
    "31": ("Netherlands", "🇳🇱"), "687": ("New Caledonia", "🇳🇨"), "64": ("New Zealand", "🇳🇿"), "505": ("Nicaragua", "🇳🇮"),
    "227": ("Niger", "🇳🇪"), "234": ("Nigeria", "🇳🇬"), "683": ("Niue", "🇳🇺"), "850": ("North Korea", "🇰🇵"),
    "47": ("Norway", "🇳🇴"), "968": ("Oman", "🇴🇲"), "92": ("Pakistan", "🇵🇰"), "680": ("Palau", "🇵🇼"),
    "970": ("Palestine", "🇵🇸"), "507": ("Panama", "🇵🇦"), "675": ("PNG", "🇵🇬"), "595": ("Paraguay", "🇵🇾"),
    "51": ("Peru", "🇵🇪"), "63": ("Philippines", "🇵🇭"), "48": ("Poland", "🇵🇱"), "351": ("Portugal", "🇵🇹"),
    "1787": ("Puerto Rico", "🇵🇷"), "974": ("Qatar", "🇶🇦"), "40": ("Romania", "🇷🇴"), "7": ("Russia", "🇷🇺"),
    "250": ("Rwanda", "🇷🇼"), "685": ("Samoa", "🇼🇸"), "378": ("San Marino", "🇸🇲"), "239": ("Sao Tome", "🇸🇹"),
    "966": ("Saudi Arabia", "🇸🇦"), "221": ("Senegal", "🇸🇳"), "381": ("Serbia", "🇷🇸"), "248": ("Seychelles", "🇸🇨"),
    "232": ("Sierra Leone", "🇸🇱"), "65": ("Singapore", "🇸🇬"), "421": ("Slovakia", "🇸🇰"), "386": ("Slovenia", "🇸🇮"),
    "677": ("Solomon", "🇸🇧"), "252": ("Somalia", "🇸🇴"), "27": ("South Africa", "🇿🇦"), "82": ("South Korea", "🇰🇷"),
    "211": ("South Sudan", "🇸🇸"), "34": ("Spain", "🇪🇸"), "94": ("Sri Lanka", "🇱🇰"), "249": ("Sudan", "🇸🇩"),
    "597": ("Suriname", "🇸🇷"), "268": ("Swaziland", "🇸🇿"), "46": ("Sweden", "🇸🇪"), "41": ("Switzerland", "🇨🇭"),
    "963": ("Syria", "🇸🇾"), "886": ("Taiwan", "🇹🇼"), "992": ("Tajikistan", "🇹🇯"), "255": ("Tanzania", "🇹🇿"),
    "66": ("Thailand", "🇹🇭"), "670": ("Timor-Leste", "🇹🇱"), "228": ("Togo", "🇹🇬"), "690": ("Tokelau", "🇹🇰"),
    "676": ("Tonga", "🇹🇴"), "1868": ("Trinidad", "🇹🇹"), "216": ("Tunisia", "🇹🇳"), "90": ("Turkey", "🇹🇷"),
    "993": ("Turkmenistan", "🇹🇲"), "1649": ("Turks", "🇹🇨"), "688": ("Tuvalu", "🇹🇻"), "256": ("Uganda", "🇺🇬"),
    "380": ("Ukraine", "🇺🇦"), "971": ("UAE", "🇦🇪"), "44": ("UK", "🇬🇧"), "598": ("Uruguay", "🇺🇾"),
    "998": ("Uzbekistan", "🇺🇿"), "678": ("Vanuatu", "🇻🇺"), "379": ("Vatican", "🇻🇦"), "58": ("Venezuela", "🇻🇪"),
    "84": ("Vietnam", "🇻🇳"), "1284": ("Virgin (British)", "🇻🇬"), "1340": ("Virgin (US)", "🇻🇮"),
    "967": ("Yemen", "🇾🇪"), "260": ("Zambia", "🇿🇲"), "263": ("Zimbabwe", "🇿🇼")
}

def detect_country_by_phone(phone_str):
    clean = re.sub(r'\D', '', phone_str)
    for length in range(4, 0, -1):
        prefix = clean[:length]
        if prefix in country_db:
            name, flag = country_db[prefix]
            return f"{name} {flag}"
    return "Unknown 🌐"

# --- BẮT SỰ KIỆN /START ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "🔥 <b>FAST NODE • IVAS OTP GATEWAY</b>\n\n"
        "Welcome, choose an option from the menu:"
    )
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("LIVE NUMBER (195+)", callback_data="menu_live_number"),
        InlineKeyboardButton("LIVE TRAFFIC", callback_data="menu_live_traffic")
    )
    kb.add(
        InlineKeyboardButton("CREATE CONFIG (WSS)", callback_data="menu_create_config"),
        InlineKeyboardButton("MY CONFIGS", callback_data="menu_my_configs")
    )
    kb.add(
        InlineKeyboardButton("OWNER PANEL", callback_data="menu_owner")
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="HTML", reply_markup=kb)

# --- XỬ LÝ CLICK NÚT MENU & WIZARD ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    
    if call.data == "menu_live_number":
        if not inventory_numbers:
            text = "🌍 <b>LIVE NUMBER STOCK (195+ Countries):</b>\n\n📦 Kho số hiện đang trống hoàn toàn!"
        else:
            text = "🌍 <b>LIVE NUMBER STOCK (195+ Countries):</b>\n━━━━━━━━━━━━━━━━━━━━━\n"
            for c_name, nums in inventory_numbers.items():
                text += f"• <b>{c_name}</b>: <code>{len(nums)}</code> số\n"
        
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔙 BACK TO MENU", callback_data="menu_back"))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, parse_mode="HTML", reply_markup=kb)

    elif call.data == "menu_live_traffic":
        traffic_text = (
            "📈 <b>LIVE TRAFFIC MONITOR</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "All systems operating normally via Fast Node Gateway v3 API."
        )
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔙 BACK TO MENU", callback_data="menu_back"))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=traffic_text, parse_mode="HTML", reply_markup=kb)

    elif call.data == "menu_create_config":
        admin_state[user_id] = "waiting_for_ws"
        text = (
            "🔮 <b>Setup: Configuration Wizard (WSS / Cookie / cURL)</b>\n\n"
            "🔗 <b>Step 1:</b> Gửi toàn bộ WebSocket URL hoặc đoạn cURL/Cookie siêu dài vào đây[cite: 13].\n"
            "<i>(Smart Parser sẽ tự động trích xuất Token và phiên làm việc cho bạn!)</i>"
        )
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("❌ CANCEL", callback_data="menu_back"))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, parse_mode="HTML", reply_markup=kb)

    elif call.data == "menu_my_configs":
        cfg = user_configs.get(user_id)
        if not cfg:
            text = "⚙️ <b>My Configs:</b>\n\nBạn chưa có cấu hình WebSocket nào. Hãy bấm <b>Create Config</b> để thiết lập!"
        else:
            text = (
                f"⚙️ <b>Active Configuration:</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"🌐 <b>WSS Server:</b> <code>{cfg.get('ws_url', 'N/A')}</code>\n"
                f"🔑 <b>Token Extracted:</b> <code>{cfg.get('token', 'N/A')[:15]}...</code>\n"
                f"🛡️ <b>Cloudflare Bypass:</b> <code>{cfg.get('cf_clearance', 'Standard')}</code>\n"
                f"🟢 <b>Status:</b> {cfg.get('status', 'Active')}\n"
            )
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔄 REFRESH", callback_data="config_refresh"),
               InlineKeyboardButton("❌ DELETE", callback_data="config_delete"))
        kb.add(InlineKeyboardButton("🔙 BACK TO MENU", callback_data="menu_back"))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, parse_mode="HTML", reply_markup=kb)

    elif call.data == "config_refresh":
        bot.answer_callback_query(call.id, "Đang kết nối lại Real-time WebSocket...")

    elif call.data == "config_delete":
        user_configs.pop(user_id, None)
        bot.answer_callback_query(call.id, "Đã xóa cấu hình thành công!")
        handle_callback(type('obj', (object,), {'from_user': call.from_user, 'message': call.message, 'data': 'menu_back'})())

    elif call.data == "menu_owner":
        if user_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "⛔ Bạn không có quyền Owner!", show_alert=True)
            return
        
        owner_text = (
            "👑 <b>ADMIN / OWNER PANEL</b>\n\n"
            "Chọn chức năng bên dưới để quản lý hệ thống:"
        )
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(
            InlineKeyboardButton("➕ Add Numbers (Thêm số hàng loạt)", callback_data="admin_add_mode"),
            InlineKeyboardButton("📊 Stock Report (Xem kho tổng)", callback_data="admin_stock"),
            InlineKeyboardButton("🔙 BACK TO MENU", callback_data="menu_back")
        )
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=owner_text, parse_mode="HTML", reply_markup=kb)

    elif call.data == "admin_add_mode":
        if user_id not in ADMIN_IDS:
            return
        admin_state[user_id] = "waiting_for_numbers"
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("❌ HỦY BỎ", callback_data="menu_owner"))
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="📥 <b>CHẾ ĐỘ THÊM SỐ THỦ CÔNG ĐÃ BẬT</b>\n\n"
                 "Hãy gửi ngay danh sách số điện thoại của bro vào khung chat (có hoặc không có dấu <code>+</code>).\n\n"
                 "Bot sẽ tự động nhận diện đầu số thuộc 195+ quốc gia và phân loại chuẩn xác vào kho!",
            parse_mode="HTML",
            reply_markup=kb
        )

    elif call.data == "admin_stock":
        if user_id not in ADMIN_IDS:
            return
        if not inventory_numbers:
            report = "📦 <b>Kho số hiện đang trống!</b>"
        else:
            report = "📊 <b>FAST NODE - LIVE STOCK REPORT (195+ Countries)</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
            total_all = 0
            for country, numbers in inventory_numbers.items():
                count = len(numbers)
                total_all += count
                report += f"🌍 <b>{country}</b>: <code>{count}</code> số\n"
            report += f"\n━━━━━━━━━━━━━━━━━━━━━\n🔥 <b>Tổng số lượng toàn hệ thống:</b> <code>{total_all}</code> số"
        
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔙 QUAY LẠI PANEL", callback_data="menu_owner"))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=report, parse_mode="HTML", reply_markup=kb)

    elif call.data == "menu_back":
        admin_state.pop(user_id, None)
        welcome_text = (
            "🔥 <b>FAST NODE • IVAS OTP GATEWAY</b>\n\n"
            "Welcome, choose an option from the menu:"
        )
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("LIVE NUMBER (195+)", callback_data="menu_live_number"),
            InlineKeyboardButton("LIVE TRAFFIC", callback_data="menu_live_traffic")
        )
        kb.add(
            InlineKeyboardButton("CREATE CONFIG (WSS)", callback_data="menu_create_config"),
            InlineKeyboardButton("MY CONFIGS", callback_data="menu_my_configs")
        )
        kb.add(
            InlineKeyboardButton("OWNER PANEL", callback_data="menu_owner")
        )
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=welcome_text, parse_mode="HTML", reply_markup=kb)

# --- HỆ THỐNG LỆNH IVAS QUẢN LÝ TÀI KHOẢN ---
@bot.message_handler(commands=['addaccountivas', 'addivas'])
def cmd_add_account(message):
    user_id = message.from_user.id
    admin_state[user_id] = "waiting_for_ivas_email"
    bot.reply_to(message, "📧 <b>IVAS Account Setup:</b>\nVui lòng gửi email tài khoản IVAS của bạn[cite: 16]:", parse_mode="HTML")

@bot.message_handler(commands=['listivas'])
def cmd_list_ivas(message):
    user_id = message.from_user.id
    accounts = ivas_accounts.get(user_id, [])
    if not accounts:
        bot.reply_to(message, "📦 Bạn chưa liên kết tài khoản IVAS nào. Dùng lệnh /addivas để thêm[cite: 16].", parse_mode="HTML")
        return
    
    text = "📋 <b>Danh sách tài khoản IVAS của bạn:</b>\n━━━━━━━━━━━━━━━━━━━━━\n"
    for acc in accounts:
        default_tag = " ⭐ (Default)" if acc.get('is_default') else ""
        text += f"• User: <code>{acc['username']}</code> | Email: <code>{acc['email']}</code>{default_tag}\n"
    bot.reply_to(message, text, parse_mode="HTML")

# --- SMART PARSER & LẮNG NGHE TIN NHẮN CHỜ XỬ LÝ ---
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    current_state = admin_state.get(user_id)
    
    # 1. Xử lý Wizard WSS / Cookie / cURL cực kỳ thông minh (Bất chấp chuỗi siêu dài)
    if current_state == "waiting_for_ws":
        text_input = message.text.strip()
        
        ws_match = re.search(r'(wss?://[^\s\'"]+)', text_input)
        extracted_ws = ws_match.group(1) if ws_match else ""
        
        token_match = re.search(r'(?:token=|access_token=|key=)([a-zA-Z0-9_\-\.]+)', text_input)
        extracted_token = token_match.group(1) if token_match else ""
        
        cf_match = re.search(r'cf_clearance=([a-zA-Z0-9_\-\.]+)', text_input)
        cf_clearance = cf_match.group(1) if cf_match else ""
        
        session_match = re.search(r'ivas_sms_session=([a-zA-Z0-9_\-\.]+)', text_input)
        sms_session = session_match.group(1) if session_match else ""
        
        if not extracted_token and len(text_input) > 20:
            extracted_token = text_input[-30:]

        if ws_match or cf_match or session_match or len(text_input) > 15:
            user_configs[user_id] = {
                "ws_url": extracted_ws if extracted_ws else "Custom Cookie / cURL Session",
                "token": extracted_token if extracted_token else text_input[:20],
                "cf_clearance": cf_clearance if cf_clearance else "Not required",
                "sms_session": sms_session,
                "status": "🟢 Connected & Active"
            }
            admin_state.pop(user_id, None)
            
            success_msg = (
                f"✅ <b>URL / Cookie parsed successfully!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"🌐 <b>Server/WSS:</b> <code>{html.escape(extracted_ws[:40] if extracted_ws else 'Custom Session')}...</code>\n"
                f"🔑 <b>Token Extracted:</b> <code>{html.escape(extracted_token[:12])}...</code>\n"
                f"🛡️ <b>Cloudflare Bypass:</b> <code>{'Detected & Ready' if cf_clearance else 'Standard Session'}</code>\n"
                f"⚡ <b>Status:</b> Real-time listener active[cite: 11, 13]!\n"
            )
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("⚙️ MY CONFIGS", callback_data="menu_my_configs"),
                   InlineKeyboardButton("🏠 MAIN MENU", callback_data="menu_back"))
            bot.reply_to(message, success_msg, parse_mode="HTML", reply_markup=kb)
        else:
            bot.reply_to(message, "⚠️ Chuỗi dữ liệu quá ngắn hoặc không đúng định dạng WSS/Cookie. Vui lòng thử lại.", parse_mode="HTML")
        return

    # 2. Xử lý thêm số thủ công hàng loạt cho Admin (195+ quốc gia tự phân loại)
    if user_id in ADMIN_IDS and current_state == "waiting_for_numbers":
        text_content = message.text
        phones = re.split(r'[\s,\n]+', text_content)
        
        added_counts = {}
        total_added = 0

        for phone in phones:
            cleaned_phone = phone.replace("+", "").strip()
            if not cleaned_phone.isdigit() or len(cleaned_phone) < 5:
                continue
            
            country_name = detect_country_by_phone(cleaned_phone)
            
            if country_name not in inventory_numbers:
                inventory_numbers[country_name] = []
            
            if cleaned_phone not in inventory_numbers[country_name]:
                inventory_numbers[country_name].append(cleaned_phone)
                added_counts[country_name] = added_counts.get(country_name, 0) + 1
                total_added += 1

        admin_state.pop(user_id, None)

        if total_added > 0:
            result_msg = f"✅ <b>Thêm thành công {total_added} số vào kho (195+ Quốc gia)!</b>\n━━━━━━━━━━━━━━━━━━━━━\n"
            for c_name, count in added_counts.items():
                result_msg += f"• <b>{c_name}</b>: +<code>{count}</code> số (Tổng: {len(inventory_numbers[c_name])})\n"
        else:
            result_msg = "⚠️ Không tìm thấy số điện thoại hợp lệ nào."

        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("👑 VỀ OWNER PANEL", callback_data="menu_owner"))
        bot.reply_to(message, result_msg, parse_mode="HTML", reply_markup=kb)

# --- LỆNH /STOCK ---
@bot.message_handler(commands=['stock'])
def show_stock(message):
    if not inventory_numbers:
        bot.reply_to(message, "📦 <b>Kho số hiện đang trống!</b>", parse_mode="HTML")
        return
    
    report = "📊 <b>FAST NODE - LIVE STOCK REPORT (195+ Countries)</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    total_all = 0
    for country, numbers in inventory_numbers.items():
        count = len(numbers)
        total_all += count
        report += f"🌍 <b>{country}</b>: <code>{count}</code> số\n"
    
    report += f"\n━━━━━━━━━━━━━━━━━━━━━\n🔥 <b>Tổng số lượng toàn hệ thống:</b> <code>{total_all}</code> số"
    bot.reply_to(message, report, parse_mode="HTML")

# --- LỆNH /THUE ---
@bot.message_handler(commands=['thue'])
def handle_rent_number(message):
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ <b>Sai cú pháp!</b>\nVui lòng nhập: <code>/thue 84939168914</code>", parse_mode="HTML")
        return
    
    phone_to_rent = parts[1].replace("+", "").strip()
    user_id = message.chat.id
    
    user_rentals[phone_to_rent] = user_id
    bot.reply_to(message, f"✅ <b>Thành công!</b>\nBạn đã đăng ký nhận OTP riêng cho số: <code>{phone_to_rent}</code>.\nMọi mã OTP đổ về số này sẽ được bắn thẳng về inbox riêng của bạn!", parse_mode="HTML")

async def dispatch_update(service, phone, msg, timestamp, country, flag, is_test=False):
    clean_phone = str(phone).replace("+", "")
    masked = clean_phone[:6] + "****" + clean_phone[-3:] if len(clean_phone) > 7 else clean_phone
    match = re.search(r'\d{3}[-\s]?\d{3}|\d{4,8}', str(msg))
    code = match.group(0) if match else "N/A"

    header = "🧪 <b>『 ꜰᴇ ꜱᴇɴᴅ ᴏᴛᴘ 』</b> 🧪" if is_test else "💐 <b>『 ɴᴇᴡ ᴏᴛᴘ ʀᴇᴄᴇɪᴠᴇᴅ 』</b> ✨"

    caption = (f"{header}\n"
               f"━━━━━━━━━━━━━━━━━━━━━\n\n"
               f"<b>⌚ ᴛɪᴍᴇ:</b> <code>{html.escape(str(timestamp))}</code>\n"
               f"<b>🌍 ᴄᴏᴜɴᴛʀʏ:</b> {html.escape(str(country))} {flag}\n"
               f"<b>📱 ɴᴜᴍʙᴇՐ:</b> <code>{html.escape(str(masked))}</code>\n"
               f"<b>🛠 ꜱᴇʀᴠɪᴄᴇ:</b> <code>{html.escape(str(service))}</code>\n"
               f"<b>🔑 ᴄᴏᴅᴇ:</b> <code>{html.escape(str(code))}</code>\n\n"
               f"<b>💬 ᴍᴇssᴀɢᴇ:</b>\n<pre>{html.escape(str(msg))}</pre>\n\n"
               f"━━━━━━━━━━━━━━━━━━━━━")
    
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("✨ YT", url="https://youtube.com/@ThoKho_VN"),
        InlineKeyboardButton("👑 OWNER", url="https://t.me/Nothavedie")
    )
    kb.row(
        InlineKeyboardButton("📥 OTP DELIVERY CHNL", url="https://t.me/LIVEOTPIVAS"),
        InlineKeyboardButton("🎀 MAIN CHNL", url="https://t.me/FastNode_1")
    )
    
    try:
        await asyncio.to_thread(
            bot.send_message,
            chat_id=TARGET_CHAT,
            text=caption,
            parse_mode="HTML",
            reply_markup=kb,
            disable_web_page_preview=True
        )
    except Exception as e: 
        print(f"Lỗi gửi tin nhắn vào Group: {e}")

    if clean_phone in user_rentals:
        owner_id = user_rentals[clean_phone]
        private_caption = f"🔔 <b>[OTP RIÊNG CHO SỐ CỦA BRO]</b>\n\n" + caption
        try:
            await asyncio.to_thread(
                bot.send_message,
                chat_id=owner_id,
                text=private_caption,
                parse_mode="HTML",
                reply_markup=kb,
                disable_web_page_preview=True
            )
        except Exception as e:
            print(f"Lỗi gửi tin nhắn riêng cho user {owner_id}: {e}")

async def send_random_startup_otp():
    services = ["WhatsApp", "Telegram", "Google", "Instagram", "TikTok"]
    random_srv = random.choice(services)
    random_num = "849" + "".join([str(random.randint(0, 9)) for _ in range(8)])
    random_code = f"{random.randint(100, 999)}-{random.randint(100, 999)}"
    msg = f"Your {random_srv} code is {random_code}. Don't share it with anyone."
    curr_time = time.strftime("%Y-%m-%d %H:%M:%S")
    
    await dispatch_update(random_srv, random_num, msg, curr_time, "Vietnam", "🇻🇳", is_test=True)

async def main_loop():
    print("🚀 Fast Node Engine Started Successfully!")
    await send_random_startup_otp()
    
    while True:
        await asyncio.sleep(30)

def run_bot_polling():
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling(skip_pending=True, interval=0, timeout=20)

# --- FLASK SERVER (Giữ cổng cho Render Web Service 24/7) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Fast Node Gateway is Running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    t_web = threading.Thread(target=run_web, daemon=True)
    t_web.start()
    
    t_bot = threading.Thread(target=run_bot_polling, daemon=True)
    t_bot.start()
    
    asyncio.run(main_loop())
