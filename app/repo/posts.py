"""글 저장소 — 작성과 필터 조회 (Supabase Postgres)."""

from __future__ import annotations

from app.repo.database import get_connection
from app.types.models import Post

# 작성자 표시 정보 + 인게이지먼트 집계를 함께 가져오는 공통 SELECT
_SELECT = """
SELECT p.id, p.author_id, p.category, p.title, p.body,
       to_char(p.created_at, 'YYYY-MM-DD HH24:MI') AS created_at,
       p.event_at, p.location, p.online_url,
       u.name AS author_name, u.school_level AS author_school_level,
       u.region AS author_region,
       (SELECT COUNT(*) FROM post_reactions r WHERE r.post_id = p.id) AS reaction_count,
       (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) AS comment_count
FROM posts p
JOIN teachers u ON u.id = p.author_id
"""

# 정렬: 최신 / 공감 / 화제(댓글 많은)
_ORDER = {
    "new": "ORDER BY p.created_at DESC, p.id DESC",
    "top": "ORDER BY reaction_count DESC, p.created_at DESC, p.id DESC",
    "buzz": "ORDER BY comment_count DESC, p.created_at DESC, p.id DESC",
}


def _to_post(row: dict) -> Post:
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
        reaction_count=row["reaction_count"],
        comment_count=row["comment_count"],
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
    sql = (
        "INSERT INTO posts (author_id, category, title, body, event_at, location, online_url) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id"
    )
    with get_connection() as conn:
        row = conn.execute(
            sql, (author_id, category, title, body, event_at, location, online_url)
        ).fetchone()
        return row["id"]


def get_post(post_id: int) -> Post | None:
    with get_connection() as conn:
        row = conn.execute(_SELECT + " WHERE p.id = %s", (post_id,)).fetchone()
        return _to_post(row) if row else None


def list_posts(
    category: str | None = None,
    school_level: str | None = None,
    region: str | None = None,
    author_id: int | None = None,
    sort: str = "new",
) -> list[Post]:
    """필터를 AND로 적용하고 sort(new|top|buzz)로 정렬해 돌려준다."""
    clauses: list[str] = []
    params: list[object] = []
    if category:
        clauses.append("p.category = %s")
        params.append(category)
    if school_level:
        clauses.append("u.school_level = %s")
        params.append(school_level)
    if region:
        clauses.append("u.region = %s")
        params.append(region)
    if author_id is not None:
        clauses.append("p.author_id = %s")
        params.append(author_id)

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    order = _ORDER.get(sort, _ORDER["new"])
    with get_connection() as conn:
        rows = conn.execute(_SELECT + where + " " + order, params).fetchall()
        return [_to_post(r) for r in rows]
