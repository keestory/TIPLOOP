"""팔로우 저장소 — 단방향 팔로우 관계 (Supabase Postgres)."""

from __future__ import annotations

from app.repo.database import get_connection


def follow(follower_id: int, followee_id: int) -> bool:
    """팔로우한다. 새로 생겼으면 True, 이미 있었으면 False(멱등)."""
    sql = (
        "INSERT INTO follows (follower_id, followee_id) VALUES (%s, %s) "
        "ON CONFLICT DO NOTHING RETURNING follower_id"
    )
    with get_connection() as conn:
        row = conn.execute(sql, (follower_id, followee_id)).fetchone()
        return row is not None


def unfollow(follower_id: int, followee_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM follows WHERE follower_id = %s AND followee_id = %s",
            (follower_id, followee_id),
        )


def is_following(follower_id: int, followee_id: int) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM follows WHERE follower_id = %s AND followee_id = %s",
            (follower_id, followee_id),
        ).fetchone()
        return row is not None


def followee_ids(member_id: int) -> list[int]:
    """내가 팔로우하는 사람들의 id 목록 (주간 다이제스트 등에서 필터링용)."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT followee_id FROM follows WHERE follower_id = %s", (member_id,)
        ).fetchall()
        return [r["followee_id"] for r in rows]


def followers_count(member_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM follows WHERE followee_id = %s", (member_id,)
        ).fetchone()
        return row["n"]


def following_count(member_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM follows WHERE follower_id = %s", (member_id,)
        ).fetchone()
        return row["n"]
