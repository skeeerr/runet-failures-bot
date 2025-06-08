import asyncio
import logging
import subprocess
import os
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.exceptions import BotBlocked
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Command
from aiogram.utils.exceptions import BotBlocked
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

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
    "/admin - панель администратора (для админов)\n"
    "/me - предоставляет информацию о себе"
)

ADMIN_TEXT = (
    "👤Администраторы данного бота:\n"
    "🤴@internetmodel - владелец\n"
    "🧑‍💻@overnightwatch - кодер"
)

ADMIN_LOG_ID = config.ADMIN_IDS[0]

class EditNameState(StatesGroup):
    WaitingForName = State()

main_menu = InlineKeyboardMarkup(row_width=1).add(
    InlineKeyboardButton("🛠️Сервисы", callback_data="menu_services"),
    InlineKeyboardButton("⚠️Последние сбои", callback_data="menu_last"),
    InlineKeyboardButton("🔗Реферальная ссылка", callback_data="menu_ref"),
    InlineKeyboardButton("🎭 Информация обо мне", callback_data="menu_me"),
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

    try:
        result = subprocess.run(["node", "./make_graph.js", name], capture_output=True, text=True, timeout=15)
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

@dp.message_handler(commands=["me"])
async def user_info(message: types.Message):
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("Информация не найдена.")
        return

    ref_count = db.get_referral_count(message.from_user.id)
    text = (
        f"👤 <b>Информация о пользователе</b>\n"
        f"Имя: {user['name']}\n"
        f"Юзернейм: @{message.from_user.username if message.from_user.username else 'нет'}\n"
        f"ID: <code>{user['user_id']}</code>\n"
        f"Дата входа: {user['joined_at']}\n"
        f"👥 Приглашено пользователей: {ref_count}"
    )
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("⬅️ Назад", callback_data="menu_main"),
        InlineKeyboardButton("🔚 Главное меню", callback_data="menu_main")
    )
    await message.answer(text, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "menu_me")
async def menu_me(callback: types.CallbackQuery):
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.message.answer("Информация не найдена.")
        return

    ref_count = db.get_referral_count(callback.from_user.id)
    text = (
        f"👤 <b>Информация о пользователе</b>\n"
        f"Имя: {user['name']}\n"
        f"Юзернейм: @{callback.from_user.username if callback.from_user.username else 'нет'}\n"
        f"ID: <code>{user['user_id']}</code>\n"
        f"Дата входа: {user['joined_at']}\n"
        f"👥 Приглашено пользователей: {ref_count}"
    )
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("✏️ Отредактировать имя", callback_data="edit_name"),
        InlineKeyboardButton("⬅️ Назад", callback_data="menu_main"),
        InlineKeyboardButton("🔚 Главное меню", callback_data="menu_main")
    )
    await callback.message.delete()
    await bot.send_message(callback.from_user.id, text, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "edit_name")
async def edit_name(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("✏️ Напишите свое новое имя:")
    await EditNameState.WaitingForName.set()

@dp.message_handler(state=EditNameState.WaitingForName, content_types=types.ContentTypes.TEXT)
async def receive_new_name(message: types.Message, state: FSMContext):
    new_name = message.text.strip()
    db.update_user_name(message.from_user.id, new_name)
    await message.answer(f"✅ Имя обновлено на: {new_name}")
    await state.finish()
    await menu_me(types.CallbackQuery(message=message, from_user=message.from_user, data="menu_me"))



# Состояния FSM
class BroadcastStates(StatesGroup):
    WaitingForMessage = State()
    ConfirmingMessage = State()

# Команда запуска рассылки
@dp.message_handler(commands=["broadcast"])
async def cmd_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.reply("⚠️ Эта команда только для администраторов.")
        return
    await message.answer("✉️ Отправьте ваше сообщение:")
    await BroadcastStates.WaitingForMessage.set()

# Получение текста от администратора
@dp.message_handler(state=BroadcastStates.WaitingForMessage, content_types=types.ContentTypes.TEXT)
async def receive_broadcast_text(message: types.Message, state: FSMContext):
    await state.update_data(text=message.text)
    kb = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("✅ Отправить сообщение", callback_data="broadcast_send"),
        InlineKeyboardButton("✒️ Отредактировать сообщение", callback_data="broadcast_edit")
    )
    await message.answer(
        f"<b>Предпросмотр сообщения:</b>\n\n{message.text}\n\n"
        "Вы хотите отправить данное сообщение пользователям или хотите что-то дополнить?",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await BroadcastStates.ConfirmingMessage.set()

# Обработка запроса на редактирование
@dp.callback_query_handler(lambda c: c.data == "broadcast_edit", state=BroadcastStates.ConfirmingMessage)
async def edit_broadcast(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("✏️👇 Отредактируй сообщение, которое ты хочешь отправить:")
    await BroadcastStates.WaitingForMessage.set()

# Отправка рассылки
@dp.callback_query_handler(lambda c: c.data == "broadcast_send", state=BroadcastStates.ConfirmingMessage)
async def send_broadcast(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text = data.get("text")
    success = 0
    blocked = 0
    users = db.get_all_users()

    for user in users:
        try:
            await bot.send_message(user["user_id"], text)
            success += 1
        except BotBlocked:
            blocked += 1
            db.block_user(user["user_id"])
        except Exception as e:
            logging.warning(f"Ошибка при отправке {user['user_id']}: {e}")

    await callback.message.edit_text(
        f"✅Сообщение успешно отправлено!\n"
        f"✔️Доставлено: {success}\n"
        f"❌Заблокировали бота: {blocked}\n\n"
        f"🛜@nosignalrubot"
    )

    admin_name = callback.from_user.username
    full_name = f"{callback.from_user.first_name or ''} {callback.from_user.last_name or ''}".strip()
    admin_tag = f"@{admin_name} ({full_name})" if admin_name else f"{full_name}"
    await bot.send_message(
        config.ADMIN_IDS[0],
        f"📬 Рассылка завершена админом {admin_tag}\n"
        f"✔️ Доставлено: {success}\n"
        f"❌ Заблокировали бота: {blocked}"
    )
    await state.finish()
# Запуск
async def main():
    db.init_db()
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())



