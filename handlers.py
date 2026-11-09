import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, ReplyKeyboardRemove, CallbackQuery
from database import register_user, get_setting, is_admin, db_exec, safe, change_usd

logger = logging.getLogger("FAST_IVAS")

def setup_handlers(dp: Dispatcher, bot: Bot, webapp_url: str, admin_id: int):
    
    @dp.message(CommandStart())
    async def cmd_start(message: Message):
        try: await message.delete()
        except: pass
        args = message.text.split(maxsplit=1)
        ref = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
        await register_user(message.from_user, ref)
        
        if await get_setting("maintenance", "off") == "on" and not is_admin(message.from_user.id):
            return await message.answer("🛠 <b>HỆ THỐNG ĐANG BẢO TRÌ</b>\n\nVui lòng quay lại sau.")
        
        if webapp_url.startswith("https://"):
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚡ MỞ ỨNG DỤNG FAST IVAS", web_app=WebAppInfo(url=webapp_url))]])
            await message.answer("🚀 Chào mừng đến với <b>FAST IVAS</b>!\n\nVui lòng bấm nút bên dưới để mở ứng dụng.", reply_markup=ReplyKeyboardRemove())
            await message.answer("👇", reply_markup=kb)
        else:
            await message.answer("⚠️ Lỗi: Chưa cấu hình WEBAPP_URL.", reply_markup=ReplyKeyboardRemove())

    @dp.message(Command("admin"))
    async def cmd_admin(message: Message):
        if not is_admin(message.from_user.id): return
        await message.answer("🛡 <b>ADMIN PANEL</b>\n\nMở Mini App và vào mục ADMIN PANEL để quản lý.")

    @dp.message(Command("broadcast"))
    async def cmd_broadcast(message: Message):
        if not is_admin(message.from_user.id): return
        content = message.text.partition(" ")[2].strip()
        if not content: return await message.answer("Usage: /broadcast Message")
        users = await db_exec("SELECT user_id FROM users", fetch="all")
        sent = 0
        for row in users or []:
            try: await bot.send_message(row["user_id"], f"📢 <b>ANNOUNCEMENT</b>\n\n{content}"); sent += 1; await asyncio.sleep(0.05)
            except: pass
        await message.answer(f"Đã gửi {sent} tin nhắn.")

    @dp.callback_query(F.data.startswith("admin_bonus_"))
    async def process_bonus_callback(callback: CallbackQuery):
        data_parts = callback.data.split("_")
        action = data_parts[2] # accept or reject
        amount_milli = int(data_parts[3])
        
        if action == "accept":
            ok, res = await change_usd(callback.from_user.id, amount_milli, "ADMIN_BONUS", "Bonus from Admin")
            if ok:
                await callback.message.edit_text(f"✅ <b>Đã nhận số dư!</b>\nBạn đã chấp nhận nhận ${amount_milli/1000:.3f} từ Admin.")
            else:
                await callback.answer(f"Lỗi: {res}", show_alert=True)
        else:
            await callback.message.edit_text("❌ <b>Đã từ chối!</b>\nBạn đã từ chối nhận số dư từ Admin.")
        await callback.answer()

    @dp.message(F.text)
    async def handle_text(message: Message):
        if message.text.startswith('/'): return
        if await get_setting("maintenance", "off") == "on" and not is_admin(message.from_user.id):
            return await message.answer("🛠 <b>HỆ THỐNG ĐANG BẢO TRÌ</b>\n\nVui lòng quay lại sau.")
        await message.answer("Vui lòng mở Mini App để sử dụng các tính năng.")
