from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode
from aiogram.utils import executor
from aiogram.dispatcher.filters import Command
from aiogram.utils.exceptions import BotBlocked
import logging
from datetime import datetime
import pytz

import config
import db
import utils

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(bot)

logging.basicConfig(level=logging.INFO)

tz = pytz.timezone('Asia/Dubai') 

WELCOME_TEXT = (
    "Добро пожаловать в бота по сбоям Рунета. Теперь ты автоматически подписан на уведомления о сбоях в интернете. 🌐\n"
    "Если надоест — блокируй бота и уведомления лететь тебе не будут ❤️\n"
    "Вся остальная информация и менеджеры ботов будут в описании самого бота 👇\n"
    "⚠️Главный бот - @downdetect0rbot\n"
    "Спасибо, что остаетесь с нами! 👥"
)

ADMINS_TEXT = (
    "👤Администраторы данного бота:\n"
    "🤴@internetmodel - владелец, по вопросам в разработке бота - к нему\n"
    "🧑‍💻@overnightwatch - кодер, отвечает за работу серверов и их обслуживание"
)

COMMANDS_TEXT = (
    "Доступные команды:\n"
    "/last - последние информации о сбоях\n"
    "/mirror - создание зеркала бота через @botfather\n"
    "/admins - администраторы бота (если вы хотите с ними связаться)"
)

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

@dp.message_handler(commands=["ref"])
async def handle_ref(message: types.Message):
    link = await utils.generate_referral_link(bot, message.from_user.id)
    await message.answer(f"🔗 Ваша реферальная ссылка:\n{link}")

@dp.message_handler(commands=["broadcast"])
async def broadcast_message(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        return
    if not message.reply_to_message:
        await message.reply("Ответьте на сообщение, которое нужно отправить всем пользователям.")
        return

    text = message.reply_to_message.text
    now = datetime.now(tz)
    db.save_last_message(text, now.strftime("%Y-%m-%d %H:%M:%S"))
    
    count = 0
    for user_id in db.get_active_users():
        try:
            await bot.send_message(user_id, text)
            count += 1
        except BotBlocked:
            db.block_user(user_id)
        except Exception as e:
            logging.warning(f"Ошибка при отправке пользователю {user_id}: {e}")
    await message.answer(f"✅ Сообщение доставлено {count} пользователям.")

@dp.message_handler(commands=["last"])
async def handle_last(message: types.Message):
    last_messages = db.get_last_messages()
    if not last_messages:
        await message.answer("Пока нет сохраненных сообщений о сбоях.")
        return
    
    response = "📢 Последние сообщения о сбоях:\n\n"
    for msg in last_messages:
        response += f"🕒 {msg['timestamp']} (UTC+4)\n"
        response += f"{msg['message']}\n\n"
    
    await message.answer(response)

@dp.message_handler(commands=["admins"])
async def handle_admins(message: types.Message):
    await message.answer(ADMINS_TEXT)

@dp.message_handler(commands=["mirror"])
async def handle_mirror(message: types.Message):
    instructions = (
        "Чтобы создать зеркало этого бота:\n"
        "1. Перейдите к @BotFather\n"
        "2. Создайте нового бота с командой /newbot\n"
        "3. После создания получите токен бота\n"
        "4. Используйте этот токен для развертывания своего экземпляра бота\n\n"
    )
    await message.answer(instructions)

@dp.message_handler(commands=["command"])
async def handle_commands(message: types.Message):
    await message.answer(COMMANDS_TEXT)

from aiogram.utils.executor import start_webhook

if __name__ == "__main__":
   
    WEBHOOK_HOST = 'https://runet-failures-bot.onrender.com/'  
    WEBHOOK_PATH = '/webhook'
    WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
    

    WEBAPP_HOST = '0.0.0.0'  
    WEBAPP_PORT = 10000  
    
    async def on_startup(dp):
        await bot.set_webhook(WEBHOOK_URL)
        logging.info("Бот успешно запущен через вебхук")
    
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )
