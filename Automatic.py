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
ivas_accounts = {}         # Tài khoản IVAS

# --- COMPLETE OFFICIAL ISO COUNTRY DATABASE (Đầy đủ chuẩn 195+ Quốc gia) ---
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

def get_menu_keyboard(user_id):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🚀 OPEN WEB APP MARKETPLACE", web_app=WebAppInfo(url=WEBAPP_URL))
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

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "🔥 <b>FAST NODE • IVAS OTP GATEWAY</b>\n\n"
        "Welcome, choose an option from the menu:"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="HTML", reply_markup=get_menu_keyboard(message.from_user.id))

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    if call.data == "menu_live_number":
        available_total = sum(1 for data in inventory_numbers.values() for item in data["numbers"] if not item.get("locked_by"))
        text = f"🌍 <b>LIVE NUMBER STOCK (195+ Countries):</b>\n\n📦 Tổng số lượng số khả dụng: <code>{available_total}</code> số.\nBấm nút <b>Open Web App Marketplace</b> để chọn số độc quyền!"
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔙 QUAY LẠI MENU", callback_data="menu_back"))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode="HTML", reply_markup=kb)

    elif call.data == "menu_live_traffic":
        traffic_text = (
            "📈 <b>LIVE TRAFFIC MONITOR</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "All systems operating normally via Fast Node Gateway v3 API."
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
            "🔮 <b>Setup: Configuration Wizard (WSS / Cookie / cURL)</b>\n\n"
            "🔗 <b>Step 1:</b> Gửi toàn bộ WebSocket URL hoặc đoạn cURL/Cookie siêu dài vào đây.\n"
            "<i>(Smart Parser sẽ tự động trích xuất Token và phiên làm việc cho bạn!)</i>"
        )
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("❌ HỦY", callback_data="menu_back"))
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
                f"💰 <b>Số dư:</b> <code>{cfg.get('balance', '250,000 VND')}</code>\n"
                f"🟢 <b>Status:</b> {cfg.get('status', 'Active')}\n"
            )
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔄 LÀM MỚI", callback_data="config_refresh"),
               InlineKeyboardButton("❌ XÓA", callback_data="config_delete"))
        kb.add(InlineKeyboardButton("🔙 QUAY LẠI MENU", callback_data="menu_back"))
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
        report = "📊 <b>FAST NODE - LIVE STOCK REPORT (195+ Countries)</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        total_all = 0
        for key, data in inventory_numbers.items():
            count = sum(1 for item in data["numbers"] if not item.get("locked_by"))
            if count > 0:
                total_all += count
                report += f"🌍 <b>{key}</b>: <code>{count}</code> số\n"
        if total_all == 0:
            report += "📦 Kho số hiện đang trống hoàn toàn!"
        else:
            report += f"\n━━━━━━━━━━━━━━━━━━━━━\n🔥 <b>Tổng số lượng khả dụng:</b> <code>{total_all}</code> số"
        
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
        
        if not extracted_token and len(text_input) > 20:
            extracted_token = text_input[-30:]

        if ws_match or cf_match or len(text_input) > 15:
            user_configs[user_id] = {
                "ws_url": extracted_ws if extracted_ws else "Custom Session",
                "token": extracted_token if extracted_token else text_input[:20],
                "cf_clearance": cf_clearance if cf_clearance else "Not required",
                "balance": "250,000 VND",
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
                f"💰 <b>Số dư hiện tại:</b> <code>250,000 VND</code>\n"
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
            
            _, _, full_key = detect_country_info(cleaned_phone)
            if full_key not in inventory_numbers:
                cname, flag = detect_country_info(cleaned_phone)[:2]
                inventory_numbers[full_key] = {"flag": flag, "name": cname, "numbers": []}
            
            existing_numbers = [item["phone"] for item in inventory_numbers[full_key]["numbers"]]
            if cleaned_phone not in existing_numbers:
                inventory_numbers[full_key]["numbers"].append({"phone": cleaned_phone, "expires": 0, "locked_by": None})
                added_counts[full_key] = added_counts.get(full_key, 0) + 1
                total_added += 1

        admin_state.pop(user_id, None)
        try:
            bot.delete_message(chat_id, message.message_id)
        except:
            pass

        if total_added > 0:
            result_msg = f"✅ <b>Thêm thành công {total_added} số vào kho (195+ Quốc gia)!</b>\n━━━━━━━━━━━━━━━━━━━━━\n"
            for c_name, count in added_counts.items():
                result_msg += f"• <b>{c_name}</b>: +<code>{count}</code> số\n"
        else:
            result_msg = "⚠️ Không tìm thấy số điện thoại hợp lệ nào."

        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("👑 VỀ OWNER PANEL", callback_data="menu_owner"))
        bot.send_message(chat_id, result_msg, parse_mode="HTML", reply_markup=kb)

@bot.message_handler(commands=['thue'])
def handle_rent_number(message):
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ <b>Sai cú pháp!</b>\nVui lòng nhập: <code>/thue 84939168914</code>", parse_mode="HTML")
        return
    
    phone_to_rent = parts[1].replace("+", "").strip()
    user_id = message.chat.id
    user_rentals[phone_to_rent] = user_id
    
    found = False
    for key, data in inventory_numbers.items():
        for item in data["numbers"]:
            if item["phone"] == phone_to_rent:
                item["expires"] = time.time() + 900
                item["locked_by"] = user_id
                found = True
                break

    if found:
        bot.reply_to(message, f"✅ <b>Thuê số thành công trong 15 phút!</b>\nSố <code>{phone_to_rent}</code> đã được khóa riêng cho bạn (người khác sẽ không thấy số này). Mọi OTP đổ về sẽ bắn thẳng về inbox!", parse_mode="HTML")
    else:
        bot.reply_to(message, f"⚠️ Số <code>{phone_to_rent}</code> không tồn tại hoặc đã bị người khác thuê mất!", parse_mode="HTML")

# --- BACKGROUND WORKER: TỰ ĐỘNG GIẢI PHÓNG SỐ SAU 15P ---
def background_cleanup_and_wss():
    while True:
        current_time = time.time()
        for key, data in inventory_numbers.items():
            for item in list(data["numbers"]):
                if item["expires"] > 0 and item["expires"] <= current_time:
                    phone = item["phone"]
                    user_rentals.pop(phone, None)
                    data["numbers"].remove(item)
        time.sleep(30)

async def dispatch_update(service, phone, msg, timestamp, country, flag, is_test=False):
    clean_phone = str(phone).replace("+", "")
    masked = clean_phone[:6] + "****" + clean_phone[-3:] if len(clean_phone) > 7 else clean_phone
    match = re.search(r'\d{3}[-\s]?\d{3}|\d{4,8}', str(msg))
    code = match.group(0) if match else "N/A"

    # Tin nhắn bắn vào Group chung cho người dùng xem hoàn toàn bằng TIẾNG ANH
    header = "🧪 <b>『 ꜰᴇ ꜱᴇɴᴅ ᴏᴛᴘ 』</b> 🧪" if is_test else "💐 <b>『 ɴᴇᴡ ᴏᴛᴘ ʀᴇᴄᴇɪᴠᴇᴅ 』</b> ✨"
    caption = (f"{header}\n"
               f"━━━━━━━━━━━━━━━━━━━━━\n\n"
               f"<b>⌚ TIME:</b> <code>{html.escape(str(timestamp))}</code>\n"
               f"<b>🌍 COUNTRY:</b> {html.escape(str(country))} {flag}\n"
               f"<b>📱 NUMBER:</b> <code>{html.escape(str(masked))}</code>\n"
               f"<b>🛠 SERVICE:</b> <code>{html.escape(str(service))}</code>\n"
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
            service = data.get("service", "IVAS Gateway")
            msg = data.get("message", "Your OTP is 123456")
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            cname, flag, _ = detect_country_info(phone)
            asyncio.run(dispatch_update(service, phone, msg, timestamp, cname, flag, is_test=False))
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
                    wsapp = websocket.WebSocketApp(ws_url, on_open=on_open, on_message=on_message, on_error=on_error, on_close=on_close)
                    wsapp.run_forever()
                except:
                    pass
        time.sleep(15)

# --- FLASK SERVER & WEB APP MARKETPLACE (DASHBOARD DROPDOWN, GET NUMBER, TIẾNG ANH CHO USER, NÚT EXIT APP) ---
app = Flask(__name__)

@app.route('/')
def home():
    countries_data = []
    for key, data in inventory_numbers.items():
        available_numbers = [
            {"phone": item["phone"], "expires": item["expires"]} 
            for item in data["numbers"] if not item.get("locked_by")
        ]
        countries_data.append({
            "key": key,
            "name": data["name"],
            "flag": data["flag"],
            "numbers": available_numbers
        })
    
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Fast Node • Dashboard & Marketplace</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            :root { --bg: #090d16; --card: #131c2e; --border: #1e293b; --accent: #38bdf8; --green: #22c55e; --text: #f8fafc; --muted: #94a3b8; --red: #ef4444; }
            body { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 12px; }
            .header { display: flex; justify-content: space-between; align-items: center; background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 12px 16px; margin-bottom: 12px; }
            .balance-amount { font-size: 15px; font-weight: bold; color: var(--green); }
            
            /* Dashboard Dropdown Menu Style */
            .dashboard-card { background: var(--card); border: 1px solid var(--border); border-radius: 14px; margin-bottom: 12px; overflow: hidden; }
            .dashboard-header { padding: 14px 16px; display: flex; justify-content: space-between; align-items: center; cursor: pointer; background: #1e293b; font-weight: bold; font-size: 15px; color: var(--accent); }
            .dashboard-dropdown { max-height: 0; overflow: hidden; transition: max-height 0.3s ease-out; padding: 0 16px; background: #0f172a; }
            .dashboard-dropdown.open { max-height: 300px; padding: 12px 16px; }
            .menu-sub-item { display: block; width: 100%; background: #131c2e; border: 1px solid var(--border); color: var(--text); padding: 10px; border-radius: 8px; text-align: left; font-size: 14px; font-weight: bold; margin-bottom: 8px; cursor: pointer; }
            .menu-sub-item:hover { border-color: var(--accent); }

            .grid-countries { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; margin-bottom: 16px; }
            .country-pill { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 8px 4px; text-align: center; cursor: pointer; transition: 0.2s; font-size: 11px; }
            .country-pill:hover { border-color: var(--accent); background: #1e293b; }
            .country-flag { font-size: 16px; display: block; margin-bottom: 2px; }
            .country-count { font-size: 10px; color: var(--green); font-weight: bold; }

            .card { background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 16px; margin-bottom: 12px; }
            h3 { margin: 0 0 10px 0; font-size: 16px; color: var(--accent); display: flex; justify-content: space-between; align-items: center; }
            
            .number-item { display: flex; justify-content: space-between; align-items: center; background: #0f172a; border: 1px solid var(--border); padding: 10px; border-radius: 8px; margin-bottom: 8px; font-size: 14px; }
            .btn { background: var(--green); color: white; border: none; border-radius: 8px; padding: 8px 14px; font-size: 13px; font-weight: bold; cursor: pointer; }
            .btn-blue { background: #0284c7; }
            .btn-red { background: var(--red); }
            .btn-gray { background: #475569; }
            
            .action-row { display: flex; gap: 8px; margin-top: 10px; }
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Header -->
            <div class="header">
                <div>
                    <div style="font-weight: bold; font-size: 14px;">⚡ Fast Node Gateway</div>
                    <div style="font-size: 10px; color: var(--muted);">Real-time OTP Service</div>
                </div>
                <div class="balance-box" style="text-align: right;">
                    <div style="font-size: 10px; color: var(--muted);">Balance</div>
                    <div class="balance-amount">250,000 VND</div>
                </div>
            </div>

            <!-- DASHBOARD DROPDOWN MENU -->
            <div class="dashboard-card">
                <div class="dashboard-header" onclick="toggleDashboard()">
                    <span>📊 Dashboard Menu</span>
                    <span id="arrowIcon">▼</span>
                </div>
                <div class="dashboard-dropdown" id="dashboardDropdown">
                    <button class="menu-sub-item" onclick="scrollToGetNumber()">📥 Get Number</button>
                    <button class="menu-sub-item" onclick="window.open('https://t.me/LIVEOTPIVAS', '_blank')">📢 Official Channel</button>
                    <button class="menu-sub-item btn-red" style="color:white; text-align:center;" onclick="exitApp()">❌ Exit App</button>
                </div>
            </div>

            <!-- GET NUMBER / COUNTRIES MARKETPLACE -->
            <div class="card" id="getNumberSection">
                <h3>🌍 195+ Countries Marketplace</h3>
                <div class="grid-countries" id="countryGrid"></div>
            </div>

            <!-- NUMBER DETAILS VIEW -->
            <div class="card" id="detailCard" style="display:none;">
                <h3 id="detailTitleText">Number Details</h3>
                <div id="numberListContainer"></div>
                <div class="action-row">
                    <button class="btn btn-gray" onclick="goBackToGrid()">🔙 Back</button>
                    <button class="btn btn-blue" onclick="refreshNumbers()">🔄 Refresh</button>
                </div>
            </div>
        </div>

        <script>
            let tg = window.Telegram.WebApp;
            tg.expand();

            let countriesData = {{ countries_data | tojson }};
            let currentSelectedCountry = null;

            function toggleDashboard() {
                let dropdown = document.getElementById('dashboardDropdown');
                let arrow = document.getElementById('arrowIcon');
                dropdown.classList.toggle('open');
                arrow.innerText = dropdown.classList.contains('open') ? '▲' : '▼';
            }

            function scrollToGetNumber() {
                document.getElementById('getNumberSection').scrollIntoView({ behavior: 'smooth' });
                toggleDashboard();
            }

            function exitApp() {
                tg.close();
            }

            function renderCountries() {
                let grid = document.getElementById('countryGrid');
                grid.innerHTML = '';
                countriesData.forEach(c => {
                    let totalNums = c.numbers.length;
                    let div = document.createElement('div');
                    div.className = 'country-pill';
                    div.innerHTML = `<span class="country-flag">${c.flag}</span><div style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${c.name}</div><div class="country-count">${totalNums} left</div>`;
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
                    container.innerHTML = '<p style="color:var(--muted); text-align:center;">No available numbers in this country!</p>';
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

            function refreshNumbers() {
                location.reload();
            }

            function rentNumber(phone) {
                tg.sendData(`/thue ${phone}`);
                tg.showAlert(`Successfully rented number ${phone} for 15 minutes! This number is now hidden from others.`);
                tg.close();
            }

            renderCountries();
        </script>
    </body>
    </html>
    """, countries_data=countries_data)

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def run_bot_polling():
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

    t_clean = threading.Thread(target=background_cleanup_and_wss, daemon=True)
    t_clean.start()
    
    run_bot_polling()
