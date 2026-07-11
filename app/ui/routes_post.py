"""글 라우트 — 글쓰기(유형·템플릿)·상세·댓글·공감·후기·영상 코멘트."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.config.settings import CATEGORIES, WRITE_TEMPLATES
from app.service import community_service, crew_service, reaction_service
from app.service.community_service import CommunityError
from app.types.models import User
from app.ui.deps import get_current_user
from app.ui.render import back, gate, render

router = APIRouter()


@router.get("/posts/new")
def new_post_type(
    request: Request, category: str = "", user: Optional[User] = Depends(get_current_user)
):
    """글쓰기 1단계 — 유형 선택."""
    if g := gate(user):
        return g
    return render(request, "post_type.html", user, prefill_category=category)


@router.get("/posts/new/write")
def new_post_write(
    request: Request,
    category: str = "",
    from_entry: int = 0,
    user: Optional[User] = Depends(get_current_user),
):
    """글쓰기 2단계 — 유형별 템플릿 작성. from_entry면 내 크루 조각을 채워서 시작."""
    if g := gate(user):
        return g
    if category not in CATEGORIES:
        return RedirectResponse("/posts/new", status_code=303)
    prefill = ""
    if from_entry:
        entry = crew_service.my_entry(from_entry, user.id)
        prefill = entry.body if entry else ""
    return render(
        request, "post_write.html", user,
        category=category, sections=WRITE_TEMPLATES.get(category, []), prefill=prefill,
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
    if g := gate(user):
        return g
    try:
        post_id = community_service.create_post(
            user.id, category, title, body, link_url, image_url, video_url
        )
    except CommunityError as exc:
        cat = category if category in CATEGORIES else "tip"
        return render(
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
        return render(request, "not_found.html", user, message=str(exc))
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
    return render(
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
    if g := gate(user):
        return g
    parent = int(parent_id) if parent_id.isdigit() else None
    try:
        community_service.add_comment(post_id, user.id, body, parent)
    except CommunityError:
        pass  # 빈 댓글 등은 조용히 무시
    return RedirectResponse(f"/posts/{post_id}", status_code=303)


@router.post("/posts/{post_id}/react")
def react_post(request: Request, post_id: int, user: Optional[User] = Depends(get_current_user)):
    if g := gate(user):
        return g
    reaction_service.toggle_post(post_id, user.id)
    return back(request, f"/posts/{post_id}")


@router.post("/comments/{comment_id}/react")
def react_comment(request: Request, comment_id: int, user: Optional[User] = Depends(get_current_user)):
    if g := gate(user):
        return g
    post_id = reaction_service.toggle_comment(comment_id, user.id)
    return back(request, f"/posts/{post_id}" if post_id else "/")


@router.post("/posts/{post_id}/helpful")
def helpful_post(request: Request, post_id: int, user: Optional[User] = Depends(get_current_user)):
    if g := gate(user):
        return g
    reaction_service.toggle_helpful(post_id, user.id)
    return back(request, f"/posts/{post_id}")


@router.post("/posts/{post_id}/reviews")
def add_review(
    request: Request,
    post_id: int,
    body: str = Form(...),
    user: Optional[User] = Depends(get_current_user),
):
    if g := gate(user):
        return g
    try:
        community_service.add_review(post_id, user.id, body)
    except CommunityError:
        pass  # 빈 후기 등은 조용히 무시
    return RedirectResponse(f"/posts/{post_id}", status_code=303)
