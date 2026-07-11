"""크루 저장소 — 함께 쓰는 주간 기록 (Supabase Postgres)."""

from __future__ import annotations

from app.repo.database import get_connection
from app.types.models import Crew, CrewEntry

_SELECT = """
SELECT c.id, c.name, c.topic, c.invite_code, c.created_by,
       to_char(c.created_at, 'YYYY-MM-DD') AS created_at,
       (SELECT COUNT(*) FROM crew_members m WHERE m.crew_id = c.id) AS member_count
FROM crews c
"""


def _to_crew(row: dict) -> Crew:
    return Crew(
        id=row["id"], name=row["name"], topic=row["topic"],
        invite_code=row["invite_code"], created_by=row["created_by"],
        created_at=row["created_at"], member_count=row["member_count"],
    )


def _to_entry(row: dict) -> CrewEntry:
    return CrewEntry(
        id=row["id"], crew_id=row["crew_id"], author_id=row["author_id"],
        week=row["week"], body=row["body"], created_at=row["created_at"],
        author_name=row["author_name"],
    )


def create(name: str, topic: str | None, invite_code: str, created_by: int) -> Crew:
    """크루를 만들고 만든 사람을 첫 멤버로 넣는다."""
    with get_connection() as conn:
        row = conn.execute(
            "INSERT INTO crews (name, topic, invite_code, created_by) "
            "VALUES (%s, %s, %s, %s) RETURNING id",
            (name, topic, invite_code, created_by),
        ).fetchone()
        conn.execute(
            "INSERT INTO crew_members (crew_id, member_id) VALUES (%s, %s)",
            (row["id"], created_by),
        )
        return get(row["id"])  # member_count 포함해 다시 읽는다


def get(crew_id: int) -> Crew | None:
    with get_connection() as conn:
        row = conn.execute(_SELECT + " WHERE c.id = %s", (crew_id,)).fetchone()
        return _to_crew(row) if row else None


def get_by_code(invite_code: str) -> Crew | None:
    with get_connection() as conn:
        row = conn.execute(_SELECT + " WHERE c.invite_code = %s", (invite_code,)).fetchone()
        return _to_crew(row) if row else None


def list_for_member(member_id: int) -> list[Crew]:
    sql = _SELECT + (
        " JOIN crew_members cm ON cm.crew_id = c.id"
        " WHERE cm.member_id = %s ORDER BY cm.joined_at DESC"
    )
    with get_connection() as conn:
        return [_to_crew(r) for r in conn.execute(sql, (member_id,)).fetchall()]


def is_member(crew_id: int, member_id: int) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM crew_members WHERE crew_id = %s AND member_id = %s",
            (crew_id, member_id),
        ).fetchone()
        return row is not None


def add_member(crew_id: int, member_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO crew_members (crew_id, member_id) VALUES (%s, %s) "
            "ON CONFLICT DO NOTHING",
            (crew_id, member_id),
        )


def member_ids(crew_id: int) -> list[int]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT member_id FROM crew_members WHERE crew_id = %s ORDER BY joined_at",
            (crew_id,),
        ).fetchall()
        return [r["member_id"] for r in rows]


def members_of(crew_id: int) -> list[dict]:
    """멤버 표시 정보 (id, name, avatar_url) — 참여 도트용."""
    sql = """
    SELECT u.id, u.name, u.avatar_url
    FROM crew_members cm JOIN members u ON u.id = cm.member_id
    WHERE cm.crew_id = %s ORDER BY cm.joined_at
    """
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(sql, (crew_id,)).fetchall()]


def add_entry(crew_id: int, author_id: int, week: str, body: str) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "INSERT INTO crew_entries (crew_id, author_id, week, body) "
            "VALUES (%s, %s, %s, %s) RETURNING id",
            (crew_id, author_id, week, body),
        ).fetchone()
        return row["id"]


def entries(crew_id: int, week: str) -> list[CrewEntry]:
    sql = """
    SELECT e.id, e.crew_id, e.author_id, e.week, e.body,
           to_char(e.created_at, 'MM-DD HH24:MI') AS created_at,
           u.name AS author_name
    FROM crew_entries e JOIN members u ON u.id = e.author_id
    WHERE e.crew_id = %s AND e.week = %s
    ORDER BY e.created_at DESC, e.id DESC
    """
    with get_connection() as conn:
        return [_to_entry(r) for r in conn.execute(sql, (crew_id, week)).fetchall()]


def participant_ids(crew_id: int, week: str) -> set[int]:
    """이번 주에 한 번이라도 기록한 멤버 id — 참여 도트의 근거."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT author_id FROM crew_entries WHERE crew_id = %s AND week = %s",
            (crew_id, week),
        ).fetchall()
        return {r["author_id"] for r in rows}


def recent_weeks(crew_id: int, limit: int = 5) -> list[str]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT week FROM crew_entries WHERE crew_id = %s "
            "ORDER BY week DESC LIMIT %s",
            (crew_id, limit),
        ).fetchall()
        return [r["week"] for r in rows]
