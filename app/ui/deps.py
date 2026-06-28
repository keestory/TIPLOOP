"""요청 의존성 — 현재 로그인 사용자."""

from __future__ import annotations

from typing import Optional

from fastapi import Request

from app.config.settings import SESSION_COOKIE
from app.service import auth_service
from app.types.models import User


def get_current_user(request: Request) -> Optional[User]:
    """세션 쿠키로 현재 사용자를 찾는다. 비로그인이면 None."""
    token = request.cookies.get(SESSION_COOKIE)
    return auth_service.current_user(token)
