"""글 저장소 — 작성과 필터 조회 (Supabase Postgres)."""

from __future__ import annotations

from app.repo.database import get_connection
from app.types.models import Post

# 작성자 표시 정보 + 인게이지먼트 집계를 함께 가져오는 공통 SELECT
_SELECT = """
SELECT p.id, p.author_id, p.category, p.title, p.body,
       to_char(p.created_at, 'YYYY-MM-DD HH24:MI') AS created_at,
       p.link_url, p.image_url, p.video_url,
       u.name AS author_name, u.job_role AS author_job_role, u.years AS author_years,
       (SELECT COUNT(*) FROM post_reactions r WHERE r.post_id = p.id) AS reaction_count,
       (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) AS comment_count,
       (SELECT COUNT(*) FROM post_helpful h WHERE h.post_id = p.id) AS helpful_count,
       (SELECT COUNT(*) FROM reviews v WHERE v.post_id = p.id) AS review_count
FROM posts p
JOIN members u ON u.id = p.author_id
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
        link_url=row["link_url"],
        image_url=row["image_url"],
        video_url=row["video_url"],
        author_name=row["author_name"],
        author_job_role=row["author_job_role"],
        author_years=row["author_years"],
        reaction_count=row["reaction_count"],
        comment_count=row["comment_count"],
        helpful_count=row["helpful_count"],
        review_count=row["review_count"],
    )


def create_post(
    author_id: int,
    category: str,
    title: str,
    body: str,
    link_url: str | None = None,
    image_url: str | None = None,
    video_url: str | None = None,
) -> int:
    """글을 만들고 id를 돌려준다."""
    sql = (
        "INSERT INTO posts (author_id, category, title, body, link_url, image_url, video_url) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id"
    )
    with get_connection() as conn:
        row = conn.execute(
            sql, (author_id, category, title, body, link_url, image_url, video_url)
        ).fetchone()
        return row["id"]


def get_post(post_id: int) -> Post | None:
    with get_connection() as conn:
        row = conn.execute(_SELECT + " WHERE p.id = %s", (post_id,)).fetchone()
        return _to_post(row) if row else None


def list_posts(
    category: str | None = None,
    job_role: str | None = None,
    industry: str | None = None,
    author_id: int | None = None,
    search: str | None = None,
    sort: str = "new",
) -> list[Post]:
    """필터를 AND로 적용하고 sort(new|top|buzz)로 정렬해 돌려준다."""
    clauses: list[str] = []
    params: list[object] = []
    if category:
        clauses.append("p.category = %s")
        params.append(category)
    if job_role:
        clauses.append("u.job_role = %s")
        params.append(job_role)
    if industry:
        clauses.append("u.industry = %s")
        params.append(industry)
    if author_id is not None:
        clauses.append("p.author_id = %s")
        params.append(author_id)
    if search:
        # 제목 또는 본문에 검색어 포함 (대소문자 무시). %/_ 는 리터럴로.
        like = "%" + search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        clauses.append("(p.title ILIKE %s OR p.body ILIKE %s)")
        params.extend([like, like])

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    order = _ORDER.get(sort, _ORDER["new"])
    with get_connection() as conn:
        rows = conn.execute(_SELECT + where + " " + order, params).fetchall()
        return [_to_post(r) for r in rows]
