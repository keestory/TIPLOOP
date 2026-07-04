"""영상 지점 코멘트 저장소 (Supabase Postgres)."""

from __future__ import annotations

from app.repo.database import get_connection
from app.types.models import MediaComment

_SELECT = """
SELECT m.id, m.post_id, m.author_id, m.t_seconds, m.x, m.y, m.body,
       to_char(m.created_at, 'YYYY-MM-DD HH24:MI') AS created_at,
       u.name AS author_name
FROM media_comments m
JOIN members u ON u.id = m.author_id
"""


def _to_media_comment(row: dict) -> MediaComment:
    return MediaComment(
        id=row["id"],
        post_id=row["post_id"],
        author_id=row["author_id"],
        t_seconds=float(row["t_seconds"]),
        x=float(row["x"]),
        y=float(row["y"]),
        body=row["body"],
        created_at=row["created_at"],
        author_name=row["author_name"],
    )


def create(
    post_id: int, author_id: int, t_seconds: float, x: float, y: float, body: str
) -> MediaComment:
    with get_connection() as conn:
        row = conn.execute(
            "INSERT INTO media_comments (post_id, author_id, t_seconds, x, y, body) "
            "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (post_id, author_id, t_seconds, x, y, body),
        ).fetchone()
        return get(row["id"])


def get(comment_id: int) -> MediaComment | None:
    with get_connection() as conn:
        row = conn.execute(_SELECT + " WHERE m.id = %s", (comment_id,)).fetchone()
        return _to_media_comment(row) if row else None


def list_for_post(post_id: int) -> list[MediaComment]:
    with get_connection() as conn:
        rows = conn.execute(
            _SELECT + " WHERE m.post_id = %s ORDER BY m.t_seconds ASC, m.id ASC", (post_id,)
        ).fetchall()
        return [_to_media_comment(r) for r in rows]
