# config.py

import os
from dotenv import load_dotenv

# Загрузка переменных из .env
load_dotenv()

BOT_TOKEN = os.getenv("7956227252:AAHQ_POn0XZDceipwwT1EAbc052tY04tySs")
BOT_USERNAME = os.getenv("Downdetector", "@downdetect0rbot") 
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "602393297,852861796").split(",")]


WELCOME_TEXT = (
    "Добро пожаловать в бота по сбоям Рунета. 🌐\n\n"
    "Вы автоматически подключены к системе мониторинга инцидентов крупных сервисов. "
    "Здесь можно посмотреть статистику, последние сбои, вашу реферальную активность и связаться с администраторами.\n\n"
    "⚠️Главный бот - @nosignalrubot\n"
    "Спасибо, что остаетесь с нами! 👥\n\n"
    "👇Выберите пункт меню ниже:"
)

