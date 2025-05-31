from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.utils.exceptions import BotBlocked
from datetime import datetime, timedelta, date
import logging
import os

import config
import db

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(bot)

logging.basicConfig(level=logging.INFO)

WELCOME_TEXT = (
    "Добро пожаловать в бота по сбоям Рунета. Теперь ты автоматически подписан на уведомления о сбоях в интернете. 🌐\n"
    "Если надоест — блокируй бота и уведомления лететь тебе не будут ❤️\n"
    "Вся остальная информация и менеджеры ботов будут в описании самого бота 👇\n"
    "⚠️Главный бот - @downdetect0rbot\n"
    "Спасибо, что остаетесь с нами! 👥"
)

ADMIN_TEXT = (
    "👤Администраторы данного бота:\n"
    "🤴@internetmodel - владелец, по вопросам в разработке бота - к нему\n"
    "🧑‍💻@overnightwatch - кодер, отвечает за работу серверов и их обслуживание"
)

COMMANDS_TEXT = (
    "/last - последние информации о сбоях\n"
    "/mirror - создание зеркала бота через @botfather\n"
    "/admins - администраторы бота (если вы хотите с ними связаться)"
)

ADMIN_LOG_ID = 602393297  # ID администратора, которому отправляются логи

# Служебная переменная для хранения текущей даты
current_log_date = date.today()

async def send_admin_log(text):
    try:
        await bot.send_message(ADMIN_LOG_ID, f"[ЛОГ] {text}")
    except Exception as e:
        logging.warning(f"Не удалось отправить лог администратору: {e}")

@dp.message_handler(commands=["start"])
async def handle_start(message: types.Message):
    ref_id = None
    if message.get_args():
        try:
            ref_id = int(message.get_args())
        except ValueError:
            pass
    db.add_user(message.from_user.id, referral_id=ref_id)
    await message.answer(WELCOME_TEXT)

@dp.message_handler(commands=["stats"])
async def handle_stats(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        return
    stats = db.get_stats()
    text = (
        f"📊 Статистика:\n"
        f"Всего пользователей: {stats['total']}\n"
        f"Заблокировали бота: {stats['blocked']}\n"
        f"Новых за день: {stats['daily']}\n"
        f"Новых за неделю: {stats['weekly']}\n"
        f"Новых за месяц: {stats['monthly']}"
    )
    await message.answer(text)

@dp.message_handler(commands=["broadcast"])
async def broadcast_message(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        return
    if not message.reply_to_message:
        await message.reply("Ответьте на сообщение, которое нужно отправить всем пользователям.")
        return

    text = message.reply_to_message.text
    db.save_last_message(text)
    count = 0
    for user_id in db.get_active_users():
        try:
            await bot.send_message(user_id, text)
            count += 1
        except BotBlocked:
            db.block_user(user_id)
        except Exception as e:
            await send_admin_log(f"Ошибка при отправке {user_id}: {e}")
    await message.answer(f"✅ Сообщение доставлено {count} пользователям.")
    await send_admin_log(f"Broadcast от {message.from_user.id}: доставлено {count} пользователям.")

@dp.message_handler(commands=["last"])
async def handle_last(message: types.Message):
    global current_log_date
    today = date.today()

    if today != current_log_date:
        db.clear_old_messages()
        current_log_date = today
        await send_admin_log("Сообщения очищены по окончании дня.")

    messages = db.get_last_messages(limit=5)
    if not messages:
        now = datetime.utcnow() + timedelta(hours=4)
        updated_time = now.strftime("%Y-%m-%d %H:%M")
        await message.answer(f"За сегодня не зафиксировано сбоев.\nОбновлено: {updated_time} (GMT+4)")
        return

    formatted = "\n\n".join(f"🕒 {msg['time']} (GMT+4):\n{msg['text']}" for msg in messages)
    await message.answer(f"📰 Последние сообщения от админов:\n\n{formatted}")

@dp.message_handler(commands=["admins"])
async def handle_admins(message: types.Message):
    await message.answer(ADMIN_TEXT)

@dp.message_handler(commands=["command"])
async def handle_command(message: types.Message):
    await message.answer(COMMANDS_TEXT)

@dp.message_handler(commands=["mirror"])
async def handle_mirror(message: types.Message):
    await message.answer("Чтобы создать зеркало бота, зайдите в @BotFather, нажмите /newbot и следуйте инструкциям.")

if __name__ == "__main__":
    executor.start_polling(dp)
