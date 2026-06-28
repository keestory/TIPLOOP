"""커뮤니티 라우트 — 피드·글쓰기·상세·댓글·공감·프로필."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.service import community_service, reaction_service
from app.service.community_service import CommunityError
from app.types.models import User
from app.ui.deps import get_current_user

router = APIRouter()

FEED_SORTS = {"new": "최신", "top": "공감", "buzz": "화제"}


def _render(request: Request, name: str, current_user: User | None, **ctx):
    return request.app.state.templates.TemplateResponse(
        request, name, {"current_user": current_user, **ctx}
    )


def _back(request: Request, fallback: str) -> RedirectResponse:
    """같은 출처의 referer로 되돌아간다. 없으면 fallback."""
    referer = request.headers.get("referer", "")
    target = referer if referer.startswith(str(request.base_url)) else fallback
    return RedirectResponse(target, status_code=303)


@router.get("/")
def feed(
    request: Request,
    sort: str = "new",
    category: str = "",
    school_level: str = "",
    region: str = "",
    user: User | None = Depends(get_current_user),
):
    sort = sort if sort in FEED_SORTS else "new"
    posts = community_service.list_feed(category, school_level, region, sort)
    reacted = reaction_service.viewer_post_reactions(user.id if user else None)
    return _render(
        request, "index.html", user, posts=posts, reacted=reacted,
        sorts=FEED_SORTS, sort=sort,
        active={"category": category, "school_level": school_level, "region": region},
    )


@router.get("/posts/new")
def new_post_form(request: Request, user: User | None = Depends(get_current_user)):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    return _render(request, "post_new.html", user)


@router.post("/posts")
def create_post(
    request: Request,
    category: str = Form(...),
    title: str = Form(...),
    body: str = Form(...),
    event_at: str = Form(""),
    location: str = Form(""),
    online_url: str = Form(""),
    user: User | None = Depends(get_current_user),
):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    try:
        post_id = community_service.create_post(
            user.id, category, title, body, event_at, location, online_url
        )
    except CommunityError as exc:
        return _render(request, "post_new.html", user, error=str(exc), form={
            "category": category, "title": title, "body": body,
            "event_at": event_at, "location": location, "online_url": online_url,
        })
    return RedirectResponse(f"/posts/{post_id}", status_code=303)


@router.get("/posts/{post_id}")
def post_detail(request: Request, post_id: int, user: User | None = Depends(get_current_user)):
    try:
        post, threads = community_service.get_post_with_threads(post_id)
    except CommunityError as exc:
        return _render(request, "not_found.html", user, message=str(exc))
    reacted = reaction_service.viewer_post_reactions(user.id if user else None)
    reacted_comments = reaction_service.viewer_comment_reactions(
        user.id if user else None, post_id
    )
    return _render(
        request, "post_detail.html", user, post=post, threads=threads,
        reacted=reacted, reacted_comments=reacted_comments,
    )


@router.post("/posts/{post_id}/comments")
def add_comment(
    request: Request,
    post_id: int,
    body: str = Form(...),
    parent_id: str = Form(""),
    user: User | None = Depends(get_current_user),
):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    parent = int(parent_id) if parent_id.isdigit() else None
    try:
        community_service.add_comment(post_id, user.id, body, parent)
    except CommunityError:
        pass  # 빈 댓글 등은 조용히 무시
    return RedirectResponse(f"/posts/{post_id}", status_code=303)


@router.post("/posts/{post_id}/react")
def react_post(request: Request, post_id: int, user: User | None = Depends(get_current_user)):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    reaction_service.toggle_post(post_id, user.id)
    return _back(request, f"/posts/{post_id}")


@router.post("/comments/{comment_id}/react")
def react_comment(request: Request, comment_id: int, user: User | None = Depends(get_current_user)):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    post_id = reaction_service.toggle_comment(comment_id, user.id)
    return _back(request, f"/posts/{post_id}" if post_id else "/")


@router.get("/users/{user_id}")
def profile(request: Request, user_id: int, user: User | None = Depends(get_current_user)):
    try:
        teacher, posts, received = community_service.get_profile(user_id)
    except CommunityError as exc:
        return _render(request, "not_found.html", user, message=str(exc))
    return _render(
        request, "profile.html", user, teacher=teacher, posts=posts, received=received
    )
