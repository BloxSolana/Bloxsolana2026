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
admin_state = {}           # Lưu trạng thái chờ nhập số của admin: {user_id: "waiting_for_numbers"}

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

# --- BẮT SỰ KIỆN /START (Giao diện Menu Đầy Đủ) ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "🔥 <b>FAST NODE • LIVE OTP GATEWAY</b>\n\n"
        "Welcome, choose an option from the menu:"
    )
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("LIVE NUMBER", callback_data="menu_live_number"),
        InlineKeyboardButton("LIVE TRAFFIC", callback_data="menu_live_traffic")
    )
    kb.add(
        InlineKeyboardButton("INVITE FRIEND", callback_data="menu_invite"),
        InlineKeyboardButton("WALLET", callback_data="menu_wallet")
    )
    kb.add(
        InlineKeyboardButton("LEADERBOARD", callback_data="menu_leaderboard")
    )
    kb.add(
        InlineKeyboardButton("OWNER PANEL", callback_data="menu_owner")
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="HTML", reply_markup=kb)

# --- XỬ LÝ CLICK NÚT MENU INTERACTIVE ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    
    if call.data == "menu_live_number":
        # Hiển thị tổng kho số theo quốc gia
        if not inventory_numbers:
            text = "🌍 <b>LIVE NUMBER STOCK:</b>\n\n📦 Kho số hiện đang trống hoàn toàn!"
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

    elif call.data == "menu_invite":
        bot.answer_callback_query(call.id, "Tính năng mời bạn bè đang phát triển!")
    elif call.data == "menu_wallet":
        bot.answer_callback_query(call.id, "Số dư ví: 0 VND")

    elif call.data == "menu_leaderboard":
        bot.answer_callback_query(call.id, "Đang cập nhật bảng xếp hạng...")

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
                 "Hãy gửi ngay danh sách số điện thoại của bro vào khung chat này (có thể gửi 10, 100 hay hàng ngàn số, có hoặc không có dấu <code>+</code>).\n\n"
                 "Bot sẽ tự động nhận diện đầu số, phân loại vào đúng quốc gia và cộng dồn vào kho!",
            parse_mode="HTML",
            reply_markup=kb
        )

    elif call.data == "admin_stock":
        if user_id not in ADMIN_IDS:
            return
        if not inventory_numbers:
            report = "📦 <b>Kho số hiện đang trống!</b>"
        else:
            report = "📊 <b>FAST NODE - LIVE STOCK REPORT</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
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
            "🔥 <b>FAST NODE • LIVE OTP GATEWAY</b>\n\n"
            "Welcome, choose an option from the menu:"
        )
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("LIVE NUMBER", callback_data="menu_live_number"),
            InlineKeyboardButton("LIVE TRAFFIC", callback_data="menu_live_traffic")
        )
        kb.add(
            InlineKeyboardButton("INVITE FRIEND", callback_data="menu_invite"),
            InlineKeyboardButton("WALLET", callback_data="menu_wallet")
        )
        kb.add(
            InlineKeyboardButton("LEADERBOARD", callback_data="menu_leaderboard")
        )
        kb.add(
            InlineKeyboardButton("OWNER PANEL", callback_data="menu_owner")
        )
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=welcome_text, parse_mode="HTML", reply_markup=kb)

    elif call.data == "menu_close":
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass

# --- LẮNG NGHE TIN NHẮN ĐỂ NHẬN SỐ THỦ CÔNG TỪ ADMIN ---
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    
    # Kiểm tra xem admin có đang bật chế độ chờ nhập số không
    if user_id in ADMIN_IDS and admin_state.get(user_id) == "waiting_for_numbers":
        text_content = message.text
        # Tách danh sách số bằng khoảng trắng, xuống dòng hoặc dấu phẩy
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

        # Tắt trạng thái chờ sau khi nhận xong
        admin_state.pop(user_id, None)

        if total_added > 0:
            result_msg = f"✅ <b>Thêm thành công {total_added} số vào kho!</b>\n━━━━━━━━━━━━━━━━━━━━━\n"
            for c_name, count in added_counts.items():
                result_msg += f"• <b>{c_name}</b>: +<code>{count}</code> số\n"
            result_msg += f"\n🔥 <b>Tổng số lượng trong kho quốc gia đó hiện tại:</b> <code>{len(inventory_numbers[c_name])}</code> số"
        else:
            result_msg = "⚠️ Không tìm thấy số điện thoại hợp lệ nào trong nội dung bro vừa gửi."

        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("👑 VỀ OWNER PANEL", callback_data="menu_owner"))
        bot.reply_to(message, result_msg, parse_mode="HTML", reply_markup=kb)

# --- XEM KHO SỐ HIỆN CÓ (/STOCK) ---
@bot.message_handler(commands=['stock'])
def show_stock(message):
    if not inventory_numbers:
        bot.reply_to(message, "📦 <b>Kho số hiện đang trống!</b>", parse_mode="HTML")
        return
    
    report = "📊 <b>FAST NODE - LIVE STOCK REPORT</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    total_all = 0
    for country, numbers in inventory_numbers.items():
        count = len(numbers)
        total_all += count
        report += f"🌍 <b>{country}</b>: <code>{count}</code> số\n"
    
    report += f"\n━━━━━━━━━━━━━━━━━━━━━\n🔥 <b>Tổng số lượng toàn hệ thống:</b> <code>{total_all}</code> số"
    bot.reply_to(message, report, parse_mode="HTML")

# --- LỆNH THUÊ SỐ (/THUE) ---
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
               f"<b>📱 ɴ🇺ᴍʙᴇՐ:</b> <code>{html.escape(str(masked))}</code>\n"
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
    bot.re
