"""개인 연구 노트 전환 전 커뮤니티 액션의 호환 라우트."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response

from app.service import community_service, reaction_service, research_service
from app.service.community_service import CommunityError
from app.service.research_service import ResearchError
from app.types.models import User
from app.ui.deps import get_current_user
from app.ui.render import back, gate

router = APIRouter()


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
    """영상 지점 코멘트. 개인 연구 노트에는 지원하지 않는다."""
    if user is None:
        return JSONResponse({"error": "로그인이 필요합니다."}, status_code=401)
    if not user.is_onboarded:
        return JSONResponse({"error": "온보딩이 필요합니다."}, status_code=403)
    try:
        post = research_service.get_owned_record(post_id, user.id)
    except ResearchError:
        return JSONResponse({"error": "글을 찾을 수 없습니다."}, status_code=404)
    if post.category == "reference":
        return JSONResponse(
            {"error": "연구 노트에는 댓글을 지원하지 않습니다."}, status_code=400
        )
    try:
        comment = community_service.add_media_comment(
            post_id, user.id, t, x, y, body
        )
    except CommunityError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    return JSONResponse({
        "id": comment.id,
        "t": comment.t_seconds,
        "x": comment.x,
        "y": comment.y,
        "body": comment.body,
        "author_name": comment.author_name,
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
    try:
        post = research_service.get_owned_record(post_id, user.id)
    except ResearchError:
        return RedirectResponse("/", status_code=303)
    if post.category == "reference":
        return RedirectResponse(f"/posts/{post_id}", status_code=303)
    parent = int(parent_id) if parent_id.isdigit() else None
    try:
        community_service.add_comment(post_id, user.id, body, parent)
    except CommunityError:
        pass
    return RedirectResponse(f"/posts/{post_id}", status_code=303)


@router.post("/posts/{post_id}/react")
def react_post(
    request: Request,
    post_id: int,
    user: Optional[User] = Depends(get_current_user),
):
    if g := gate(user):
        return g
    try:
        post = research_service.get_owned_record(post_id, user.id)
    except ResearchError:
        return RedirectResponse("/", status_code=303)
    if post.category == "reference":
        return RedirectResponse(f"/posts/{post_id}", status_code=303)
    reaction_service.toggle_post(post_id, user.id)
    return back(request, f"/posts/{post_id}")


@router.post("/comments/{comment_id}/react")
def react_comment(
    request: Request,
    comment_id: int,
    user: Optional[User] = Depends(get_current_user),
):
    """개인 노트 전환 후 레거시 댓글 반응 엔드포인트는 폐기했다."""
    if g := gate(user):
        return g
    return Response(status_code=410)


@router.post("/posts/{post_id}/helpful")
def helpful_post(
    request: Request,
    post_id: int,
    user: Optional[User] = Depends(get_current_user),
):
    if g := gate(user):
        return g
    try:
        post = research_service.get_owned_record(post_id, user.id)
    except ResearchError:
        return RedirectResponse("/", status_code=303)
    if post.category == "reference":
        return RedirectResponse(f"/posts/{post_id}", status_code=303)
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
        post = research_service.get_owned_record(post_id, user.id)
    except ResearchError:
        return RedirectResponse("/", status_code=303)
    if post.category == "reference":
        return RedirectResponse(f"/posts/{post_id}", status_code=303)
    try:
        community_service.add_review(post_id, user.id, body)
    except CommunityError:
        pass
    return RedirectResponse(f"/posts/{post_id}", status_code=303)
