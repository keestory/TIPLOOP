"""댓글 저장소 — 답글(parent_id)과 공감 집계 포함 (Supabase Postgres)."""

from __future__ import annotations

from app.repo.database import get_connection
from app.types.models import Comment

_SELECT = """
SELECT c.id, c.post_id, c.author_id, c.body, c.parent_id,
       to_char(c.created_at, 'YYYY-MM-DD HH24:MI') AS created_at,
       u.name AS author_name, u.school_level AS author_school_level,
       (SELECT COUNT(*) FROM comment_reactions r WHERE r.comment_id = c.id) AS reaction_count
FROM comments c
JOIN teachers u ON u.id = c.author_id
"""


def _to_comment(row: dict) -> Comment:
    return Comment(
        id=row["id"],
        post_id=row["post_id"],
        author_id=row["author_id"],
        body=row["body"],
        created_at=row["created_at"],
        parent_id=row["parent_id"],
        author_name=row["author_name"],
        author_school_level=row["author_school_level"],
        reaction_count=row["reaction_count"],
    )


def create_comment(post_id: int, author_id: int, body: str, parent_id: int | None = None) -> int:
    sql = (
        "INSERT INTO comments (post_id, author_id, body, parent_id) "
        "VALUES (%s, %s, %s, %s) RETURNING id"
    )
    with get_connection() as conn:
        row = conn.execute(sql, (post_id, author_id, body, parent_id)).fetchone()
        return row["id"]


def get_comment(comment_id: int) -> Comment | None:
    with get_connection() as conn:
        row = conn.execute(_SELECT + " WHERE c.id = %s", (comment_id,)).fetchone()
        return _to_comment(row) if row else None


def list_comments(post_id: int) -> list[Comment]:
    """글의 모든 댓글을 작성순으로. 스레드 구성은 상위 레이어에서 한다."""
    with get_connection() as conn:
        rows = conn.execute(
            _SELECT + " WHERE c.post_id = %s ORDER BY c.created_at ASC, c.id ASC", (post_id,)
        ).fetchall()
        return [_to_comment(r) for r in rows]
