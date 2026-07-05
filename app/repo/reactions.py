"""공감(반응) 저장소 — 글/댓글에 대한 단일 반응 토글 (Supabase Postgres)."""

from __future__ import annotations

from app.repo.database import get_connection


def toggle_post_reaction(post_id: int, user_id: int) -> bool:
    """글 공감을 토글한다. 토글 후 켜졌으면 True."""
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT 1 FROM post_reactions WHERE post_id = %s AND user_id = %s", (post_id, user_id)
        ).fetchone()
        if existing:
            conn.execute(
                "DELETE FROM post_reactions WHERE post_id = %s AND user_id = %s", (post_id, user_id)
            )
            return False
        conn.execute(
            "INSERT INTO post_reactions (post_id, user_id) VALUES (%s, %s)", (post_id, user_id)
        )
        return True


def toggle_comment_reaction(comment_id: int, user_id: int) -> bool:
    """댓글 공감을 토글한다. 토글 후 켜졌으면 True."""
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT 1 FROM comment_reactions WHERE comment_id = %s AND user_id = %s",
            (comment_id, user_id),
        ).fetchone()
        if existing:
            conn.execute(
                "DELETE FROM comment_reactions WHERE comment_id = %s AND user_id = %s",
                (comment_id, user_id),
            )
            return False
        conn.execute(
            "INSERT INTO comment_reactions (comment_id, user_id) VALUES (%s, %s)",
            (comment_id, user_id),
        )
        return True


def reacted_post_ids(user_id: int) -> set[int]:
    """사용자가 공감한 글 id 집합 (화면에서 버튼 상태 표시용)."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT post_id FROM post_reactions WHERE user_id = %s", (user_id,)
        ).fetchall()
        return {r["post_id"] for r in rows}


def reacted_comment_ids(user_id: int, post_id: int) -> set[int]:
    """사용자가 공감한, 해당 글의 댓글 id 집합."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT cr.comment_id FROM comment_reactions cr "
            "JOIN comments c ON c.id = cr.comment_id "
            "WHERE cr.user_id = %s AND c.post_id = %s",
            (user_id, post_id),
        ).fetchall()
        return {r["comment_id"] for r in rows}


def toggle_post_helpful(post_id: int, user_id: int) -> bool:
    """'도움됐어요'를 토글한다. 토글 후 켜졌으면 True."""
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT 1 FROM post_helpful WHERE post_id = %s AND user_id = %s", (post_id, user_id)
        ).fetchone()
        if existing:
            conn.execute(
                "DELETE FROM post_helpful WHERE post_id = %s AND user_id = %s", (post_id, user_id)
            )
            return False
        conn.execute(
            "INSERT INTO post_helpful (post_id, user_id) VALUES (%s, %s)", (post_id, user_id)
        )
        return True


def helpful_post_ids(user_id: int) -> set[int]:
    """사용자가 '도움됐어요' 누른 글 id 집합."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT post_id FROM post_helpful WHERE user_id = %s", (user_id,)
        ).fetchall()
        return {r["post_id"] for r in rows}


def received_helpful_count(user_id: int) -> int:
    """이 사용자의 글이 받은 '도움됐어요' 총합 — '도움을 준 사람 수'."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM post_helpful h JOIN posts p ON p.id = h.post_id "
            "WHERE p.author_id = %s",
            (user_id,),
        ).fetchone()
        return int(row["n"] or 0)


def received_reaction_count(user_id: int) -> int:
    """이 사용자가 쓴 글/댓글이 받은 공감 총합 (프로필 카르마)."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT "
            "(SELECT COUNT(*) FROM post_reactions pr JOIN posts p ON p.id = pr.post_id "
            "  WHERE p.author_id = %s) + "
            "(SELECT COUNT(*) FROM comment_reactions cr JOIN comments c ON c.id = cr.comment_id "
            "  WHERE c.author_id = %s) AS total",
            (user_id, user_id),
        ).fetchone()
        return int(row["total"] or 0)
