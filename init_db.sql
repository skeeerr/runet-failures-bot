
-- Скрипт инициализации базы данных
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS messages;

CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    referral_id INTEGER,
    joined_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    time TEXT DEFAULT CURRENT_TIMESTAMP,
    text TEXT NOT NULL
);
