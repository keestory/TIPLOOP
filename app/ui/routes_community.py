"""커뮤니티 라우트 — 피드·글쓰기·상세·댓글·프로필."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.service import community_service
from app.service.community_service import CommunityError
from app.types.models import User
from app.ui.deps import get_current_user

router = APIRouter()


def _render(request: Request, name: str, current_user: User | None, **ctx):
    return request.app.state.templates.TemplateResponse(
        request, name, {"current_user": current_user, **ctx}
    )


@router.get("/")
def feed(
    request: Request,
    category: str = "",
    school_level: str = "",
    region: str = "",
    user: User | None = Depends(get_current_user),
):
    posts = community_service.list_feed(category, school_level, region)
    return _render(
        request, "index.html", user, posts=posts,
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
        post, comments = community_service.get_post_with_comments(post_id)
    except CommunityError as exc:
        return _render(request, "not_found.html", user, message=str(exc))
    return _render(request, "post_detail.html", user, post=post, comments=comments)


@router.post("/posts/{post_id}/comments")
def add_comment(
    request: Request,
    post_id: int,
    body: str = Form(...),
    user: User | None = Depends(get_current_user),
):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    try:
        community_service.add_comment(post_id, user.id, body)
    except CommunityError:
        pass  # 빈 댓글 등은 조용히 무시하고 글로 되돌아간다
    return RedirectResponse(f"/posts/{post_id}", status_code=303)


@router.get("/users/{user_id}")
def profile(request: Request, user_id: int, user: User | None = Depends(get_current_user)):
    try:
        teacher, posts = community_service.get_profile(user_id)
    except CommunityError as exc:
        return _render(request, "not_found.html", user, message=str(exc))
    return _render(request, "profile.html", user, teacher=teacher, posts=posts)
