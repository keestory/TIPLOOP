"""Supabase Postgres의 브라우저 접근 차단 상수와 SQL."""

from __future__ import annotations

RLS_TABLES = (
    "members", "posts", "media_comments", "comments", "post_reactions",
    "comment_reactions", "post_helpful", "reviews", "follows", "crews",
    "crew_members", "crew_entries", "notifications", "post_shares",
    "post_share_media_grants",
)

REVOKE_BROWSER_PRIVILEGES_SQL = """
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
$$
"""
