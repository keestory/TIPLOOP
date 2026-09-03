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
    deletion_started_at TIMESTAMPTZ,              -- 계정 삭제 중: 새 Storage 업로드 차단
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE members ADD COLUMN IF NOT EXISTS deletion_started_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS posts (
    id         BIGSERIAL PRIMARY KEY,
    author_id  BIGINT NOT NULL REFERENCES members(id),
    category   TEXT NOT NULL,
    title      TEXT NOT NULL,
    body       TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    link_url   TEXT,                          -- 레퍼런스 참고 링크 (선택)
    image_url  TEXT,                          -- 주석 이미지 (Supabase Storage URL, 선택)
    video_url  TEXT,                          -- 첨부 영상 (Supabase Storage URL, 선택)
    analysis_mode TEXT CHECK (analysis_mode IS NULL OR analysis_mode IN ('quick', 'focus', 'full')),
    analysis_template_version TEXT,
    selected_question_ids TEXT[],
    attachments JSONB CHECK (
        attachments IS NULL OR (
            jsonb_typeof(attachments) = 'array' AND jsonb_array_length(attachments) <= 6
        )
    )                                         -- 비공개 Storage path와 표시 메타데이터
);

-- 작성자가 명시적으로 켠 링크 공유. 원문 토큰은 저장하지 않고 해시만 둔다.
CREATE TABLE IF NOT EXISTS post_shares (
    id            BIGSERIAL PRIMARY KEY,
    post_id       BIGINT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    token_hash    TEXT NOT NULL UNIQUE CHECK (token_hash ~ '^[0-9a-f]{64}$'),
    include_media BOOLEAN NOT NULL DEFAULT FALSE,
    snapshot      JSONB NOT NULL CHECK (jsonb_typeof(snapshot) = 'object'),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at    TIMESTAMPTZ NOT NULL DEFAULT (now() + interval '7 days'),
    revoked_at    TIMESTAMPTZ,
    CHECK (expires_at > created_at AND expires_at <= created_at + interval '30 days')
);
CREATE TABLE IF NOT EXISTS post_share_media_grants (
    id               BIGSERIAL PRIMARY KEY,
    share_id         BIGINT NOT NULL REFERENCES post_shares(id) ON DELETE CASCADE,
    attachment_index SMALLINT NOT NULL CHECK (attachment_index BETWEEN 0 AND 5),
    token_hash       TEXT NOT NULL UNIQUE CHECK (token_hash ~ '^[0-9a-f]{64}$'),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (share_id, attachment_index)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_post_shares_one_active
    ON post_shares(post_id) WHERE revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_post_shares_active_token
    ON post_shares(token_hash) WHERE revoked_at IS NULL;

-- 기존 설치에도 질문 선택·private 첨부 컬럼을 추가한다.
ALTER TABLE posts ADD COLUMN IF NOT EXISTS analysis_mode TEXT;
ALTER TABLE posts ADD COLUMN IF NOT EXISTS analysis_template_version TEXT;
ALTER TABLE posts ADD COLUMN IF NOT EXISTS selected_question_ids TEXT[];
ALTER TABLE posts ADD COLUMN IF NOT EXISTS attachments JSONB;

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
ALTER TABLE post_shares ENABLE ROW LEVEL SECURITY;
ALTER TABLE post_share_media_grants ENABLE ROW LEVEL SECURITY;

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

-- 연구 노트의 스크린샷·영상은 공개 URL이 아닌 사용자별 private bucket에 둔다.
-- 두 버킷으로 나눠 이미지가 영상의 50 MiB 상한을 악용하지 못하게 한다.
INSERT INTO storage.buckets (
    id, name, public, file_size_limit, allowed_mime_types
)
VALUES (
    'tiploop-research-images', 'tiploop-research-images', FALSE, 10485760,
    ARRAY['image/jpeg', 'image/png', 'image/webp', 'image/gif']
)
ON CONFLICT (id) DO UPDATE SET
    public = EXCLUDED.public,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;

INSERT INTO storage.buckets (
    id, name, public, file_size_limit, allowed_mime_types
)
VALUES (
    'tiploop-research-videos', 'tiploop-research-videos', FALSE, 52428800,
    ARRAY['video/mp4', 'video/webm', 'video/quicktime']
)
ON CONFLICT (id) DO UPDATE SET
    public = EXCLUDED.public,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;

DROP POLICY IF EXISTS "research_media_insert_own" ON storage.objects;
CREATE OR REPLACE FUNCTION public.tiploop_account_accepts_storage()
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, auth
AS $$
DECLARE
    account_is_active BOOLEAN;
BEGIN
    -- 행 잠금으로 삭제 시작과 업로드의 경합을 직렬화한다.
    SELECT deletion_started_at IS NULL
      INTO account_is_active
      FROM public.members
     WHERE auth_id = auth.uid()::text
       FOR SHARE;
    RETURN COALESCE(account_is_active, FALSE);
END;
$$;
REVOKE ALL ON FUNCTION public.tiploop_account_accepts_storage() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.tiploop_account_accepts_storage() TO authenticated;

CREATE POLICY "research_media_insert_own"
ON storage.objects FOR INSERT TO authenticated
WITH CHECK (
    bucket_id IN ('tiploop-research-images', 'tiploop-research-videos')
    AND public.tiploop_account_accepts_storage()
    AND (storage.foldername(name))[1] = (SELECT auth.uid()::text)
    AND (storage.foldername(name))[2] = 'drafts'
    AND cardinality(storage.foldername(name)) = 3
    AND (
        (bucket_id = 'tiploop-research-images' AND storage.extension(name) IN ('jpg', 'png', 'webp', 'gif'))
        OR
        (bucket_id = 'tiploop-research-videos' AND storage.extension(name) IN ('mp4', 'webm', 'mov'))
    )
);

DROP POLICY IF EXISTS "research_media_select_own" ON storage.objects;
CREATE POLICY "research_media_select_own"
ON storage.objects FOR SELECT TO authenticated
USING (
    bucket_id IN ('tiploop-research-images', 'tiploop-research-videos')
    AND (storage.foldername(name))[1] = (SELECT auth.uid()::text)
    AND owner_id = (SELECT auth.uid()::text)
);

DROP POLICY IF EXISTS "research_media_delete_own" ON storage.objects;
CREATE POLICY "research_media_delete_own"
ON storage.objects FOR DELETE TO authenticated
USING (
    bucket_id IN ('tiploop-research-images', 'tiploop-research-videos')
    AND (storage.foldername(name))[1] = (SELECT auth.uid()::text)
    AND owner_id = (SELECT auth.uid()::text)
);
