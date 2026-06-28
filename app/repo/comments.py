"""댓글 저장소."""

import sqlite3

from app.repo.database import get_connection
from app.types.models import Comment

_SELECT = """
SELECT c.*, u.name AS author_name, u.school_level AS author_school_level
FROM comments c
JOIN users u ON u.id = c.author_id
"""


def _to_comment(row: sqlite3.Row) -> Comment:
    return Comment(
        id=row["id"],
        post_id=row["post_id"],
        author_id=row["author_id"],
        body=row["body"],
        created_at=row["created_at"],
        author_name=row["author_name"],
        author_school_level=row["author_school_level"],
    )


def create_comment(post_id: int, author_id: int, body: str) -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO comments (post_id, author_id, body) VALUES (?, ?, ?)",
            (post_id, author_id, body),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_comments(post_id: int) -> list[Comment]:
    conn = get_connection()
    try:
        rows = conn.execute(
            _SELECT + " WHERE c.post_id = ? ORDER BY c.created_at ASC, c.id ASC", (post_id,)
        )
        return [_to_comment(r) for r in rows.fetchall()]
    finally:
        conn.close()
