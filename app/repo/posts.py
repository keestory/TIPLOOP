"""글 저장소 — 작성과 필터 조회."""

import sqlite3

from app.repo.database import get_connection
from app.types.models import Post

# 작성자 표시 정보를 함께 가져오는 공통 SELECT
_SELECT = """
SELECT p.*, u.name AS author_name, u.school_level AS author_school_level,
       u.region AS author_region
FROM posts p
JOIN users u ON u.id = p.author_id
"""


def _to_post(row: sqlite3.Row) -> Post:
    return Post(
        id=row["id"],
        author_id=row["author_id"],
        category=row["category"],
        title=row["title"],
        body=row["body"],
        created_at=row["created_at"],
        event_at=row["event_at"],
        location=row["location"],
        online_url=row["online_url"],
        author_name=row["author_name"],
        author_school_level=row["author_school_level"],
        author_region=row["author_region"],
    )


def create_post(
    author_id: int,
    category: str,
    title: str,
    body: str,
    event_at: str | None = None,
    location: str | None = None,
    online_url: str | None = None,
) -> int:
    """글을 만들고 id를 돌려준다."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO posts (author_id, category, title, body, event_at, location, online_url) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (author_id, category, title, body, event_at, location, online_url),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_post(post_id: int) -> Post | None:
    conn = get_connection()
    try:
        row = conn.execute(_SELECT + " WHERE p.id = ?", (post_id,)).fetchone()
        return _to_post(row) if row else None
    finally:
        conn.close()


def list_posts(
    category: str | None = None,
    school_level: str | None = None,
    region: str | None = None,
    author_id: int | None = None,
) -> list[Post]:
    """필터를 AND로 적용해 최신순으로 글을 돌려준다."""
    clauses: list[str] = []
    params: list[object] = []
    if category:
        clauses.append("p.category = ?")
        params.append(category)
    if school_level:
        clauses.append("u.school_level = ?")
        params.append(school_level)
    if region:
        clauses.append("u.region = ?")
        params.append(region)
    if author_id is not None:
        clauses.append("p.author_id = ?")
        params.append(author_id)

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    conn = get_connection()
    try:
        rows = conn.execute(_SELECT + where + " ORDER BY p.created_at DESC, p.id DESC", params)
        return [_to_post(r) for r in rows.fetchall()]
    finally:
        conn.close()
