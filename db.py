import sqlite3
from datetime import datetime

DB_PATH = "database.sqlite3"

def init_db():
    with open("init_db.sql", "r", encoding="utf-8") as f:
        sql = f.read()
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(sql)

def add_user(user_id, name=None, referral_id=None):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO users (user_id, name, referral_id, is_blocked)
            VALUES (?, ?, ?, 0)
            """,
            (user_id, name, referral_id),
        )

def get_user(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT user_id, name, joined_at FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row:
            return {"user_id": row[0], "name": row[1], "joined_at": row[2]}
        return None

def get_all_users():
    with sqlite3.connect(DB_PATH) as conn:
        return [
            {"user_id": row[0]}
            for row in conn.execute("SELECT user_id FROM users WHERE is_blocked = 0").fetchall()
        ]

def block_user(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET is_blocked = 1 WHERE user_id = ?", (user_id,))

def get_referral_count(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM users WHERE referral_id = ?", (user_id,)
        ).fetchone()[0]

def get_referral_ranking(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT referral_id, COUNT(*) as count FROM users WHERE referral_id IS NOT NULL GROUP BY referral_id ORDER BY count DESC"
        ).fetchall()
        for i, row in enumerate(rows):
            if row[0] == user_id:
                return i + 1
    return "—"

def get_top_referrers(limit=10):
    with sqlite3.connect(DB_PATH) as conn:
        return [
            {"user_id": row[0], "count": row[1], "name": get_user_name(row[0])}
            for row in conn.execute(
                "SELECT referral_id, COUNT(*) FROM users WHERE referral_id IS NOT NULL GROUP BY referral_id ORDER BY COUNT(*) DESC LIMIT ?",
                (limit,),
            ).fetchall()
        ]

def get_user_name(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT name FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        return row[0] if row else None

def get_last_messages(limit=5):
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT time, text FROM messages ORDER BY time DESC LIMIT ?", (limit,)
        ).fetchall()
        return [{"time": row[0], "text": row[1]} for row in rows]

def update_user_name(user_id, new_name):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE users SET name = ? WHERE user_id = ?",
            (new_name, user_id)
        )
