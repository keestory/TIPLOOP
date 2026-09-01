"""Supabase public 스키마의 브라우저 접근 차단 검증."""

from __future__ import annotations

from app.config.database_security import RLS_TABLES
from app.repo.database import get_connection


def verify_privacy_boundaries() -> None:
    """모든 앱 테이블의 RLS와 브라우저 역할 정책 부재를 확인한다."""
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
