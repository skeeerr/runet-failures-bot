import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    joined_at TEXT,
    referral_id INTEGER,
    is_blocked INTEGER DEFAULT 0
)
""")
conn.commit()

def add_user(user_id, referral_id=None):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if cursor.fetchone() is None:
        now = datetime.utcnow().isoformat()
        cursor.execute("INSERT INTO users (user_id, joined_at, referral_id) VALUES (?, ?, ?)",
                       (user_id, now, referral_id))
        conn.commit()

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

def get_active_users():
    cursor.execute("SELECT user_id FROM users WHERE is_blocked=0")
    return [row[0] for row in cursor.fetchall()]

def block_user(user_id):
    cursor.execute("UPDATE users SET is_blocked=1 WHERE user_id=?", (user_id,))
    conn.commit()

def save_last_message(message: str, timestamp: str):
    pass

def get_last_messages(limit=5):
    pass
