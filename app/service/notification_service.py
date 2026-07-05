"""알림 도메인 로직 — 목록 조회(상대 시간 포함), 안 읽음 수, 모두 읽음."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from app.repo import notifications
from app.types.models import Notification


def _ago(created_at: str) -> str:
    """'5분 전' 같은 상대 시간. DB 시각은 UTC(to_char)라 utcnow와 비교."""
    try:
        t = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return ""
    secs = (datetime.utcnow() - t).total_seconds()
    if secs < 60:
        return "방금"
    minutes = secs // 60
    if minutes < 60:
        return f"{int(minutes)}분 전"
    hours = minutes // 60
    if hours < 24:
        return f"{int(hours)}시간 전"
    days = hours // 24
    if days < 7:
        return f"{int(days)}일 전"
    return f"{int(days // 7)}주 전"


def list_recent(user_id: int, limit: int = 40) -> list[Notification]:
    """최근 알림에 상대 시간을 채워 돌려준다."""
    return [
        replace(n, ago=_ago(n.created_at))
        for n in notifications.list_for(user_id, limit)
    ]


def unread_count(user_id: int | None) -> int:
    if user_id is None:
        return 0
    return notifications.unread_count(user_id)


def mark_all_read(user_id: int) -> None:
    notifications.mark_all_read(user_id)
