"""Supabase Postgres 커넥션과 스키마 초기화.

Types, Config, Providers만 import 가능. 연결은 DATABASE_URL(환경 변수)로.
"""

from __future__ import annotations

import psycopg
from psycopg.rows import dict_row

from app.config.settings import DATABASE_URL

try:  # 커넥션 풀(선택 의존성). 없으면 매 호출 새 커넥션으로 폴백.
    from psycopg_pool import ConnectionPool
except ImportError:  # pragma: no cover
    ConnectionPool = None

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
    agreed_terms  BOOLEAN NOT NULL DEFAULT FALSE,  -- 약관·개인정보 동의 (신규 첫 단계)
    has_seen_tour BOOLEAN NOT NULL DEFAULT FALSE,  -- 첫 로그인 코치마크 투어 시청 여부
    checklist_dismissed BOOLEAN NOT NULL DEFAULT FALSE,  -- 홈 시작 체크리스트 닫음
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

-- 크루 — 동료들과 함께 쓰는 주간 기록 (셋로그식 소그룹)
CREATE TABLE IF NOT EXISTS crews (
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    topic       TEXT,
    invite_code TEXT UNIQUE NOT NULL,
    created_by  BIGINT NOT NULL REFERENCES members(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS crew_members (
    crew_id   BIGINT NOT NULL REFERENCES crews(id),
    member_id BIGINT NOT NULL REFERENCES members(id),
    joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (crew_id, member_id)
);

CREATE TABLE IF NOT EXISTS crew_entries (
    id         BIGSERIAL PRIMARY KEY,
    crew_id    BIGINT NOT NULL REFERENCES crews(id),
    author_id  BIGINT NOT NULL REFERENCES members(id),
    week       TEXT NOT NULL,                 -- ISO 주 (예: 2026-W28)
    body       TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_crew_entries ON crew_entries(crew_id, week);

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


# 커넥션 kwargs — 풀/직접 연결 양쪽에서 동일하게 쓴다.
#   prepare_threshold=None: 준비된 구문(prepared statement)을 끈다. Supabase
#   트랜잭션 풀러(pgbouncer)에서 커넥션이 재사용될 때 'prepared statement already
#   exists' 오류가 나지 않도록 하기 위함.
_CONN_KWARGS = {"row_factory": dict_row, "autocommit": True, "prepare_threshold": None}

_pool = None  # 지연 생성되는 프로세스 단위 커넥션 풀


def _get_pool():
    """프로세스마다 하나의 커넥션 풀을 지연 생성한다.

    서버리스(Vercel)에서 함수 인스턴스가 '따뜻하게' 재사용될 때 매 요청·매 쿼리마다
    새 TCP+TLS+auth 핸드셰이크(≈100~300ms)를 반복하지 않도록, 살아있는 커넥션을
    재사용한다. 한 페이지가 여러 repo 호출로 커넥션을 여러 번 열어도 핸드셰이크
    비용이 사라진다.

    check=check_connection: 인스턴스가 얼었다 깨어나면서 죽은 커넥션이 남아 있어도,
    건네주기 전에 검사·재연결해 간헐적 500(connection closed)을 막는다.
    """
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            DATABASE_URL,
            min_size=1,
            max_size=4,
            max_idle=60,
            kwargs=_CONN_KWARGS,
            check=ConnectionPool.check_connection,
            open=True,
        )
    return _pool


def get_connection():
    """커넥션 컨텍스트 매니저. `with get_connection() as conn:` 형태로 쓴다.

    풀이 있으면 살아있는 커넥션을 빌려주고(반납 시 닫지 않음), 없으면 매번 새로
    연결한다(로컬/테스트 폴백).
    """
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL이 설정되지 않았습니다. Supabase Postgres 연결 문자열을 넣어주세요.")
    if ConnectionPool is not None:
        return _get_pool().connection()
    return psycopg.connect(DATABASE_URL, **_CONN_KWARGS)


# 나중에 추가된 nullable 컬럼들 — 옛 DB에도 안전하게 채워 넣는다(멱등).
_MIGRATIONS = [
    "ALTER TABLE IF EXISTS posts ADD COLUMN IF NOT EXISTS link_url TEXT",
    "ALTER TABLE IF EXISTS posts ADD COLUMN IF NOT EXISTS image_url TEXT",
    "ALTER TABLE IF EXISTS posts ADD COLUMN IF NOT EXISTS video_url TEXT",
    "ALTER TABLE IF EXISTS comments ADD COLUMN IF NOT EXISTS parent_id BIGINT",
    "ALTER TABLE IF EXISTS members ADD COLUMN IF NOT EXISTS topics TEXT[] NOT NULL DEFAULT '{}'",
    "ALTER TABLE IF EXISTS members ADD COLUMN IF NOT EXISTS has_seen_tour BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE IF EXISTS members ADD COLUMN IF NOT EXISTS agreed_terms BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE IF EXISTS members ADD COLUMN IF NOT EXISTS checklist_dismissed BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE IF EXISTS notifications ADD COLUMN IF NOT EXISTS crew_id BIGINT",
]


def init_db() -> None:
    """스키마를 생성하고(없으면), 뒤늦게 추가된 컬럼을 채운다(멱등)."""
    with get_connection() as conn:
        conn.execute(_SCHEMA)
        for stmt in _MIGRATIONS:
            conn.execute(stmt)
