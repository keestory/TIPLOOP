-- 이음(Ieum) Supabase 스키마
-- Supabase 대시보드 → SQL Editor에 붙여넣고 실행하세요.
-- (앱을 DATABASE_URL로 처음 켜면 자동 생성되기도 합니다)

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
