"""연구 노트 라우트 — 작성·편집·상세와 이전 글 호환 액션."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response

from app.config.settings import WRITE_TEMPLATES
from app.service import community_service, reaction_service, research_service
from app.service.community_service import CommunityError
from app.service.research_service import ResearchError
from app.types.models import User
from app.ui.deps import get_current_user
from app.ui.render import back, gate, render

router = APIRouter()


@router.get("/posts/new")
def new_post_type(
    request: Request, user: Optional[User] = Depends(get_current_user)
):
    """유형 선택을 건너뛰고 서비스 분석 폼으로 간다."""
    if g := gate(user):
        return g
    return RedirectResponse("/posts/new/write", status_code=303)


@router.get("/posts/new/write")
def new_post_write(
    request: Request,
    link_url: str = "",
    user: Optional[User] = Depends(get_current_user),
):
    """서비스 분석 템플릿 작성. 홈에서 넘긴 링크를 미리 채운다."""
    if g := gate(user):
        return g
    return render(
        request, "post_write.html", user,
        category="reference", sections=WRITE_TEMPLATES["reference"],
        form={"link_url": link_url.strip()}, section_values={}, editing=False,
    )


@router.post("/posts")
def create_post(
    request: Request,
    title: str = Form(...),
    body: str = Form(...),
    link_url: str = Form(""),
    user: Optional[User] = Depends(get_current_user),
):
    if g := gate(user):
        return g
    try:
        post_id = research_service.create_note(user.id, title, body, link_url)
    except ResearchError as exc:
        return render(
            request, "post_write.html", user, error=str(exc),
            category="reference", sections=WRITE_TEMPLATES["reference"],
            form={"title": title, "body": body, "link_url": link_url},
            section_values=research_service.section_values(body), editing=False,
            legacy_body=research_service.legacy_preamble(body),
        )
    return RedirectResponse(f"/posts/{post_id}?saved=new", status_code=303)


@router.get("/posts/{post_id}/edit")
def edit_post(
    request: Request,
    post_id: int,
    user: Optional[User] = Depends(get_current_user),
):
    if g := gate(user):
        return g
    try:
        post = research_service.get_note(post_id, user.id)
    except ResearchError as exc:
        return render(request, "not_found.html", user, status_code=404, message=str(exc))
    return render(
        request, "post_write.html", user,
        category="reference", sections=WRITE_TEMPLATES["reference"],
        form={"title": post.title, "body": post.body, "link_url": post.link_url or ""},
        section_values=research_service.section_values(post.body),
        legacy_body=research_service.legacy_preamble(post.body),
        editing=True, post_id=post.id,
    )


@router.post("/posts/{post_id}/edit")
def update_post(
    request: Request,
    post_id: int,
    title: str = Form(...),
    body: str = Form(...),
    link_url: str = Form(""),
    user: Optional[User] = Depends(get_current_user),
):
    if g := gate(user):
        return g
    try:
        research_service.update_note(post_id, user.id, title, body, link_url)
    except ResearchError as exc:
        return render(
            request, "post_write.html", user, error=str(exc),
            category="reference", sections=WRITE_TEMPLATES["reference"],
            form={"title": title, "body": body, "link_url": link_url},
            section_values=research_service.section_values(body),
            legacy_body=research_service.legacy_preamble(body),
            editing=True, post_id=post_id,
        )
    return RedirectResponse(f"/posts/{post_id}?saved=edit", status_code=303)


@router.get("/posts/{post_id}")
def post_detail(
    request: Request,
    post_id: int,
    saved: str = "",
    user: Optional[User] = Depends(get_current_user),
):
    if g := gate(user):
        return g
    try:
        post = research_service.get_note(post_id, user.id)
    except ResearchError as exc:
        return render(request, "not_found.html", user, status_code=404, message=str(exc))
    return render(
        request, "post_detail.html", user,
        post=post, progress=research_service.progress(post),
        groups=research_service.detail_groups(post.body),
        saved=saved if saved in {"new", "edit"} else "",
    )


@router.get("/posts/{post_id}/share")
def post_share(request: Request, post_id: int, user: Optional[User] = Depends(get_current_user)):
    """개인 노트의 공개 공유는 제공하지 않고 상세로 되돌린다."""
    if g := gate(user):
        return g
    try:
        research_service.get_note(post_id, user.id)
    except ResearchError as exc:
        return render(request, "not_found.html", user, status_code=404, message=str(exc))
    return RedirectResponse(f"/posts/{post_id}", status_code=303)


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
        post = research_service.get_owned_record(post_id, user.id)
    except ResearchError:
        return JSONResponse({"error": "글을 찾을 수 없습니다."}, status_code=404)
    if post.category == "reference":
        return JSONResponse({"error": "연구 노트에는 댓글을 지원하지 않습니다."}, status_code=400)
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
        pass  # 빈 댓글 등은 조용히 무시
    return RedirectResponse(f"/posts/{post_id}", status_code=303)


@router.post("/posts/{post_id}/react")
def react_post(request: Request, post_id: int, user: Optional[User] = Depends(get_current_user)):
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
def react_comment(request: Request, comment_id: int, user: Optional[User] = Depends(get_current_user)):
    """개인 노트 전환 후 레거시 댓글 반응 엔드포인트는 폐기했다."""
    if g := gate(user):
        return g
    return Response(status_code=410)


@router.post("/posts/{post_id}/helpful")
def helpful_post(request: Request, post_id: int, user: Optional[User] = Depends(get_current_user)):
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
        pass  # 빈 후기 등은 조용히 무시
    return RedirectResponse(f"/posts/{post_id}", status_code=303)
