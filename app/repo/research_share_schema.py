"""앱 초기화에서도 쓰는 연구 링크 공유 스키마."""

RESEARCH_SHARE_SCHEMA = """
-- 작성자가 명시적으로 켠 링크 공유. 토큰 원문은 저장하지 않는다.
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
CREATE UNIQUE INDEX IF NOT EXISTS idx_post_shares_one_active
    ON post_shares(post_id) WHERE revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_post_shares_active_token
    ON post_shares(token_hash) WHERE revoked_at IS NULL;

CREATE TABLE IF NOT EXISTS post_share_media_grants (
    id               BIGSERIAL PRIMARY KEY,
    share_id         BIGINT NOT NULL REFERENCES post_shares(id) ON DELETE CASCADE,
    attachment_index SMALLINT NOT NULL CHECK (attachment_index BETWEEN 0 AND 5),
    token_hash       TEXT NOT NULL UNIQUE CHECK (token_hash ~ '^[0-9a-f]{64}$'),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (share_id, attachment_index)
);
"""
