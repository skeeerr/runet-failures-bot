import sqlite3
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
DB_PATH = "database.sqlite3"

class DBError(Exception):
    pass

def init_db():
    try:
        with open("init_db.sql", "r", encoding="utf-8") as f:
            sql = f.read()
        with sqlite3.connect(DB_PATH) as conn:
            conn.executescript(sql)
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}")
        raise DBError("Не удалось инициализировать базу данных")

def add_user(user_id, name=None, referral_id=None):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO users (user_id, name, referral_id, is_blocked)
                VALUES (?, ?, ?, 0)
                """,
                (user_id, name, referral_id),
            )
    except Exception as e:
        logger.error(f"Ошибка добавления пользователя {user_id}: {e}")
        raise DBError("Не удалось добавить пользователя")

# Аналогично для остальных функций добавляем обработку ошибок
# ...

def get_last_messages(limit=5):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                "SELECT time, text FROM messages ORDER BY time DESC LIMIT ?", (limit,)
            ).fetchall()
            return [{"time": row[0], "text": row[1]} for row in rows]
    except Exception as e:
        logger.error(f"Ошибка получения сообщений: {e}")
        raise DBError("Не удалось получить сообщения")
