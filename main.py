import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.enums import ParseMode, ContentType
from aiogram.exceptions import TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    Message,
)
from middlewares import RateLimiterMiddleware
import config
import db

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Бот и диспетчер
bot = Bot(token=config.BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()
dp.message.middleware(RateLimiterMiddleware())
dp.callback_query.middleware(RateLimiterMiddleware())

router = Router()

# Состояния
class EditNameState(StatesGroup):
    WaitingForName = State()

class BroadcastStates(StatesGroup):
    WaitingForMessage = State()
    ConfirmingMessage = State()

# Главное меню
main_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⚠️Последние сбои", callback_data="menu_last")],
    [InlineKeyboardButton(text="🔗Реферальная ссылка", callback_data="menu_ref")],
    [InlineKeyboardButton(text="🎭 Информация обо мне", callback_data="menu_me")],
    [InlineKeyboardButton(text="👥 Администраторы бота", callback_data="menu_admins")],
    [InlineKeyboardButton(text="🕹️Доступные команды", callback_data="menu_commands")],
])

WELCOME_TEXT = (
    "Добро пожаловать в бота по сбоям Рунета. 🌐\n\n"
    "Вы автоматически подключены к системе мониторинга инцидентов крупных сервисов.\n"
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

# Старт
@router.message(F.text.startswith("/start"))
async def handle_start(message: Message):
    args = message.text.split()
    ref_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    user_id = message.from_user.id

    if db.get_user(user_id):
        await message.answer(WELCOME_TEXT, reply_markup=main_menu)
        return

    full_name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip()
    db.add_user(user_id, name=full_name, referral_id=ref_id)
    await message.answer(WELCOME_TEXT, reply_markup=main_menu)

    if ref_id and ref_id != user_id:
        await bot.send_message(
            ADMIN_LOG_ID,
            f"👤 Новый пользователь: {full_name} зарегистрировался по рефералке от ID {ref_id}"
        )

# Реферальная ссылка
@router.message(F.text == "/ref")
async def ref_link(message: Message):
    user_id = message.from_user.id
    link = f"https://t.me/{config.BOT_USERNAME}?start={user_id}"
    await message.answer(f"🔗 Ваша реферальная ссылка:\n{link}")

# Топ по рефералам
@router.message(F.text == "/refstats")
async def ref_stats(message: Message):
    top = db.get_top_referrers()
    if not top:
        await message.answer("👥 Пока никто не пригласил других пользователей.")
        return

    text = "👥 <b>Топ 10 рефералов:</b>\n"
    for i, row in enumerate(top, 1):
        name = row['name'] or f"ID {row['user_id']}"
        text += f"{i}. {name} - {row['count']}\n"
    await message.answer(text)

# Панель администратора
@router.message(F.text == "/admin")
async def admin_panel(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("❌ У вас нет доступа к панели администратора.")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📬 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="📈 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🧾 Лог ошибок", callback_data="admin_logs")],
    ])
    await message.answer("🔧 Панель администратора:", reply_markup=kb)

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery, state: FSMContext):
    await cmd_broadcast(callback.message, state)

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    count = len(db.get_all_users())
    await callback.message.answer(f"📊 Зарегистрированных пользователей: <b>{count}</b>")

@router.callback_query(F.data == "admin_logs")
async def admin_logs(callback: CallbackQuery):
    try:
        with open("bot.log", "r", encoding="utf-8") as f:
            last_lines = f.readlines()[-20:]
        text = "<b>🧾 Последние строки из лога:</b>\n\n" + "".join(last_lines)
        await callback.message.answer(f"<code>{text}</code>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await callback.message.answer(f"⚠️ Не удалось загрузить лог: {e}")
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

from middlewares import RateLimiterMiddleware

