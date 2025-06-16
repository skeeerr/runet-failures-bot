import os
from dotenv import load_dotenv

load_dotenv()

try:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не найден в .env файле")
        
    BOT_USERNAME = os.getenv("BOT_USERNAME", "@downdetect0rbot")
    ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
    
except Exception as e:
    print(f"Ошибка загрузки конфигурации: {e}")
    raise

WELCOME_TEXT = (
    "Добро пожаловать в бота по сбоям Рунета. 🌐\n\n"
    "Вы автоматически подключены к системе мониторинга инцидентов крупных сервисов. "
    "Здесь можно посмотреть статистику, последние сбои, вашу реферальную активность и связаться с администраторами.\n\n"
    "⚠️Главный бот - @nosignalrubot\n"
    "Спасибо, что остаетесь с нами! 👥\n\n"
    "👇Выберите пункт меню ниже:"
)

