"""교사 프로필 저장소 (Supabase Postgres).

인증 자체는 Supabase Auth가 맡고, 여기엔 프로필만 보관한다.
auth_id(Supabase 사용자 id)로 우리 교사 레코드와 1:1 매핑.
"""

from __future__ import annotations

from app.repo.database import get_connection
from app.types.models import User


def _to_user(row: dict) -> User:
    return User(
        id=row["id"],
        auth_id=row["auth_id"],
        name=row["name"],
        created_at=str(row["created_at"]),
        email=row["email"],
        avatar_url=row["avatar_url"],
        provider=row["provider"],
        phone=row["phone"],
        phone_verified=row["phone_verified"],
        school_level=row["school_level"],
        region=row["region"],
        subject=row["subject"],
    )


def upsert_by_auth(
    auth_id: str,
    name: str,
    email: str | None,
    avatar_url: str | None,
    provider: str | None,
) -> User:
    """소셜 로그인 결과로 교사를 만들거나 갱신한다(이름·이메일·아바타·제공자 최신화)."""
    sql = """
    INSERT INTO teachers (auth_id, name, email, avatar_url, provider)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (auth_id) DO UPDATE SET
        name = EXCLUDED.name,
        email = EXCLUDED.email,
        avatar_url = EXCLUDED.avatar_url,
        provider = EXCLUDED.provider
    RETURNING *;
    """
    with get_connection() as conn:
        row = conn.execute(sql, (auth_id, name, email, avatar_url, provider)).fetchone()
        return _to_user(row)


def get(teacher_id: int) -> User | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM teachers WHERE id = %s", (teacher_id,)).fetchone()
        return _to_user(row) if row else None


def get_by_auth(auth_id: str) -> User | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM teachers WHERE auth_id = %s", (auth_id,)).fetchone()
        return _to_user(row) if row else None


def complete_profile(teacher_id: int, school_level: str, region: str, subject: str) -> User:
    """온보딩 — 학교급·지역·담당을 채운다."""
    sql = """
    UPDATE teachers
    SET school_level = %s, region = %s, subject = %s
    WHERE id = %s
    RETURNING *;
    """
    with get_connection() as conn:
        row = conn.execute(sql, (school_level, region, subject, teacher_id)).fetchone()
        return _to_user(row)
