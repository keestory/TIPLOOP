"""Supabase Postgres 커넥션과 스키마 초기화.

Types, Config, Providers만 import 가능. 연결은 DATABASE_URL(환경 변수)로.
"""

from __future__ import annotations

import psycopg
from psycopg.rows import dict_row

from app.config.settings import DATABASE_URL

_SCHEMA = """
CREATE TABLE IF NOT EXISTS members (
    id         BIGSERIAL PRIMARY KEY,
    auth_id    TEXT UNIQUE NOT NULL,          -- Supabase auth 사용자 id(uuid)
    email      TEXT,
    name       TEXT NOT NULL,
    avatar_url TEXT,
    provider   TEXT,                          -- google | kakao
    job_role   TEXT,                          -- 직군 (온보딩 전엔 NULL)
    years      TEXT,                          -- 연차
    industry   TEXT,                          -- 업종
    topics     TEXT[] NOT NULL DEFAULT '{}',  -- 관심 주제 (온보딩 2단계)
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS posts (
    id         BIGSERIAL PRIMARY KEY,
    author_id  BIGINT NOT NULL REFERENCES members(id),
    category   TEXT NOT NULL,
    title      TEXT NOT NULL,
    body       TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    link_url   TEXT,                          -- 레퍼런스 참고 링크 (선택)
    image_url  TEXT,                          -- 주석 이미지 (Supabase Storage URL, 선택)
    video_url  TEXT                           -- 첨부 영상 (Supabase Storage URL, 선택)
);

-- 영상 위 특정 시각+위치에 달리는 코멘트 (Frame.io식)
CREATE TABLE IF NOT EXISTS media_comments (
    id         BIGSERIAL PRIMARY KEY,
    post_id    BIGINT NOT NULL REFERENCES posts(id),
    author_id  BIGINT NOT NULL REFERENCES members(id),
    t_seconds  DOUBLE PRECISION NOT NULL,     -- 영상 재생 시각(초)
    x          DOUBLE PRECISION NOT NULL,     -- 화면 가로 위치 0~1
    y          DOUBLE PRECISION NOT NULL,     -- 화면 세로 위치 0~1
    body       TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS comments (
    id         BIGSERIAL PRIMARY KEY,
    post_id    BIGINT NOT NULL REFERENCES posts(id),
    author_id  BIGINT NOT NULL REFERENCES members(id),
    body       TEXT NOT NULL,
    parent_id  BIGINT REFERENCES comments(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS post_reactions (
    post_id BIGINT NOT NULL REFERENCES posts(id),
    user_id BIGINT NOT NULL REFERENCES members(id),
    PRIMARY KEY (post_id, user_id)
);

CREATE TABLE IF NOT EXISTS comment_reactions (
    comment_id BIGINT NOT NULL REFERENCES comments(id),
    user_id    BIGINT NOT NULL REFERENCES members(id),
    PRIMARY KEY (comment_id, user_id)
);

-- "도움됐어요" — 공감(♥)과 분리된 자기효능감 신호
CREATE TABLE IF NOT EXISTS post_helpful (
    post_id BIGINT NOT NULL REFERENCES posts(id),
    user_id BIGINT NOT NULL REFERENCES members(id),
    PRIMARY KEY (post_id, user_id)
);

-- 적용 후기 — 실제로 써보고 남기는 결과/후기 (강한 임팩트 신호)
CREATE TABLE IF NOT EXISTS reviews (
    id         BIGSERIAL PRIMARY KEY,
    post_id    BIGINT NOT NULL REFERENCES posts(id),
    author_id  BIGINT NOT NULL REFERENCES members(id),
    body       TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 팔로우 (단방향)
CREATE TABLE IF NOT EXISTS follows (
    follower_id BIGINT NOT NULL REFERENCES members(id),
    followee_id BIGINT NOT NULL REFERENCES members(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (follower_id, followee_id)
);

-- 활동 알림 (내 글 반응 · 팔로우 · 구독 주제의 새 글)
CREATE TABLE IF NOT EXISTS notifications (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL REFERENCES members(id),   -- 받는 사람
    actor_id   BIGINT REFERENCES members(id),            -- 행동한 사람
    kind       TEXT NOT NULL,                            -- review|helpful|comment|follow|topic_post
    post_id    BIGINT REFERENCES posts(id),
    topic      TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    read_at    TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, created_at DESC);
"""


def get_connection() -> psycopg.Connection:
    """요청마다 새 커넥션. dict_row로 컬럼명 접근.

    prepare_threshold=None: 준비된 구문(prepared statement)을 끈다.
    Supabase 트랜잭션 풀러(pgbouncer)·서버리스 환경에서 커넥션이 재사용될 때
    'prepared statement already exists' 오류가 나지 않도록 하기 위함.
    """
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL이 설정되지 않았습니다. Supabase Postgres 연결 문자열을 넣어주세요.")
    return psycopg.connect(
        DATABASE_URL, row_factory=dict_row, autocommit=True, prepare_threshold=None
    )


# 나중에 추가된 nullable 컬럼들 — 옛 DB에도 안전하게 채워 넣는다(멱등).
_MIGRATIONS = [
    "ALTER TABLE IF EXISTS posts ADD COLUMN IF NOT EXISTS link_url TEXT",
    "ALTER TABLE IF EXISTS posts ADD COLUMN IF NOT EXISTS image_url TEXT",
    "ALTER TABLE IF EXISTS posts ADD COLUMN IF NOT EXISTS video_url TEXT",
    "ALTER TABLE IF EXISTS comments ADD COLUMN IF NOT EXISTS parent_id BIGINT",
    "ALTER TABLE IF EXISTS members ADD COLUMN IF NOT EXISTS topics TEXT[] NOT NULL DEFAULT '{}'",
]


def init_db() -> None:
    """스키마를 생성하고(없으면), 뒤늦게 추가된 컬럼을 채운다(멱등)."""
    with get_connection() as conn:
        conn.execute(_SCHEMA)
        for stmt in _MIGRATIONS:
            conn.execute(stmt)
