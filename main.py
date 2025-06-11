import asyncio
import logging
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.enums import ParseMode, ContentType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from aiogram.utils.markdown import hbold, hcode

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramNotFound
from middlewares import RateLimiterMiddleware
import config
import db

# Инициализация
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
bot = Bot(token=config.BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()
dp.message.middleware(RateLimiterMiddleware())
dp.callback_query.middleware(RateLimiterMiddleware())

# FSM
class EditNameState(StatesGroup):
    WaitingForName = State()

class BroadcastStates(StatesGroup):
    WaitingForMessage = State()
    ConfirmingMessage = State()

# Меню
main_menu = InlineKeyboardMarkup(row_width=1).add(
    InlineKeyboardButton("⚠️Последние сбои", callback_data="menu_last"),
    InlineKeyboardButton("🔗Реферальная ссылка", callback_data="menu_ref"),
    InlineKeyboardButton("🎭 Информация обо мне", callback_data="menu_me"),
    InlineKeyboardButton("👥 Администраторы бота", callback_data="menu_admins"),
    InlineKeyboardButton("🕹️Доступные команды", callback_data="menu_commands")
)

WELCOME_TEXT = (
    "Добро пожаловать в бота по сбоям Рунета. 🌐\n\n"
    "Вы автоматически подключены к системе мониторинга инцидентов крупных сервисов."
    " Здесь можно посмотреть статистику, последние сбои, вашу реферальную активность и связаться с администраторами.\n\n"
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
ADMIN_TEXT = "👤Администраторы данного бота:\n🤴@internetmodel - владелец\n🧑‍💻@overnightwatch - кодер"
ADMIN_LOG_ID = config.ADMIN_IDS[0]

router = Router()

@router.message(F.text.startswith("/start"))
async def handle_start(message: Message):
    ref_id = int(message.text.split(maxsplit=1)[-1]) if len(message.text.split()) > 1 and message.text.split()[1].isdigit() else None
    user_id = message.from_user.id
    user = db.get_user(user_id)
    if user:
        await message.answer(WELCOME_TEXT, reply_markup=main_menu)
        return

    full_name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip()
    db.add_user(user_id, name=full_name, referral_id=ref_id)
    await message.answer(WELCOME_TEXT, reply_markup=main_menu)

    if ref_id and ref_id != user_id:
        await bot.send_message(ADMIN_LOG_ID, f"👤 Новый пользователь: {full_name} зарегистрировался по рефералке от ID {ref_id}")

@router.message(F.text == "/ref")
async def ref_link(message: Message):
    user_id = message.from_user.id
    link = f"https://t.me/{config.BOT_USERNAME}?start={user_id}"
    await message.answer(f"🔗 Ваша реферальная ссылка:\n{link}")

@router.callback_query(F.data == "menu_main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(WELCOME_TEXT, reply_markup=main_menu)

@router.callback_query(F.data == "menu_last")
async def menu_last(callback: CallbackQuery):
    await callback.message.delete()
    messages = db.get_last_messages(limit=5)
    now = datetime.now(ZoneInfo("Europe/Moscow"))
    updated_time = now.strftime("%Y-%m-%d %H:%M")
    if not messages:
        text = f"За сегодня не зафиксировано сбоев.\nОбновлено: {updated_time} (GMT+3)"
    else:
        text = "📰 Последние сообщения от админов:\n\n" + "\n\n".join(
            f"🕒 {msg['time']} (GMT+3):\n{msg['text']}" for msg in messages
        )
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Назад", callback_data="menu_main"))
    await callback.message.answer(text, reply_markup=kb)

@router.callback_query(F.data == "menu_admins")
async def menu_admins(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(ADMIN_TEXT, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Назад", callback_data="menu_main")))

@router.callback_query(F.data == "menu_commands")
async def menu_commands(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(COMMANDS_TEXT, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Назад", callback_data="menu_main")))

@router.message(F.text == "/me")
async def user_info(message: Message):
    await send_user_info(message.from_user.id, message)

@router.callback_query(F.data == "menu_me")
async def menu_me(callback: CallbackQuery):
    await callback.message.delete()
    await send_user_info(callback.from_user.id, callback)

async def send_user_info(user_id, msg_or_cb):
    user = db.get_user(user_id)
    if not user:
        await msg_or_cb.answer("Информация не найдена.")
        return

    ref_count = db.get_referral_count(user_id)
    text = (
        f"👤 <b>Информация о пользователе</b>\n"
        f"Имя: {user['name']}\n"
        f"Юзернейм: @{msg_or_cb.from_user.username or 'нет'}\n"
        f"ID: <code>{user['user_id']}</code>\n"
        f"Дата входа: {user['joined_at']}\n"
        f"👥 Приглашено пользователей: {ref_count}"
    )
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("✏️ Отредактировать имя", callback_data="edit_name"),
        InlineKeyboardButton("⬅️ Назад", callback_data="menu_main")
    )
    await bot.send_message(user_id, text, reply_markup=kb)

@router.callback_query(F.data == "edit_name")
async def edit_name(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("✏️ Напишите свое новое имя:")
    await state.set_state(EditNameState.WaitingForName)

@router.message(EditNameState.WaitingForName, F.content_type == ContentType.TEXT)
async def receive_new_name(message: Message, state: FSMContext):
    new_name = message.text.strip()
    if len(new_name) > 50:
        await message.answer("Имя слишком длинное. Попробуйте покороче.")
        return
    db.update_user_name(message.from_user.id, new_name)
    await message.answer(f"✅ Имя обновлено на: {new_name}")
    await state.clear()
    await send_user_info(message.from_user.id, message)

@router.message(F.text == "/broadcast")
async def cmd_broadcast(message: Message, state: FSMContext):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.reply("⚠️ Эта команда только для администраторов.")
        return
    await message.answer("✉️ Отправьте ваше сообщение (можно с медиа и кнопками):")
    await state.set_state(BroadcastStates.WaitingForMessage)

@router.message(BroadcastStates.WaitingForMessage)
async def receive_broadcast_message(message: Message, state: FSMContext):
    await state.update_data(message=message)
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("✅ Отправить сообщение", callback_data="broadcast_send"),
        InlineKeyboardButton("✒️ Отредактировать сообщение", callback_data="broadcast_edit")
    )
    await message.answer("<b>Предпросмотр подготовлен.</b>\n\nВы хотите отправить сообщение или изменить?", reply_markup=kb)
    await state.set_state(BroadcastStates.ConfirmingMessage)

@router.callback_query(F.data == "broadcast_edit", BroadcastStates.ConfirmingMessage)
async def edit_broadcast(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("✏️👇 Отредактируйте сообщение:")
    await state.set_state(BroadcastStates.WaitingForMessage)

@router.callback_query(F.data == "broadcast_send", BroadcastStates.ConfirmingMessage)
async def send_broadcast(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    src_msg: Message = data["message"]
    success, blocked = 0, 0
    for user in db.get_all_users():
        try:
            if src_msg.photo:
                await bot.send_photo(user["user_id"], src_msg.photo[-1].file_id, caption=src_msg.caption or src_msg.text or "")
            elif src_msg.document:
                await bot.send_document(user["user_id"], src_msg.document.file_id, caption=src_msg.caption or src_msg.text or "")
            elif src_msg.video:
                await bot.send_video(user["user_id"], src_msg.video.file_id, caption=src_msg.caption or src_msg.text or "")
            else:
                await bot.send_message(user["user_id"], src_msg.text or "")
            success += 1
        except TelegramForbiddenError:
            blocked += 1
            db.block_user(user["user_id"])
        except Exception as e:
            logger.error(f"Ошибка при рассылке {user['user_id']}: {e}")

    await callback.message.edit_text(f"✅Сообщение отправлено!\n✔️ Доставлено: {success}\n❌ Заблокировали бота: {blocked}")
    await state.clear()

async def main():
    db.init_db()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())




