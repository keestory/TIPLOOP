"""알림 저장소 (Supabase Postgres).

내 글에 달린 후기·도움·댓글, 팔로우, 구독 주제의 새 글을 한곳에 모은다.
조회 시 행동한 사람 이름과 글 제목을 함께 가져온다(join).
"""

from __future__ import annotations

from app.repo.database import get_connection
from app.types.models import Notification

_SELECT = """
SELECT n.id, n.user_id, n.actor_id, n.kind,
       to_char(n.created_at, 'YYYY-MM-DD HH24:MI:SS') AS created_at,
       n.post_id, n.topic, n.crew_id,
       to_char(n.read_at, 'YYYY-MM-DD HH24:MI:SS') AS read_at,
       a.name AS actor_name, p.title AS post_title
FROM notifications n
LEFT JOIN members a ON a.id = n.actor_id
LEFT JOIN posts p   ON p.id = n.post_id
"""


def _to_notification(row: dict) -> Notification:
    return Notification(
        id=row["id"],
        user_id=row["user_id"],
        kind=row["kind"],
        created_at=row["created_at"],
        actor_id=row["actor_id"],
        post_id=row["post_id"],
        topic=row["topic"],
        crew_id=row["crew_id"],
        read_at=row["read_at"],
        actor_name=row["actor_name"],
        post_title=row["post_title"],
    )


def create(
    user_id: int,
    kind: str,
    actor_id: int | None = None,
    post_id: int | None = None,
    topic: str | None = None,
    crew_id: int | None = None,
) -> None:
    """알림 한 건을 남긴다. 자기 자신에게는 남기지 않는다."""
    if actor_id is not None and actor_id == user_id:
        return
    sql = (
        "INSERT INTO notifications (user_id, actor_id, kind, post_id, topic, crew_id) "
        "VALUES (%s, %s, %s, %s, %s, %s)"
    )
    with get_connection() as conn:
        conn.execute(sql, (user_id, actor_id, kind, post_id, topic, crew_id))


def list_for(user_id: int, limit: int = 40) -> list[Notification]:
    with get_connection() as conn:
        rows = conn.execute(
            _SELECT + " WHERE n.user_id = %s ORDER BY n.created_at DESC, n.id DESC LIMIT %s",
            (user_id, limit),
        ).fetchall()
        return [_to_notification(r) for r in rows]


def crew_nudge_sent_this_week(user_id: int, crew_id: int) -> bool:
    """이번 주(월요일 시작)에 이미 마감 넛지를 보냈는지 — 크론 중복 방지."""
    sql = (
        "SELECT 1 FROM notifications WHERE user_id = %s AND crew_id = %s "
        "AND kind = 'crew_nudge' AND created_at >= date_trunc('week', now())"
    )
    with get_connection() as conn:
        return conn.execute(sql, (user_id, crew_id)).fetchone() is not None


def unread_count(user_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM notifications WHERE user_id = %s AND read_at IS NULL",
            (user_id,),
        ).fetchone()
        return row["n"]


def mark_all_read(user_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE notifications SET read_at = now() WHERE user_id = %s AND read_at IS NULL",
            (user_id,),
        )
