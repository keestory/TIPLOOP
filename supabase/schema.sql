-- 티핑(Tipping) Supabase 스키마
-- Supabase 대시보드 → SQL Editor에 붙여넣고 실행하세요.
-- (앱을 DATABASE_URL로 처음 켜면 자동 생성되기도 합니다)

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
    has_seen_tour BOOLEAN NOT NULL DEFAULT FALSE,  -- 첫 로그인 코치마크 투어 시청 여부
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
    user_id    BIGINT NOT NULL REFERENCES members(id),
    actor_id   BIGINT REFERENCES members(id),
    kind       TEXT NOT NULL,   -- review|helpful|comment|reply|follow|topic_post
    post_id    BIGINT REFERENCES posts(id),
    topic      TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    read_at    TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, created_at DESC);
