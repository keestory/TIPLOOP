"""공감(반응) 저장소 — 글/댓글에 대한 단일 반응 토글."""

from app.repo.database import get_connection


def toggle_post_reaction(post_id: int, user_id: int) -> bool:
    """글 공감을 토글한다. 토글 후 켜졌으면 True."""
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT 1 FROM post_reactions WHERE post_id = ? AND user_id = ?", (post_id, user_id)
        ).fetchone()
        if existing:
            conn.execute(
                "DELETE FROM post_reactions WHERE post_id = ? AND user_id = ?", (post_id, user_id)
            )
            now_on = False
        else:
            conn.execute(
                "INSERT INTO post_reactions (post_id, user_id) VALUES (?, ?)", (post_id, user_id)
            )
            now_on = True
        conn.commit()
        return now_on
    finally:
        conn.close()


def toggle_comment_reaction(comment_id: int, user_id: int) -> bool:
    """댓글 공감을 토글한다. 토글 후 켜졌으면 True."""
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT 1 FROM comment_reactions WHERE comment_id = ? AND user_id = ?",
            (comment_id, user_id),
        ).fetchone()
        if existing:
            conn.execute(
                "DELETE FROM comment_reactions WHERE comment_id = ? AND user_id = ?",
                (comment_id, user_id),
            )
            now_on = False
        else:
            conn.execute(
                "INSERT INTO comment_reactions (comment_id, user_id) VALUES (?, ?)",
                (comment_id, user_id),
            )
            now_on = True
        conn.commit()
        return now_on
    finally:
        conn.close()


def reacted_post_ids(user_id: int) -> set[int]:
    """사용자가 공감한 글 id 집합 (화면에서 버튼 상태 표시용)."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT post_id FROM post_reactions WHERE user_id = ?", (user_id,))
        return {r["post_id"] for r in rows.fetchall()}
    finally:
        conn.close()


def reacted_comment_ids(user_id: int, post_id: int) -> set[int]:
    """사용자가 공감한, 해당 글의 댓글 id 집합."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT cr.comment_id FROM comment_reactions cr "
            "JOIN comments c ON c.id = cr.comment_id "
            "WHERE cr.user_id = ? AND c.post_id = ?",
            (user_id, post_id),
        )
        return {r["comment_id"] for r in rows.fetchall()}
    finally:
        conn.close()


def received_reaction_count(user_id: int) -> int:
    """이 사용자가 쓴 글/댓글이 받은 공감 총합 (프로필 카르마)."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT "
            "(SELECT COUNT(*) FROM post_reactions pr JOIN posts p ON p.id = pr.post_id "
            "  WHERE p.author_id = ?) + "
            "(SELECT COUNT(*) FROM comment_reactions cr JOIN comments c ON c.id = cr.comment_id "
            "  WHERE c.author_id = ?) AS total",
            (user_id, user_id),
        ).fetchone()
        return row["total"] or 0
    finally:
        conn.close()
