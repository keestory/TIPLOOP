"""커뮤니티 라우트 — 피드·글쓰기·상세·댓글·공감·프로필."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.config.settings import CATEGORIES, WRITE_TEMPLATES
from app.service import (
    auth_service,
    community_service,
    follow_service,
    notification_service,
    reaction_service,
)
from app.service.community_service import CommunityError
from app.types.models import User
from app.ui.deps import get_current_user

router = APIRouter()

FEED_SORTS = {"new": "최신", "top": "공감", "buzz": "화제"}


def _nav_unread(user: Optional[User]) -> int:
    """탭바의 알림 배지용 안 읽은 알림 수."""
    return notification_service.unread_count(user.id if user else None)


def _render(request: Request, name: str, current_user: Optional[User], **ctx):
    return request.app.state.templates.TemplateResponse(
        request, name, {"current_user": current_user, **ctx}
    )


def _back(request: Request, fallback: str) -> RedirectResponse:
    """같은 출처의 referer로 되돌아간다. 없으면 fallback."""
    referer = request.headers.get("referer", "")
    target = referer if referer.startswith(str(request.base_url)) else fallback
    return RedirectResponse(target, status_code=303)


def _gate(user: Optional[User]) -> Optional[RedirectResponse]:
    """쓰기 액션 가드 — 비로그인은 로그인, 온보딩 미완료는 온보딩으로."""
    if user is None:
        return RedirectResponse("/login", status_code=303)
    if not user.is_onboarded:
        return RedirectResponse("/onboarding", status_code=303)
    return None


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
    return _render(
        request, "index.html", user,
        featured=featured, waiting=waiting, rest=rest,
        sort=sort, active_category=category, nav_unread=_nav_unread(user),
        show_tour=show_tour, checklist=community_service.onboarding_checklist(user),
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
        return _render(request, "explore.html", user, q=query, results=results,
                       popular=None, nav_unread=unread)
    popular = community_service.list_feed(sort="top")[:6]
    return _render(request, "explore.html", user, q="", results=None,
                   popular=popular, nav_unread=unread)


@router.get("/notifications")
def notifications_page(request: Request, user: Optional[User] = Depends(get_current_user)):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    items = notification_service.list_recent(user.id)
    return _render(request, "notifications.html", user,
                   items=items, nav_unread=_nav_unread(user))


@router.post("/notifications/read")
def notifications_read(request: Request, user: Optional[User] = Depends(get_current_user)):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    notification_service.mark_all_read(user.id)
    return RedirectResponse("/notifications", status_code=303)


@router.post("/users/{user_id}/follow")
def follow_user(request: Request, user_id: int, user: Optional[User] = Depends(get_current_user)):
    if gate := _gate(user):
        return gate
    follow_service.toggle(user.id, user_id)
    return _back(request, f"/users/{user_id}")


@router.get("/posts/new")
def new_post_type(
    request: Request, category: str = "", user: Optional[User] = Depends(get_current_user)
):
    """글쓰기 1단계 — 유형 선택."""
    if gate := _gate(user):
        return gate
    return _render(request, "post_type.html", user, prefill_category=category)


@router.get("/posts/new/write")
def new_post_write(
    request: Request, category: str = "", user: Optional[User] = Depends(get_current_user)
):
    """글쓰기 2단계 — 유형별 템플릿 작성."""
    if gate := _gate(user):
        return gate
    if category not in CATEGORIES:
        return RedirectResponse("/posts/new", status_code=303)
    return _render(
        request, "post_write.html", user,
        category=category, sections=WRITE_TEMPLATES.get(category, []),
    )


@router.post("/posts")
def create_post(
    request: Request,
    category: str = Form(...),
    title: str = Form(...),
    body: str = Form(...),
    link_url: str = Form(""),
    image_url: str = Form(""),
    video_url: str = Form(""),
    user: Optional[User] = Depends(get_current_user),
):
    if gate := _gate(user):
        return gate
    try:
        post_id = community_service.create_post(
            user.id, category, title, body, link_url, image_url, video_url
        )
    except CommunityError as exc:
        cat = category if category in CATEGORIES else "tip"
        return _render(
            request, "post_write.html", user, error=str(exc),
            category=cat, sections=WRITE_TEMPLATES.get(cat, []),
            form={"title": title, "body": body, "link_url": link_url},
        )
    return RedirectResponse(f"/posts/{post_id}", status_code=303)


@router.get("/posts/{post_id}")
def post_detail(request: Request, post_id: int, user: Optional[User] = Depends(get_current_user)):
    try:
        post, threads = community_service.get_post_with_threads(post_id)
    except CommunityError as exc:
        return _render(request, "not_found.html", user, message=str(exc))
    reacted = reaction_service.viewer_post_reactions(user.id if user else None)
    helped = reaction_service.viewer_helpful(user.id if user else None)
    reacted_comments = reaction_service.viewer_comment_reactions(
        user.id if user else None, post_id
    )
    reviews = community_service.list_reviews(post_id)
    mcs = community_service.list_media_comments(post_id) if post.video_url else []
    media = [
        {"id": m.id, "t": m.t_seconds, "x": m.x, "y": m.y,
         "body": m.body, "author_name": m.author_name}
        for m in mcs
    ]
    return _render(
        request, "post_detail.html", user, post=post, threads=threads,
        reacted=reacted, helped=helped, reacted_comments=reacted_comments,
        reviews=reviews, media_comments=media,
    )


@router.post("/posts/{post_id}/media-comments")
def add_media_comment(
    request: Request,
    post_id: int,
    t: float = Form(...),
    x: float = Form(...),
    y: float = Form(...),
    body: str = Form(...),
    user: Optional[User] = Depends(get_current_user),
):
    """영상 지점 코멘트 — 비동기(fetch)로 추가하고 만든 코멘트를 JSON으로 돌려준다."""
    if user is None:
        return JSONResponse({"error": "로그인이 필요합니다."}, status_code=401)
    if not user.is_onboarded:
        return JSONResponse({"error": "온보딩이 필요합니다."}, status_code=403)
    try:
        mc = community_service.add_media_comment(post_id, user.id, t, x, y, body)
    except CommunityError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    return JSONResponse({
        "id": mc.id, "t": mc.t_seconds, "x": mc.x, "y": mc.y,
        "body": mc.body, "author_name": mc.author_name,
    })


@router.post("/posts/{post_id}/comments")
def add_comment(
    request: Request,
    post_id: int,
    body: str = Form(...),
    parent_id: str = Form(""),
    user: Optional[User] = Depends(get_current_user),
):
    if gate := _gate(user):
        return gate
    parent = int(parent_id) if parent_id.isdigit() else None
    try:
        community_service.add_comment(post_id, user.id, body, parent)
    except CommunityError:
        pass  # 빈 댓글 등은 조용히 무시
    return RedirectResponse(f"/posts/{post_id}", status_code=303)


@router.post("/posts/{post_id}/react")
def react_post(request: Request, post_id: int, user: Optional[User] = Depends(get_current_user)):
    if gate := _gate(user):
        return gate
    reaction_service.toggle_post(post_id, user.id)
    return _back(request, f"/posts/{post_id}")


@router.post("/comments/{comment_id}/react")
def react_comment(request: Request, comment_id: int, user: Optional[User] = Depends(get_current_user)):
    if gate := _gate(user):
        return gate
    post_id = reaction_service.toggle_comment(comment_id, user.id)
    return _back(request, f"/posts/{post_id}" if post_id else "/")


@router.post("/posts/{post_id}/helpful")
def helpful_post(request: Request, post_id: int, user: Optional[User] = Depends(get_current_user)):
    if gate := _gate(user):
        return gate
    reaction_service.toggle_helpful(post_id, user.id)
    return _back(request, f"/posts/{post_id}")


@router.post("/posts/{post_id}/reviews")
def add_review(
    request: Request,
    post_id: int,
    body: str = Form(...),
    user: Optional[User] = Depends(get_current_user),
):
    if gate := _gate(user):
        return gate
    try:
        community_service.add_review(post_id, user.id, body)
    except CommunityError:
        pass  # 빈 후기 등은 조용히 무시
    return RedirectResponse(f"/posts/{post_id}", status_code=303)


@router.get("/users/{user_id}")
def profile(request: Request, user_id: int, user: Optional[User] = Depends(get_current_user)):
    try:
        member, posts, stats = community_service.get_profile(user_id)
    except CommunityError as exc:
        return _render(request, "not_found.html", user, message=str(exc))
    heatmap = community_service.contribution_heatmap(posts)
    follow = follow_service.status(user.id if user else None, user_id)
    return _render(
        request, "profile.html", user, teacher=member, posts=posts,
        stats=stats, heatmap=heatmap, follow=follow, nav_unread=_nav_unread(user),
    )
