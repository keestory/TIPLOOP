"""커뮤니티 라우트 — 홈 피드·탐색·알림·다이제스트·팔로우·프로필.

글 작성·상세·댓글·반응은 routes_post.py 참고.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app.service import (
    auth_service,
    community_service,
    crew_service,
    follow_service,
    notification_service,
    share_service,
)
from app.service.community_service import CommunityError
from app.types.models import User
from app.ui.deps import get_current_user
from app.ui.render import back, gate, render

router = APIRouter()

FEED_SORTS = {"new": "최신", "top": "공감", "buzz": "화제"}


def _nav_unread(user: Optional[User]) -> int:
    """탭바의 알림 배지용 안 읽은 알림 수."""
    return notification_service.unread_count(user.id if user else None)


@router.get("/")
def feed(
    request: Request,
    sort: str = "new",
    category: str = "",
    user: Optional[User] = Depends(get_current_user),
):
    sort = sort if sort in FEED_SORTS else "new"
    posts = community_service.list_feed(category, sort=sort)
    featured, waiting, rest = community_service.home_feed(posts)
    show_tour = bool(user and user.is_onboarded and not user.has_seen_tour)
    return render(
        request, "index.html", user,
        featured=featured, waiting=waiting, rest=rest,
        sort=sort, active_category=category, nav_unread=_nav_unread(user),
        show_tour=show_tour, checklist=community_service.onboarding_checklist(user),
        my_crews=crew_service.my_crews(user.id) if (user and user.is_onboarded) else [],
    )


@router.post("/checklist/dismiss")
def dismiss_checklist(request: Request, user: Optional[User] = Depends(get_current_user)):
    """홈 시작 체크리스트 닫기 — 다시 뜨지 않는다."""
    if user is not None:
        auth_service.dismiss_checklist(user.id)
    return RedirectResponse("/", status_code=303)


@router.get("/explore")
def explore(request: Request, q: str = "", user: Optional[User] = Depends(get_current_user)):
    query = q.strip()
    unread = _nav_unread(user)
    if query:
        results = community_service.list_feed(search=query, sort="new")
        return render(request, "explore.html", user, q=query, results=results,
                      popular=None, nav_unread=unread)
    popular = community_service.list_feed(sort="top")[:6]
    return render(request, "explore.html", user, q="", results=None,
                  popular=popular, nav_unread=unread)


@router.get("/notifications")
def notifications_page(request: Request, user: Optional[User] = Depends(get_current_user)):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    items = notification_service.list_recent(user.id)
    return render(request, "notifications.html", user,
                  items=items, nav_unread=_nav_unread(user))


@router.get("/digest")
def weekly_digest(request: Request, user: Optional[User] = Depends(get_current_user)):
    """이번 주 티핑 (6a) — 가장 도움된 팁·팔로우 새 글·답변 대기·내 글 받은 후기."""
    if user is None:
        return RedirectResponse("/login", status_code=303)
    if not user.is_onboarded:
        return RedirectResponse("/onboarding", status_code=303)
    return render(request, "digest.html", user,
                  digest=community_service.weekly_digest(user), nav_unread=_nav_unread(user))


@router.post("/notifications/read")
def notifications_read(request: Request, user: Optional[User] = Depends(get_current_user)):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    notification_service.mark_all_read(user.id)
    return RedirectResponse("/notifications", status_code=303)


@router.post("/users/{user_id}/follow")
def follow_user(request: Request, user_id: int, user: Optional[User] = Depends(get_current_user)):
    if g := gate(user):
        return g
    follow_service.toggle(user.id, user_id)
    return back(request, f"/users/{user_id}")


@router.get("/users/{user_id}")
def profile(request: Request, user_id: int, user: Optional[User] = Depends(get_current_user)):
    try:
        member, posts, stats = community_service.get_profile(user_id)
    except CommunityError as exc:
        return render(request, "not_found.html", user, message=str(exc))
    heatmap = community_service.contribution_heatmap(posts)
    follow = follow_service.status(user.id if user else None, user_id)
    return render(
        request, "profile.html", user, teacher=member, posts=posts,
        stats=stats, heatmap=heatmap, follow=follow, nav_unread=_nav_unread(user),
    )


@router.get("/users/{user_id}/share")
def profile_share(request: Request, user_id: int, user: Optional[User] = Depends(get_current_user)):
    """인스타 스토리용 공유 카드 — 내가 도움을 준 사람 수를 자랑."""
    try:
        member, _, stats = community_service.get_profile(user_id)
    except CommunityError as exc:
        return render(request, "not_found.html", user, message=str(exc))
    spec = share_service.profile_card(member, stats["helpful"])
    return render(request, "share.html", user, spec=spec)
