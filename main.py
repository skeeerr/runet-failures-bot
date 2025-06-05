import asyncio
import aiohttp
import logging
import subprocess
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor
from aiogram.utils.exceptions import BotBlocked
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, date

import config
import db

bot = Bot(token=config.BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

logging.basicConfig(level=logging.INFO)

apps = {
    "telegram": "https://downdetector.su/status/telegram/",
    "youtube": "https://downdetector.su/status/youtube/",
    "vkontakte": "https://downdetector.su/status/vkontakte/",
    "tiktok": "https://downdetector.su/status/tiktok/",
}

WELCOME_TEXT = (
    "Добро пожаловать в бота по сбоям Рунета. 🌐\n\n"
    "Вы автоматически подключены к системе мониторинга инцидентов крупных сервисов. "
    "Здесь можно посмотреть статистику, последние сбои, вашу реферальную активность и связаться с администраторами.\n\n"
    "⚠️Главный бот - @nosignalrubot\n"
    "Спасибо, что остаетесь с нами! 👥\n\n"
    "👇Выберите пункт меню ниже:"
)

COMMANDS_TEXT = (
    "/last - последние сообщения от админов\n"
    "/ref - ваша реферальная ссылка\n"
    "/refstats - топ-10 по рефералам\n"
    "/admins - администраторы бота\n"
    "/admin - панель администратора (для админов)"
)

ADMIN_TEXT = (
    "👤Администраторы данного бота:\n"
    "🤴@internetmodel - владелец\n"
    "🧑‍💻@overnightwatch - кодер"
)

ADMIN_LOG_ID = config.ADMIN_IDS[0]

main_menu = InlineKeyboardMarkup(row_width=1).add(
    InlineKeyboardButton("🛠️Сервисы", callback_data="menu_services"),
    InlineKeyboardButton("⚠️Последние сбои", callback_data="menu_last"),
    InlineKeyboardButton("🔗Реферальная ссылка", callback_data="menu_ref"),
    InlineKeyboardButton("👥 Администраторы бота", callback_data="menu_admins"),
    InlineKeyboardButton("🕹️Доступные команды", callback_data="menu_commands")
)

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

@dp.callback_query_handler(lambda c: c.data == "menu_main")
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.delete()
    await bot.send_message(callback.from_user.id, WELCOME_TEXT, reply_markup=main_menu)

@dp.callback_query_handler(lambda c: c.data == "menu_services")
async def menu_services(callback: types.CallbackQuery):
    await callback.message.delete()
    kb = InlineKeyboardMarkup(row_width=2)
    for name in apps:
        kb.insert(InlineKeyboardButton(name.capitalize(), callback_data=f"app_{name}"))
    kb.add(InlineKeyboardButton("⬅️ Назад", callback_data="menu_main"))
    await bot.send_message(callback.from_user.id, "Выберите сервис для просмотра жалоб:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("app_"))
async def show_app_stats(callback: types.CallbackQuery):
    name = callback.data[4:]
    await callback.message.delete()

    # Генерация графика с помощью Puppeteer
    try:
        result = subprocess.run(["node", "make_graph.js", name], capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            raise Exception(result.stderr)
        img_path = f"graphs/{name}_graph.png"
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"Файл графика не найден: {img_path}")

        text = (
            f"⚠️Информация о работе {name.capitalize()}\n\n"
            f"📊 График жалоб за последние часы\n\n"
            f"🛜@nosignalrubot"
        )
        back = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Назад", callback_data="menu_services"))
        with open(img_path, "rb") as photo:
            await bot.send_photo(callback.from_user.id, photo=photo, caption=text, reply_markup=back)
    except Exception as e:
        await bot.send_message(callback.from_user.id, f"Не удалось сгенерировать график: {e}")

@dp.callback_query_handler(lambda c: c.data == "menu_last")
async def menu_last(callback: types.CallbackQuery):
    await callback.message.delete()
    messages = db.get_last_messages(limit=5)
    if not messages:
        now = datetime.utcnow() + timedelta(hours=4)
        updated_time = now.strftime("%Y-%m-%d %H:%M")
        text = f"За сегодня не зафиксировано сбоев.\nОбновлено: {updated_time} (GMT+4)"
    else:
        text = "📰 Последние сообщения от админов:\n\n" + "\n\n".join(
            f"🕒 {msg['time']} (GMT+4):\n{msg['text']}" for msg in messages
        )
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Назад", callback_data="menu_main"))
    await bot.send_message(callback.from_user.id, text, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "menu_ref")
async def menu_ref(callback: types.CallbackQuery):
    await callback.message.delete()
    user_id = callback.from_user.id
    bot_username = (await bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start={user_id}"
    count = db.get_referral_count(user_id)
    rank = db.get_referral_ranking(user_id)
    text = (
        f"✔️ <a href=\"{referral_link}\">ссылка</a> — вот твоя реферальная ссылка для приглашения людей в бота.\n\n"
        f"🎯Всего приглашено: {count}\n"
        f"🥇Ваш рейтинг в списке рефералов: {rank}"
    )
    kb = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("🔗 Поделиться ссылкой", url=referral_link),
        InlineKeyboardButton("🤴 Топ пригласивших пользователей", callback_data="menu_refstats"),
        InlineKeyboardButton("⬅️ Назад", callback_data="menu_main")
    )
    await bot.send_message(callback.from_user.id, text, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "menu_refstats")
async def menu_refstats(callback: types.CallbackQuery):
    await callback.message.delete()
    top_users = db.get_top_referrers(limit=10)
    if not top_users:
        text = "Реферальная статистика пока пуста."
    else:
        lines = []
        for i, user in enumerate(top_users):
            name = user['name'] if user['name'] else f"id:{user['user_id']}"
            lines.append(f"{i+1}. {name} — {user['count']} приглашённых")
        text = "🏆 Топ-10 пользователей по реферальным приглашениям:\n\n" + "\n".join(lines)
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Назад", callback_data="menu_ref"))
    await bot.send_message(callback.from_user.id, text, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "menu_admins")
async def menu_admins(callback: types.CallbackQuery):
    await callback.message.delete()
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Назад", callback_data="menu_main"))
    await bot.send_message(callback.from_user.id, ADMIN_TEXT, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "menu_commands")
async def menu_commands(callback: types.CallbackQuery):
    await callback.message.delete()
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Назад", callback_data="menu_main"))
    await bot.send_message(callback.from_user.id, COMMANDS_TEXT, reply_markup=kb)

# Запуск
async def main():
    db.init_db()
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())



