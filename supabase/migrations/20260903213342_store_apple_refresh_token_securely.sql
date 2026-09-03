-- Apple 로그인 계정 삭제 시 Apple OAuth token revocation을 수행하기 위한
-- refresh token 암호문과 재시도 상태. 평문 토큰은 저장하지 않는다.
CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions;

ALTER TABLE public.members
    ADD COLUMN IF NOT EXISTS provider_refresh_token_ciphertext BYTEA,
    ADD COLUMN IF NOT EXISTS provider_token_revoked_at TIMESTAMPTZ;

COMMENT ON COLUMN public.members.provider_refresh_token_ciphertext IS
    'Apple provider refresh token encrypted with pgcrypto; never store plaintext';
COMMENT ON COLUMN public.members.provider_token_revoked_at IS
    'Successful Apple token revocation timestamp for idempotent account deletion';

REVOKE ALL ON TABLE public.members FROM anon, authenticated;
