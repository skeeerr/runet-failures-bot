from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode
from aiogram.utils import executor
from aiogram.dispatcher.filters import Command
from aiogram.utils.exceptions import BotBlocked
import logging

import config
import db
import utils

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(bot)

logging.basicConfig(level=logging.INFO)

WELCOME_TEXT = (
    "Добро пожаловать в бота по сбоям Рунета. Теперь ты автоматически подписан на уведомления о сбоях в интернете. "
    "Если надоест — блокируй бота и уведомления лететь тебе не будут ❤️\n"
    "Вся остальная информация о боте и менеджер — в описании бота. Спасибо, что остаетесь с нами!"
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

if __name__ == "__main__":
    executor.start_polling(dp)
