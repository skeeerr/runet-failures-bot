import sqlite3
from datetime import datetime

conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

def init_db():
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            referral_id INTEGER,
            joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
            blocked INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT,
            time TEXT
        )
    """)
    conn.commit()

def add_user(user_id, name=None, referral_id=None):
    cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone():
        return
    cursor.execute(
        "INSERT INTO users (user_id, name, referral_id) VALUES (?, ?, ?)",
        (user_id, name, referral_id)
    )
    conn.commit()

def block_user(user_id):
    cursor.execute("UPDATE users SET blocked = 1 WHERE user_id = ?", (user_id,))
    conn.commit()

def get_active_users():
    cursor.execute("SELECT user_id FROM users WHERE blocked = 0")
    return [row[0] for row in cursor.fetchall()]

def get_stats():
    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE blocked = 1")
    blocked = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE date(joined_at) = date('now')")
    daily = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE joined_at >= datetime('now', '-7 days')")
    weekly = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE joined_at >= datetime('now', '-30 days')")
    monthly = cursor.fetchone()[0]

    return {
        "total": total,
        "blocked": blocked,
        "daily": daily,
        "weekly": weekly,
        "monthly": monthly,
    }

def get_last_messages(limit=5):
    cursor.execute("SELECT time, text FROM messages ORDER BY id DESC LIMIT ?", (limit,))
    return [{"time": row[0], "text": row[1]} for row in cursor.fetchall()]

def save_last_message(text):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    cursor.execute("INSERT INTO messages (time, text) VALUES (?, ?)", (now, text))
    conn.commit()

def clear_old_messages():
    cursor.execute("DELETE FROM messages")
    conn.commit()

def get_referral_count(user_id):
    cursor.execute("SELECT COUNT(*) FROM users WHERE referral_id = ?", (user_id,))
    return cursor.fetchone()[0]

def get_referral_ranking(user_id):
    cursor.execute("""
        SELECT referral_id, COUNT(*) as count FROM users
        WHERE referral_id IS NOT NULL
        GROUP BY referral_id
        ORDER BY count DESC
    """)
    rankings = cursor.fetchall()
    for i, (ref_id, _) in enumerate(rankings, start=1):
        if ref_id == user_id:
            return i
    return "—"

def get_top_referrers(limit=10):
    cursor.execute("""
        SELECT referral_id as user_id, COUNT(*) as count
        FROM users
        WHERE referral_id IS NOT NULL
        GROUP BY referral_id
        ORDER BY count DESC
        LIMIT ?
    """, (limit,))
    top = cursor.fetchall()

    result = []
    for user_id, count in top:
        cursor.execute("SELECT name FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        result.append({
            "user_id": user_id,
            "name": row[0] if row else None,
            "count": count
        })
    return result
