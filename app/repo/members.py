"""회원 프로필 저장소 (Supabase Postgres).

인증 자체는 Supabase Auth가 맡고, 여기엔 프로필만 보관한다.
auth_id(Supabase 사용자 id)로 우리 회원 레코드와 1:1 매핑.
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
        job_role=row["job_role"],
        years=row["years"],
        industry=row["industry"],
        topics=tuple(row.get("topics") or ()),
        agreed_terms=bool(row.get("agreed_terms")),
        has_seen_tour=bool(row.get("has_seen_tour")),
    )


def upsert_by_auth(
    auth_id: str,
    name: str,
    email: str | None,
    avatar_url: str | None,
    provider: str | None,
) -> User:
    """소셜 로그인 결과로 회원을 만들거나 갱신한다(이름·이메일·아바타·제공자 최신화)."""
    sql = """
    INSERT INTO members (auth_id, name, email, avatar_url, provider)
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


def get(member_id: int) -> User | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM members WHERE id = %s", (member_id,)).fetchone()
        return _to_user(row) if row else None


def get_by_auth(auth_id: str) -> User | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM members WHERE auth_id = %s", (auth_id,)).fetchone()
        return _to_user(row) if row else None


def agree_terms(member_id: int) -> None:
    """약관·개인정보 동의를 저장한다."""
    with get_connection() as conn:
        conn.execute("UPDATE members SET agreed_terms = TRUE WHERE id = %s", (member_id,))


def mark_tour_seen(member_id: int) -> None:
    """첫 로그인 코치마크 투어를 봤다고 표시한다(다시 안 뜸)."""
    with get_connection() as conn:
        conn.execute("UPDATE members SET has_seen_tour = TRUE WHERE id = %s", (member_id,))


def subscribers_of_topic(topic: str) -> list[int]:
    """해당 주제를 관심 목록에 담은 회원 id들. 구독 알림 대상 산출용."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id FROM members WHERE %s = ANY(topics)", (topic,)
        ).fetchall()
        return [r["id"] for r in rows]


def set_topics(member_id: int, topics: list[str]) -> User:
    """온보딩 1단계 — 관심 주제를 저장한다."""
    sql = "UPDATE members SET topics = %s WHERE id = %s RETURNING *;"
    with get_connection() as conn:
        row = conn.execute(sql, (list(topics), member_id)).fetchone()
        return _to_user(row)


def complete_profile(member_id: int, job_role: str, years: str, industry: str) -> User:
    """온보딩 — 직군·연차·업종을 채운다."""
    sql = """
    UPDATE members
    SET job_role = %s, years = %s, industry = %s
    WHERE id = %s
    RETURNING *;
    """
    with get_connection() as conn:
        row = conn.execute(sql, (job_role, years, industry, member_id)).fetchone()
        return _to_user(row)
