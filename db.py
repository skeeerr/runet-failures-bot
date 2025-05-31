import sqlite3
from datetime import datetime, timedelta

# Подключение к базе данных SQLite
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

# Создание таблицы пользователей
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    joined_at TEXT,
    referral_id INTEGER,
    is_blocked INTEGER DEFAULT 0
)
""")

# Создание таблицы сообщений от админов
cursor.execute("""
CREATE TABLE IF NOT EXISTS broadcasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()

# Добавление нового пользователя
def add_user(user_id, referral_id=None):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if cursor.fetchone() is None:
        now = datetime.utcnow().isoformat()
        cursor.execute("INSERT INTO users (user_id, joined_at, referral_id) VALUES (?, ?, ?)",
                       (user_id, now, referral_id))
        conn.commit()

# Получение статистики пользователей
def get_stats():
    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE is_blocked=1")
    blocked = cursor.fetchone()[0]

    def count_since(days):
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        cursor.execute("SELECT COUNT(*) FROM users WHERE joined_at >= ?", (since,))
        return cursor.fetchone()[0]

    return {
        "total": total,
        "blocked": blocked,
        "daily": count_since(1),
        "weekly": count_since(7),
        "monthly": count_since(30)
    }

# Получение всех активных пользователей
def get_active_users():
    cursor.execute("SELECT user_id FROM users WHERE is_blocked=0")
    return [row[0] for row in cursor.fetchall()]

# Пометить пользователя как заблокировавшего бота
def block_user(user_id):
    cursor.execute("UPDATE users SET is_blocked=1 WHERE user_id=?", (user_id,))
    conn.commit()

# Сохранение сообщения от админа
def save_last_message(message: str, timestamp: str = None):
    if not timestamp:
        timestamp = datetime.utcnow().isoformat()
    cursor.execute("INSERT INTO broadcasts (text, created_at) VALUES (?, ?)", (message, timestamp))
    conn.commit()

# Получение последних сообщений от админов (по умолчанию 5)
def get_last_messages(limit=5):
    cursor.execute("SELECT text, created_at FROM broadcasts ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    result = []
    for text, created_at in rows:
        # Преобразуем в часовой пояс UTC+4
        dt = datetime.fromisoformat(created_at) + timedelta(hours=4)
        formatted_time = dt.strftime("%Y-%m-%d %H:%M")
        result.append({"text": text, "time": formatted_time})
    return result

