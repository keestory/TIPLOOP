"""적용 후기 저장소 (Supabase Postgres)."""

from __future__ import annotations

from datetime import date

from app.repo.database import get_connection
from app.types.models import Review

_SELECT = """
SELECT r.id, r.post_id, r.author_id, r.body,
       to_char(r.created_at, 'YYYY-MM-DD HH24:MI') AS created_at,
       u.name AS author_name, u.job_role AS author_job_role
FROM reviews r
JOIN members u ON u.id = r.author_id
"""


def _to_review(row: dict) -> Review:
    return Review(
        id=row["id"],
        post_id=row["post_id"],
        author_id=row["author_id"],
        body=row["body"],
        created_at=row["created_at"],
        author_name=row["author_name"],
        author_job_role=row["author_job_role"],
        post_title=row.get("post_title"),
    )


def create(post_id: int, author_id: int, body: str) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "INSERT INTO reviews (post_id, author_id, body) VALUES (%s, %s, %s) RETURNING id",
            (post_id, author_id, body),
        ).fetchone()
        return row["id"]


def list_for_post(post_id: int) -> list[Review]:
    with get_connection() as conn:
        rows = conn.execute(
            _SELECT + " WHERE r.post_id = %s ORDER BY r.created_at DESC, r.id DESC", (post_id,)
        ).fetchall()
        return [_to_review(r) for r in rows]


def received_since(author_id: int, since: date) -> list[Review]:
    """이 사용자의 글이 특정 날짜 이후 받은 후기 (주간 다이제스트용). 글 제목 포함."""
    sql = """
    SELECT r.id, r.post_id, r.author_id, r.body,
           to_char(r.created_at, 'YYYY-MM-DD HH24:MI') AS created_at,
           u.name AS author_name, u.job_role AS author_job_role, p.title AS post_title
    FROM reviews r
    JOIN members u ON u.id = r.author_id
    JOIN posts p   ON p.id = r.post_id
    WHERE p.author_id = %s AND r.created_at >= %s
    ORDER BY r.created_at DESC
    """
    with get_connection() as conn:
        rows = conn.execute(sql, (author_id, since)).fetchall()
        return [_to_review(r) for r in rows]


def received_count(author_id: int) -> int:
    """이 사용자의 글이 받은 후기 총합."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM reviews r JOIN posts p ON p.id = r.post_id "
            "WHERE p.author_id = %s",
            (author_id,),
        ).fetchone()
        return int(row["n"] or 0)
