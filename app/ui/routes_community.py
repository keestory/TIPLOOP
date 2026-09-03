"""개인 서비스 노트 라우트 — 홈·보관함·내 계정.

공개 피드나 사용자 간 상호작용은 제공하지 않으며, 로그인한 본인의 데이터만
조회한다. 과거 URL은 본인 계정 화면으로만 제한하거나 410으로 종료한다.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, Response

from app.service import (
    auth_service,
    notification_service,
    research_service,
)
from app.types.models import User
from app.ui.deps import get_current_user
from app.ui.render import gate, render

router = APIRouter()

def _nav_unread(user: Optional[User]) -> int:
    """탭바의 알림 배지용 안 읽은 알림 수."""
    return notification_service.unread_count(user.id if user else None)


@router.get("/")
def feed(
    request: Request,
    user: Optional[User] = Depends(get_current_user),
):
    if g := gate(user):
        return g
    dashboard = research_service.dashboard(user.id)
    return render(
        request, "index.html", user,
        dashboard=dashboard,
        nav_unread=0,
    )


@router.post("/checklist/dismiss")
def dismiss_checklist(request: Request, user: Optional[User] = Depends(get_current_user)):
    """홈 시작 체크리스트 닫기 — 다시 뜨지 않는다."""
    if user is not None:
        auth_service.dismiss_checklist(user.id)
    return RedirectResponse("/", status_code=303)


@router.get("/explore")
def explore(
    request: Request,
    q: str = "",
    focus: str = "",
    user: Optional[User] = Depends(get_current_user),
):
    if g := gate(user):
        return g
    query = q.strip()
    active_focus = "applied" if focus == "applied" else ""
    notes = (
        research_service.list_actionable_notes(user.id, query)
        if active_focus
        else research_service.list_notes(user.id, query)
    )
    results = research_service.present_notes(notes)
    return render(
        request, "explore.html", user,
        q=query, focus=active_focus, results=results, nav_unread=0,
    )


@router.get("/notifications")
def notifications_page(request: Request, user: Optional[User] = Depends(get_current_user)):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    items = notification_service.list_recent(user.id)
    return render(request, "notifications.html", user,
                  items=items, nav_unread=_nav_unread(user))


@router.get("/digest")
def weekly_digest(request: Request, user: Optional[User] = Depends(get_current_user)):
    """이전 공개 다이제스트는 개인 노트 전환 후 홈으로 모은다."""
    if g := gate(user):
        return g
    return RedirectResponse("/", status_code=303)


@router.post("/notifications/read")
def notifications_read(request: Request, user: Optional[User] = Depends(get_current_user)):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    notification_service.mark_all_read(user.id)
    return RedirectResponse("/notifications", status_code=303)


@router.post("/users/{user_id}/follow")
def follow_user(request: Request, user_id: int, user: Optional[User] = Depends(get_current_user)):
    """개인 노트 전환 후 임의 사용자 팔로우 동작은 폐기했다."""
    if g := gate(user):
        return g
    return Response(status_code=410)


@router.get("/users/{user_id}")
def profile(request: Request, user_id: int, user: Optional[User] = Depends(get_current_user)):
    if g := gate(user):
        return g
    if user_id != user.id:
        return render(
            request, "not_found.html", user,
            status_code=404, message="계정을 찾을 수 없습니다.",
        )
    member = user
    stats = research_service.dashboard(user.id)
    return render(
        request, "profile.html", user, teacher=member,
        stats=stats, nav_unread=0,
    )


@router.get("/users/{user_id}/share")
def profile_share(request: Request, user_id: int, user: Optional[User] = Depends(get_current_user)):
    """개인 연구 노트 전환 후 공개 프로필 공유는 제공하지 않는다."""
    if g := gate(user):
        return g
    if user_id != user.id:
        return render(
            request, "not_found.html", user,
            status_code=404, message="계정을 찾을 수 없습니다.",
        )
    return RedirectResponse(f"/users/{user.id}", status_code=303)
