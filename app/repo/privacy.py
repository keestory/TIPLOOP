"""Supabase public 스키마의 브라우저 접근 차단 검증."""

from __future__ import annotations

from app.config.database_security import RLS_TABLES
from app.repo.database import get_connection


def verify_privacy_boundaries() -> None:
    """앱 테이블과 계정 삭제용 Storage gate를 fail-closed로 확인한다."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT c.relname, c.relrowsecurity
              FROM pg_class c
              JOIN pg_namespace n ON n.oid = c.relnamespace
             WHERE n.nspname = 'public' AND c.relname = ANY(%s)
            """,
            (list(RLS_TABLES),),
        ).fetchall()
        states = {row["relname"]: row["relrowsecurity"] for row in rows}
        unsafe = [table for table in RLS_TABLES if not states.get(table)]
        if unsafe:
            raise RuntimeError(
                "RLS 보안 경계가 비활성화된 테이블: " + ", ".join(unsafe)
            )

        policies = conn.execute(
            """
            SELECT tablename, policyname, roles
              FROM pg_policies
             WHERE schemaname = 'public' AND tablename = ANY(%s)
            """,
            (list(RLS_TABLES),),
        ).fetchall()
        browser_roles = {"public", "anon", "authenticated"}
        exposed = [
            f"{row['tablename']}.{row['policyname']}"
            for row in policies
            if browser_roles.intersection(role.lower() for role in row["roles"])
        ]
        if exposed:
            raise RuntimeError(
                "브라우저 역할에 열린 RLS 정책이 있습니다: " + ", ".join(exposed)
            )

        privileges = conn.execute(
            """
            WITH browser_roles AS (
                SELECT rolname
                  FROM pg_roles
                 WHERE rolname IN ('anon', 'authenticated')
            ), app_tables AS (
                SELECT unnest(%s::text[]) AS table_name
            )
            SELECT r.rolname AS role_name, t.table_name
              FROM browser_roles r
              CROSS JOIN app_tables t
             WHERE has_table_privilege(
                 r.rolname,
                 format('%%I.%%I', 'public', t.table_name),
                 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'
             )
            """,
            (list(RLS_TABLES),),
        ).fetchall()
        if privileges:
            opened = [
                f"{row['role_name']}:{row['table_name']}" for row in privileges
            ]
            raise RuntimeError(
                "브라우저 역할에 직접 테이블 권한이 있습니다: " + ", ".join(opened)
            )

        deletion_gate = conn.execute(
            """
            SELECT
                EXISTS (
                    SELECT 1
                      FROM information_schema.columns
                     WHERE table_schema = 'public'
                       AND table_name = 'members'
                       AND column_name = 'deletion_started_at'
                ) AS has_tombstone,
                EXISTS (
                    SELECT 1
                      FROM pg_proc p
                      JOIN pg_namespace n ON n.oid = p.pronamespace
                     WHERE n.nspname = 'tiploop_private'
                       AND p.proname = 'tiploop_account_accepts_storage'
                       AND p.prosecdef
                       AND array_to_string(p.proconfig, ',') LIKE
                           '%%search_path=public, auth, pg_temp%%'
                ) AS has_safe_function,
                has_schema_privilege(
                    'authenticated', 'tiploop_private', 'USAGE'
                ) AS authenticated_schema_usage,
                has_schema_privilege('anon', 'tiploop_private', 'USAGE')
                    AS anon_schema_usage,
                has_function_privilege(
                    'authenticated',
                    'tiploop_private.tiploop_account_accepts_storage()',
                    'EXECUTE'
                ) AS authenticated_execute,
                has_function_privilege(
                    'anon',
                    'tiploop_private.tiploop_account_accepts_storage()',
                    'EXECUTE'
                ) AS anon_execute,
                EXISTS (
                    SELECT 1
                      FROM pg_policies
                     WHERE schemaname = 'storage'
                       AND tablename = 'objects'
                       AND policyname = 'research_media_insert_own'
                       AND cmd = 'INSERT'
                       AND roles = ARRAY['authenticated'::name]
                       AND with_check LIKE
                           '%%tiploop_account_accepts_storage%%'
                ) AS insert_policy_uses_gate
            """,
            (),
        ).fetchone()
        gate_is_safe = deletion_gate and all(
            (
                deletion_gate["has_tombstone"],
                deletion_gate["has_safe_function"],
                deletion_gate["authenticated_schema_usage"],
                not deletion_gate["anon_schema_usage"],
                deletion_gate["authenticated_execute"],
                not deletion_gate["anon_execute"],
                deletion_gate["insert_policy_uses_gate"],
            )
        )
        if not gate_is_safe:
            raise RuntimeError(
                "계정 삭제 중 새 첨부를 차단하는 Storage 보안 경계가 올바르지 않습니다."
            )
