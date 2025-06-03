import asyncio
import aiohttp
import logging
import matplotlib.pyplot as plt
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

app_status = {name: False for name in apps}
current_log_date = date.today()

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
    "/ref - ваша реферальная ссылка\n"
    "/refstats - топ-10 по рефералам\n"
    "/admins - администраторы бота (если вы хотите с ними связаться)\n"
    "/admin - панель администратора (для админов)"
)

ADMIN_LOG_ID = config.ADMIN_IDS[0]

def draw_graph(values, name):
    plt.figure(figsize=(8, 3))
    plt.plot(values, marker='o', color='red')
    plt.title(f"Жалобы на {name.capitalize()}")
    plt.xlabel("Часы назад")
    plt.ylabel("Жалобы")
    plt.tight_layout()
    path = f"{name}_graph.png"
    plt.savefig(path)
    plt.close()
    return path

async def fetch_data(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")
            try:
                hourly = int(soup.select_one("div.report-count-hour span").text)
                daily = int(soup.select_one("div.report-count-day span").text)
                script = soup.find("script", string=lambda t: t and "Highcharts.chart" in t).text
                start = script.find("data: [") + 7
                end = script.find("]", start)
                values = [int(x.strip()) for x in script[start:end].split(",")]
                return hourly, daily, values
            except:
                return 0, 0, []

async def notify_users(text):
    for user_id in db.get_active_users():
        try:
            await bot.send_message(user_id, text)
        except:
            pass

async def send_admin_log(text):
    try:
        await bot.send_message(ADMIN_LOG_ID, f"[ЛОГ] {text}")
    except Exception as e:
        logging.warning(f"Не удалось отправить лог администратору: {e}")

async def monitor():
    while True:
        for name, url in apps.items():
            hourly, _, _ = await fetch_data(url)
            is_now_failing = hourly >= 40
            was_failing = app_status[name]
            if is_now_failing and not was_failing:
                app_status[name] = True
                await notify_users(f"⚠️Сбой в работе {name.capitalize()}\n\n🛜@nosignalrubot")
            elif not is_now_failing and was_failing:
                app_status[name] = False
                await notify_users(f"✅{name.capitalize()} - работа приложения восстановлена\n\n🛜@nosignalrubot")
        await asyncio.sleep(300)

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
    await message.answer(WELCOME_TEXT)

    if ref_id and ref_id != message.from_user.id:
        await bot.send_message(
            ADMIN_LOG_ID,
            f"👤 Новый пользователь: {full_name} зарегистрировался по рефералке от ID {ref_id}"
        )

@dp.message_handler(commands=["fail"])
async def handle_fail(message: types.Message):
    kb = InlineKeyboardMarkup(row_width=2)
    for name in apps:
        kb.insert(InlineKeyboardButton(name.capitalize(), callback_data=f"app_{name}"))
    await message.answer("Выберите приложение:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("app_"))
async def show_app_stats(callback: types.CallbackQuery):
    name = callback.data[4:]
    url = apps[name]
    hourly, daily, values = await fetch_data(url)
    path = draw_graph(values, name)

    text = (
        f"⚠️Информация о работе {name.capitalize()}\n"
        f"❗Жалоб за час: {hourly}\n"
        f"❕Жалоб за сутки: {daily}\n\n"
        f"🛜@nosignalrubot"
    )

    back = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Назад", callback_data="back"))
    await bot.send_photo(callback.message.chat.id, photo=open(path, "rb"), caption=text, reply_markup=back)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "back")
async def go_back(callback: types.CallbackQuery):
    await handle_fail(callback.message)
    await callback.answer()

@dp.message_handler(commands=["ref"])
async def handle_ref(message: types.Message):
    user_id = message.from_user.id
    bot_username = (await bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start={user_id}"
    count = db.get_referral_count(user_id)
    rank = db.get_referral_ranking(user_id)
    text = (
        f"✔️ <a href=\"{referral_link}\">ссылка</a> - вот твоя реферальная ссылка для приглашения людей в бота.\n\n"
        f"🎯Всего приглашено: {count}\n"
        f"🥇Ваш рейтинг в списке рефералов: {rank}"
    )
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🔗 Поделиться ссылкой", url=referral_link))
    await message.answer(text, reply_markup=kb)

@dp.message_handler(commands=["refstats"])
async def handle_ref_stats(message: types.Message):
    top_users = db.get_top_referrers(limit=10)
    if not top_users:
        await message.answer("Реферальная статистика пока пуста.")
        return
    lines = []
    for i, user in enumerate(top_users, start=1):
        name = user['name'] or f"id:{user['user_id']}"
        count = user['count']
        lines.append(f"{i}. {name} — {count} приглашённых")
    text = "🏆 Топ-10 пользователей по реферальным приглашениям:\n\n" + "\n".join(lines)
    await message.answer(text)

@dp.message_handler(commands=["admins"])
async def handle_admins(message: types.Message):
    await message.answer(ADMIN_TEXT)

@dp.message_handler(commands=["command"])
async def handle_command(message: types.Message):
    await message.answer(COMMANDS_TEXT)

@dp.message_handler(commands=["admin"])
async def handle_admin_panel(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        return
    kb = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton("📨 Последнее сообщение", callback_data="admin_lastmsg"),
        InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast"),
        InlineKeyboardButton("👥 Топ рефералов", callback_data="admin_refstats")
    )
    await message.answer("🔧 Панель администратора:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("admin_"))
async def process_admin_panel_callback(callback_query: types.CallbackQuery):
    data = callback_query.data
    if callback_query.from_user.id not in config.ADMIN_IDS:
        return
    if data == "admin_stats":
        stats = db.get_stats()
        text = (
            f"📊 Статистика:\n"
            f"📈Всего пользователей: {stats['total']}\n"
            f"🔒Заблокировали бота: {stats['blocked']}\n"
            f"🆕Новых за день: {stats['daily']}\n"
            f"🆕Новых за неделю: {stats['weekly']}\n"
            f"🆕Новых за месяц: {stats['monthly']}"
        )
        await callback_query.message.edit_text(text)
    elif data == "admin_lastmsg":
        messages = db.get_last_messages(limit=1)
        if not messages:
            await callback_query.message.edit_text("Последних сообщений от админов пока нет.")
        else:
            msg = messages[0]
            await callback_query.message.edit_text(f"🕒 {msg['time']} (GMT+4):\n{msg['text']}")
    elif data == "admin_broadcast":
        await callback_query.message.edit_text("Для рассылки просто ответьте на нужное сообщение командой /broadcast.")
    elif data == "admin_refstats":
        top_users = db.get_top_referrers(limit=10)
        if not top_users:
            await callback_query.message.edit_text("Реферальная статистика пока пуста.")
        else:
            lines = []
            for i, user in enumerate(top_users, start=1):
                name = user['name'] or f"id:{user['user_id']}"
                count = user['count']
                lines.append(f"{i}. {name} — {count} приглашённых")
            text = "🏆 Топ-10 пользователей по реферальным приглашениям:\n\n" + "\n".join(lines)
            await callback_query.message.edit_text(text)

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

async def main():
    db.init_db()
    asyncio.create_task(monitor())
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())
