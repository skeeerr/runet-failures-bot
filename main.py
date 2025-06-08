import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.exceptions import BotBlocked

import config
import db

logging.basicConfig(level=logging.INFO)
bot = Bot(token=config.BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

apps = {
    "telegram": "https://downdetector.su/telegram",
    "youtube": "https://downdetector.su/youtube",
    "vkontakte": "https://downdetector.su/vkontakte",
    "tiktok": "https://downdetector.su/tiktok",
}

WELCOME_TEXT = (
    "Добро пожаловать в бота по сбоям Рунета. 🌐\n\n"
    "Вы автоматически подключены к системе мониторинга инцидентов крупных сервисов. "
    "Здесь можно посмотреть статистику, последние сбои, вашу реферальную активность и связаться с администраторами.\n\n"
    "⚠️Главный бот - @nosignalrubot\n"
    "Спасибо, что остаетесь с нами! 👥\n\n"
    "🔻Выберите пункт меню ниже:"
)

COMMANDS_TEXT = (
    "/last - последние сообщения от админов\n"
    "/ref - ваша реферальная ссылка\n"
    "/refstats - топ-10 по рефералам\n"
    "/admins - администраторы бота\n"
    "/admin - панель администратора (для админов)\n"
    "/broadcast <текст> - отправить сообщение всем пользователям (только для админов)"
)

ADMIN_TEXT = (
    "👤Администраторы данного бота:\n"
    "🧔@internetmodel - владелец (по всем вопросам - к нему) \n"
    "🧑‍💻@overnightwatch - кодер"
)

ADMIN_LOG_ID = config.ADMIN_IDS[0]

main_menu = InlineKeyboardMarkup(row_width=1).add(
    InlineKeyboardButton("🛠Сервисы", callback_data="menu_services"),
    InlineKeyboardButton("⚠️Последние сбои", callback_data="menu_last"),
    InlineKeyboardButton("🔗Реферальная ссылка", callback_data="menu_ref"),
    InlineKeyboardButton("👥 Администраторы бота", callback_data="menu_admins"),
    InlineKeyboardButton("🔹Доступные команды", callback_data="menu_commands")
)

# Хранилище рассылок по user_id
pending_broadcasts = {}

@dp.message_handler(commands=["start"])
async def handle_start(message: types.Message):
    ref_id = None
    if message.get_args():
        try:
            ref_id = int(message.get_args())
        except ValueError:
            pass
    full_name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip()
    db.add_user(message.from_user.id, name=full_name, referral_id=ref_id)
    await message.answer(WELCOME_TEXT, reply_markup=main_menu)

    if ref_id and ref_id != message.from_user.id:
        await bot.send_message(
            ADMIN_LOG_ID,
            f"👤 Новый пользователь: {full_name} зарегистрировался по рефералке от ID {ref_id}"
        )

@dp.message_handler(commands=["broadcast"])
async def broadcast_message(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        return await message.reply("⛔️ У вас нет доступа к этой команде.")

    text = message.get_args()
    if not text:
        return await message.reply("⚠️ Использование: /broadcast <текст сообщения>")

    pending_broadcasts[message.from_user.id] = text
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("✅ Отправить", callback_data="confirm_broadcast"),
        InlineKeyboardButton("❌ Отмена", callback_data="cancel_broadcast")
    )
    await message.reply(f"📢 <b>Предпросмотр рассылки:</b>\n\n{text}", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "confirm_broadcast")
async def confirm_broadcast(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    text = pending_broadcasts.get(user_id)
    if not text:
        return await callback.answer("Нет сообщения для рассылки.", show_alert=True)

    await callback.message.edit_text("📨 Рассылка началась, подождите...")

    users = db.get_all_user_ids()
    success, blocked, failed = 0, 0, 0

    for uid in users:
        try:
            await bot.send_message(uid, text)
            success += 1
        except BotBlocked:
            blocked += 1
        except Exception as e:
            logging.exception(e)
            failed += 1

    del pending_broadcasts[user_id]

    await bot.send_message(user_id,
        f"✅ Рассылка завершена:\n\n"
        f"📬 Доставлено: {success}\n"
        f"🚫 Заблокировали бота: {blocked}\n"
        f"❗️ Ошибок: {failed}"
    )

@dp.callback_query_handler(lambda c: c.data == "cancel_broadcast")
async def cancel_broadcast(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id in pending_broadcasts:
        del pending_broadcasts[user_id]
    await callback.message.edit_text("❌ Рассылка отменена.")

@dp.callback_query_handler(lambda c: c.data == "menu_admins")
async def menu_admins(callback: types.CallbackQuery):
    await callback.message.delete()
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Назад", callback_data="menu_main"))
    await bot.send_message(callback.from_user.id, ADMIN_TEXT, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "menu_admin")
async def menu_admin_panel(callback: types.CallbackQuery):
    await callback.message.delete()
    if callback.from_user.id not in config.ADMIN_IDS:
        return await bot.send_message(callback.from_user.id, "⛔️ У вас нет доступа к админ-панели")

    kb = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("📢 Сделать рассылку", callback_data="admin_broadcast"),
        InlineKeyboardButton("⬅️ Назад", callback_data="menu_main")
    )
    await bot.send_message(callback.from_user.id, "🛠 Админ-панель:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "admin_broadcast")
async def prompt_broadcast(callback: types.CallbackQuery):
    await callback.message.delete()
    await bot.send_message(callback.from_user.id, "✏️ Введите сообщение для рассылки как ответ на это сообщение.")

@dp.message_handler(lambda msg: msg.reply_to_message and "Введите сообщение для рассылки" in msg.reply_to_message.text)
async def handle_broadcast_reply(msg: types.Message):
    if msg.from_user.id not in config.ADMIN_IDS:
        return await msg.reply("⛔️ У вас нет доступа к этой команде.")

    text = msg.text
    pending_broadcasts[msg.from_user.id] = text

    kb = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("✅ Отправить", callback_data="confirm_broadcast"),
        InlineKeyboardButton("❌ Отмена", callback_data="cancel_broadcast")
    )
    await msg.reply(f"📢 <b>Предпросмотр рассылки:</b>\n\n{text}", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "menu_main")
async def return_main_menu(callback: types.CallbackQuery):
    await callback.message.delete()
    await bot.send_message(callback.from_user.id, WELCOME_TEXT, reply_markup=main_menu)

async def main():
    db.init_db()
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())




