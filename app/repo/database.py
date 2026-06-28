"""SQLite 커넥션과 스키마 초기화.

Types, Config, Providers만 import 가능.
"""

import sqlite3

from app.config.settings import DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name          TEXT NOT NULL,
    school_level  TEXT NOT NULL,
    region        TEXT NOT NULL,
    subject       TEXT NOT NULL DEFAULT '',
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    token      TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS posts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    author_id  INTEGER NOT NULL REFERENCES users(id),
    category   TEXT NOT NULL,
    title      TEXT NOT NULL,
    body       TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    event_at   TEXT,
    location   TEXT,
    online_url TEXT
);

CREATE TABLE IF NOT EXISTS comments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id    INTEGER NOT NULL REFERENCES posts(id),
    author_id  INTEGER NOT NULL REFERENCES users(id),
    body       TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def get_connection() -> sqlite3.Connection:
    """요청마다 새 커넥션을 연다. row_factory로 dict-유사 접근."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """스키마를 생성한다(이미 있으면 건너뜀)."""
    conn = get_connection()
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()
