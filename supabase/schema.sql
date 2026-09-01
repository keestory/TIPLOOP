-- TIPLOOP Supabase 스키마
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

-- 활동 알림 (내 글 반응 · 팔로우 · 구독 주제의 새 글 · 크루)
CREATE TABLE IF NOT EXISTS notifications (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL REFERENCES members(id),
    actor_id   BIGINT REFERENCES members(id),
    kind       TEXT NOT NULL,   -- review|helpful|comment|reply|follow|topic_post|crew
    post_id    BIGINT REFERENCES posts(id),
    topic      TEXT,
    crew_id    BIGINT REFERENCES crews(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    read_at    TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, created_at DESC);

-- 앱 데이터는 FastAPI 서버의 DATABASE_URL 연결로만 접근한다.
-- Data API에 public 스키마가 노출되더라도 anon/authenticated 직접 조회는 기본 거부한다.
ALTER TABLE members ENABLE ROW LEVEL SECURITY;
ALTER TABLE posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE media_comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE post_reactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE comment_reactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE post_helpful ENABLE ROW LEVEL SECURITY;
ALTER TABLE reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE follows ENABLE ROW LEVEL SECURITY;
ALTER TABLE crews ENABLE ROW LEVEL SECURITY;
ALTER TABLE crew_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE crew_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- 앱 데이터는 서버의 Postgres 연결로만 읽고 쓴다. RLS와 별개로 브라우저
-- Data API 역할의 테이블·시퀀스 권한을 회수해 방어 계층을 하나 더 둔다.
DO $$
DECLARE
    browser_role TEXT;
BEGIN
    FOREACH browser_role IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = browser_role) THEN
            EXECUTE format(
                'REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM %I',
                browser_role
            );
            EXECUTE format(
                'REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM %I',
                browser_role
            );
            EXECUTE format(
                'ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public '
                'REVOKE ALL PRIVILEGES ON TABLES FROM %I',
                browser_role
            );
            EXECUTE format(
                'ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public '
                'REVOKE ALL PRIVILEGES ON SEQUENCES FROM %I',
                browser_role
            );
        END IF;
    END LOOP;
END
$$;
