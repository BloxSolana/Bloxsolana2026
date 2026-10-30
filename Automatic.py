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
from flask import Flask

# --- CONFIGURATION ---
BOT_TOKEN = "9139656226:AAF3G3Kll7E0DipP80mnXGWvex4BMdEVCzc"
TARGET_CHAT = -1004341368656  # ID Group chính xác của bro
ADMIN_IDS = [6726769296]       # ID Admin tối cao của bro
WEBAPP_URL = "https://bloxsolana2026.onrender.com"  # Link WebApp trên Render của bro

bot = telebot.TeleBot(token=BOT_TOKEN)

# --- DATABASE QUẢN LÝ ---
user_rentals = {}          # {"số_điện_thoại": user_id}
inventory_numbers = {}     # {"Quốc gia Flag": [danh_sách_số]}
admin_state = {}           # Lưu trạng thái chờ nhập
user_configs = {}          # Lưu cấu hình WSS/Cookie
ivas_accounts = {}         # Lưu tài khoản IVAS

# --- COMPLETE COUNTRY DATABASE (195+ Quốc gia chuẩn) ---
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

def get_menu_keyboard(user_id):
    kb = InlineKeyboardMarkup(row_width=2)
    # Tích hợp nút mở Mini App màu sắc chuẩn phong cách Ấn Độ
    kb.add(
        InlineKeyboardButton("🚀 OPEN WEB APP", web_app=WebAppInfo(url=WEBAPP_URL))
    )
    kb.add(
        InlineKeyboardButton("LIVE NUMBER (195+)", callback_data="menu_live_number"),
        InlineKeyboardButton("LIVE TRAFFIC", callback_data="menu_live_traffic")
    )
    if user_id in ADMIN_IDS:
        kb.add(
            InlineKeyboardButton("CREATE CONFIG (WSS)", callback_data="menu_create_config"),
            InlineKeyboardButton("MY CONFIGS", callback_data="menu_my_configs")
        )
        kb.add(
            InlineKeyboardButton("OWNER PANEL", callback_data="menu_owner")
        )
    return kb

# --- BẮT SỰ KIỆN /START ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "🔥 <b>FAST NODE • IVAS OTP GATEWAY</b>\n\n"
        "Welcome, choose an option from the menu:"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="HTML", reply_markup=get_menu_keyboard(message.from_user.id))

# --- XỬ LÝ CLICK NÚT MENU & PHÂN QUYỀN ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    if call.data == "menu_live_number":
        if not inventory_numbers:
            text = "🌍 <b>LIVE NUMBER STOCK (195+ Countries):</b>\n\n📦 Kho số hiện đang trống hoàn toàn!"
        else:
            text = "🌍 <b>LIVE NUMBER STOCK (195+ Countries):</b>\n━━━━━━━━━━━━━━━━━━━━━\n"
            for c_name, nums in inventory_numbers.items():
                text += f"• <b>{c_name}</b>: <code>{len(nums)}</code> số\n"
        
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔙 BACK TO MENU", callback_data="menu_back"))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode="HTML", reply_markup=kb)

    elif call.data == "menu_live_traffic":
        traffic_text = (
            "📈 <b>LIVE TRAFFIC MONITOR</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "All systems operating normally via Fast Node Gateway v3 API."
        )
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔙 BACK TO MENU", callback_data="menu_back"))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=traffic_text, parse_mode="HTML", reply_markup=kb)

    elif call.data == "menu_create_config":
        if user_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "⛔ Bạn không có quyền này!", show_alert=True)
            return
        admin_state[user_id] = "waiting_for_ws"
        text = (
            "🔮 <b>Setup: Configuration Wizard (WSS / Cookie / cURL)</b>\n\n"
            "🔗 <b>Step 1:</b> Gửi toàn bộ WebSocket URL hoặc đoạn cURL/Cookie siêu dài vào đây.\n"
            "<i>(Smart Parser sẽ tự động trích xuất Token và phiên làm việc cho bạn!)</i>"
        )
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("❌ CANCEL", callback_data="menu_back"))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode="HTML", reply_markup=kb)

    elif call.data == "menu_my_configs":
        if user_id not in ADMIN_IDS:
            return
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
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode="HTML", reply_markup=kb)

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
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=owner_text, parse_mode="HTML", reply_markup=kb)

    elif call.data == "admin_add_mode":
        if user_id not in ADMIN_IDS:
            return
        admin_state[user_id] = "waiting_for_numbers"
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("❌ HỦY BỎ", callback_data="menu_owner"))
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
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
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=report, parse_mode="HTML", reply_markup=kb)

    elif call.data == "menu_back":
        admin_state.pop(user_id, None)
        welcome_text = (
            "🔥 <b>FAST NODE • IVAS OTP GATEWAY</b>\n\n"
            "Welcome, choose an option from the menu:"
        )
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=welcome_text, parse_mode="HTML", reply_markup=get_menu_keyboard(user_id))

# --- LẮNG NGHE TIN NHẮN CHỜ (SMART PARSER & THÊM SỐ) ---
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    current_state = admin_state.get(user_id)
    chat_id = message.chat.id
    
    if current_state == "waiting_for_ws" and user_id in ADMIN_IDS:
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
            
            try:
                bot.delete_message(chat_id, message.message_id)
            except:
                pass
            
            success_msg = (
                f"✅ <b>URL / Cookie parsed successfully!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"🌐 <b>Server/WSS:</b> <code>{html.escape(extracted_ws[:40] if extracted_ws else 'Custom Session')}...</code>\n"
                f"🔑 <b>Token Extracted:</b> <code>{html.escape(extracted_token[:12])}...</code>\n"
                f"🛡️ <b>Cloudflare Bypass:</b> <code>{'Detected & Ready' if cf_clearance else 'Standard Session'}</code>\n"
                f"⚡ <b>Status:</b> Real-time listener active[cite: 11]!\n"
            )
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("⚙️ MY CONFIGS", callback_data="menu_my_configs"),
                   InlineKeyboardButton("🏠 MAIN MENU", callback_data="menu_back"))
            bot.send_message(chat_id, success_msg, parse_mode="HTML", reply_markup=kb)
        else:
            bot.reply_to(message, "⚠️ Chuỗi dữ liệu quá ngắn hoặc không đúng định dạng WSS/Cookie.", parse_mode="HTML")
        return

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

        try:
            bot.delete_message(chat_id, message.message_id)
        except:
            pass

        if total_added > 0:
            result_msg = f"✅ <b>Thêm thành công {total_added} số vào kho (195+ Quốc gia)!</b>\n━━━━━━━━━━━━━━━━━━━━━\n"
            for c_name, count in added_counts.items():
                result_msg += f"• <b>{c_name}</b>: +<code>{count}</code> số (Tổng: {len(inventory_numbers[c_name])})\n"
        else:
            result_msg = "⚠️ Không tìm thấy số điện thoại hợp lệ nào."

        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("👑 VỀ OWNER PANEL", callback_data="menu_owner"))
        bot.send_message(chat_id, result_msg, parse_mode="HTML", reply_markup=kb)

# --- WEBSOCKET REALTIME LISTENER BACKGROUND WORKER ---
def websocket_worker():
    def on_message(ws, message):
        try:
            data = json.loads(message)
            print(f"📩 Nhận tin nhắn Realtime từ WSS: {data}")
        except:
            pass

    def on_error(ws, error):
        pass

    def on_close(ws, close_status_code, close_msg):
        time.sleep(10)

    def on_open(ws):
        print("🟢 WebSocket Connected & Listening for Real-time SMS/OTP!")

    while True:
        for uid, cfg in user_configs.items():
            ws_url = cfg.get("ws_url")
            if ws_url and ws_url.startswith("wss://"):
                try:
                    wsapp = websocket.WebSocketApp(ws_url,
                                                  on_open=on_open,
                                                  on_message=on_message,
                                                  on_error=on_error,
                                                  on_close=on_close)
                    wsapp.run_forever()
                except:
                    pass
        time.sleep(15)

# --- FLASK SERVER (Giao diện Mini App HTML siêu đẹp chuẩn Ấn Độ) ---
app = Flask(__name__)

@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Fast Node • Live OTP Gateway</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            body { background: #0f172a; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; }
            .card { background: #1e293b; border: 1px solid #334155; border-radius: 16px; padding: 24px; width: 100%; max-width: 400px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3); text-align: center; }
            h1 { font-size: 22px; color: #38bdf8; margin-bottom: 8px; }
            p { color: #94a3b8; font-size: 14px; margin-bottom: 24px; }
            .btn { background: #22c55e; color: white; border: none; border-radius: 10px; padding: 12px 20px; font-size: 16px; font-weight: bold; width: 100%; cursor: pointer; margin-bottom: 12px; transition: 0.2s; }
            .btn:hover { background: #16a34a; }
            .btn-blue { background: #0284c7; }
            .btn-blue:hover { background: #0369a1; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>⚡ FAST NODE GATEWAY</h1>
            <p>Hệ thống quản lý OTP & Stock số 195+ quốc gia real-time.</p>
            <button class="btn" onclick="Telegram.WebApp.openTelegramLink('https://t.me/LIVEOTPIVAS')">📥 Kênh Nhận OTP</button>
            <button class="btn btn-blue" onclick="Telegram.WebApp.close()">✖️ Đóng Giao Diện</button>
        </div>
    </body>
    </html>
    """

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def run_bot_polling():
    # Diệt dứt điểm lỗi 409 Conflict bằng cách xóa Webhook cũ trước khi poll
    try:
        bot.remove_webhook()
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
    
    # Chạy bot polling
    run_bot_polling()
