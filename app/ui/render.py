"""라우트 공통 헬퍼 — 템플릿 렌더링, referer 복귀, 쓰기 액션 가드.

여러 라우트 모듈(routes_community, routes_post 등)이 공유한다.
"""

from __future__ import annotations

from typing import Optional

from fastapi import Request
from fastapi.responses import RedirectResponse

from app.types.models import User


def render(
    request: Request,
    name: str,
    current_user: Optional[User],
    status_code: int = 200,
    **ctx,
):
    return request.app.state.templates.TemplateResponse(
        request,
        name,
        {"current_user": current_user, **ctx},
        status_code=status_code,
    )


def back(request: Request, fallback: str) -> RedirectResponse:
    """같은 출처의 referer로 되돌아간다. 없으면 fallback."""
    referer = request.headers.get("referer", "")
    target = referer if referer.startswith(str(request.base_url)) else fallback
    return RedirectResponse(target, status_code=303)


def gate(user: Optional[User]) -> Optional[RedirectResponse]:
    """쓰기 액션 가드 — 비로그인은 로그인, 온보딩 미완료는 온보딩으로."""
    if user is None:
        return RedirectResponse("/login", status_code=303)
    if not user.is_onboarded:
        return RedirectResponse("/onboarding", status_code=303)
    return None
