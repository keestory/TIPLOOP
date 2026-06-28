"""Supabase Postgres 커넥션과 스키마 초기화.

Types, Config, Providers만 import 가능. 연결은 DATABASE_URL(환경 변수)로.
"""

from __future__ import annotations

import psycopg
from psycopg.rows import dict_row

from app.config.settings import DATABASE_URL

_SCHEMA = """
CREATE TABLE IF NOT EXISTS teachers (
    id             BIGSERIAL PRIMARY KEY,
    auth_id        TEXT UNIQUE NOT NULL,          -- Supabase auth 사용자 id(uuid)
    email          TEXT,
    name           TEXT NOT NULL,
    avatar_url     TEXT,
    provider       TEXT,                          -- google | kakao
    phone          TEXT,
    phone_verified BOOLEAN NOT NULL DEFAULT FALSE,
    school_level   TEXT,                          -- 온보딩 전엔 NULL
    region         TEXT,
    subject        TEXT NOT NULL DEFAULT '',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS posts (
    id         BIGSERIAL PRIMARY KEY,
    author_id  BIGINT NOT NULL REFERENCES teachers(id),
    category   TEXT NOT NULL,
    title      TEXT NOT NULL,
    body       TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    event_at   TEXT,
    location   TEXT,
    online_url TEXT
);

CREATE TABLE IF NOT EXISTS comments (
    id         BIGSERIAL PRIMARY KEY,
    post_id    BIGINT NOT NULL REFERENCES posts(id),
    author_id  BIGINT NOT NULL REFERENCES teachers(id),
    body       TEXT NOT NULL,
    parent_id  BIGINT REFERENCES comments(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS post_reactions (
    post_id BIGINT NOT NULL REFERENCES posts(id),
    user_id BIGINT NOT NULL REFERENCES teachers(id),
    PRIMARY KEY (post_id, user_id)
);

CREATE TABLE IF NOT EXISTS comment_reactions (
    comment_id BIGINT NOT NULL REFERENCES comments(id),
    user_id    BIGINT NOT NULL REFERENCES teachers(id),
    PRIMARY KEY (comment_id, user_id)
);
"""


def get_connection() -> psycopg.Connection:
    """요청마다 새 커넥션. dict_row로 컬럼명 접근."""
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL이 설정되지 않았습니다. Supabase Postgres 연결 문자열을 넣어주세요.")
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, autocommit=True)


def init_db() -> None:
    """스키마를 생성한다(이미 있으면 건너뜀)."""
    with get_connection() as conn:
        conn.execute(_SCHEMA)
