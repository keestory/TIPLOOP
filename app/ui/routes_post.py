"""연구 노트 라우트 — 작성·편집·상세와 이전 글 호환 액션."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.config.settings import (
    REFERENCE_IMAGE_MAX_BYTES,
    REFERENCE_MEDIA_BUCKETS,
    REFERENCE_MEDIA_MAX_FILES,
    REFERENCE_MEDIA_MAX_TOTAL_BYTES,
    REFERENCE_MEDIA_MAX_VIDEOS,
    REFERENCE_MEDIA_TYPES,
    REFERENCE_VIDEO_MAX_BYTES,
    REFERENCE_QUESTION_IDS,
    REFERENCE_QUICK_QUESTION_IDS,
    REFERENCE_REQUIRED_FINAL_ID,
    REFERENCE_TEMPLATE_VERSION,
    WRITE_TEMPLATES,
)
from app.service import research_service
from app.service.research_service import ResearchError
from app.types.models import User
from app.ui.deps import get_current_user
from app.ui.render import gate, render

router = APIRouter()


def _form_attachments(payload: str, auth_id: str) -> list[dict]:
    """오류 재렌더링에서도 정상 첨부만 안전하게 되살린다."""
    try:
        return research_service.attachment_dicts(
            research_service.parse_attachments(payload, auth_id)
        )
    except ResearchError:
        return []


def _media_context() -> dict:
    return {
        "media_types": REFERENCE_MEDIA_TYPES,
        "media_buckets": REFERENCE_MEDIA_BUCKETS,
        "media_accept": ",".join(REFERENCE_MEDIA_TYPES),
        "media_max_files": REFERENCE_MEDIA_MAX_FILES,
        "media_max_videos": REFERENCE_MEDIA_MAX_VIDEOS,
        "media_max_total_bytes": REFERENCE_MEDIA_MAX_TOTAL_BYTES,
        "image_max_bytes": REFERENCE_IMAGE_MAX_BYTES,
        "video_max_bytes": REFERENCE_VIDEO_MAX_BYTES,
    }


def _analysis_context() -> dict:
    return {
        "quick_question_ids": REFERENCE_QUICK_QUESTION_IDS,
        "required_final_id": REFERENCE_REQUIRED_FINAL_ID,
    }


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
        analysis_mode="quick", selected_question_ids=REFERENCE_QUICK_QUESTION_IDS,
        analysis_template_version=REFERENCE_TEMPLATE_VERSION, attachments=[],
        **_media_context(),
        **_analysis_context(),
    )


@router.post("/posts")
def create_post(
    request: Request,
    title: str = Form(...),
    body: str = Form(...),
    link_url: str = Form(""),
    analysis_mode: str = Form("quick"),
    selected_question_ids: list[str] = Form([]),
    attachments_json: str = Form("[]"),
    user: Optional[User] = Depends(get_current_user),
):
    if g := gate(user):
        return g
    try:
        post_id = research_service.create_note(
            user.id, title, body, link_url, analysis_mode,
            tuple(selected_question_ids), attachments_json, user.auth_id,
        )
    except ResearchError as exc:
        return render(
            request, "post_write.html", user, error=str(exc),
            category="reference", sections=WRITE_TEMPLATES["reference"],
            form={"title": title, "body": body, "link_url": link_url},
            section_values=research_service.section_values(body), editing=False,
            legacy_body=research_service.legacy_preamble(body),
            analysis_mode=analysis_mode,
            selected_question_ids=tuple(selected_question_ids),
            analysis_template_version=REFERENCE_TEMPLATE_VERSION,
            attachments=_form_attachments(attachments_json, user.auth_id),
            **_media_context(),
            **_analysis_context(),
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
        analysis_mode=post.analysis_mode or "full",
        selected_question_ids=post.selected_question_ids or REFERENCE_QUESTION_IDS,
        analysis_template_version=post.analysis_template_version or REFERENCE_TEMPLATE_VERSION,
        attachments=research_service.attachment_dicts(post.attachments),
        **_media_context(),
        **_analysis_context(),
    )


@router.post("/posts/{post_id}/edit")
def update_post(
    request: Request,
    post_id: int,
    title: str = Form(...),
    body: str = Form(...),
    link_url: str = Form(""),
    analysis_mode: str = Form("full"),
    selected_question_ids: list[str] = Form([]),
    attachments_json: str = Form("[]"),
    user: Optional[User] = Depends(get_current_user),
):
    if g := gate(user):
        return g
    try:
        research_service.update_note(
            post_id, user.id, title, body, link_url, analysis_mode,
            tuple(selected_question_ids), attachments_json, user.auth_id,
        )
    except ResearchError as exc:
        return render(
            request, "post_write.html", user, error=str(exc),
            category="reference", sections=WRITE_TEMPLATES["reference"],
            form={"title": title, "body": body, "link_url": link_url},
            section_values=research_service.section_values(body),
            legacy_body=research_service.legacy_preamble(body),
            editing=True, post_id=post_id,
            analysis_mode=analysis_mode,
            selected_question_ids=tuple(selected_question_ids),
            analysis_template_version=REFERENCE_TEMPLATE_VERSION,
            attachments=_form_attachments(attachments_json, user.auth_id),
            **_media_context(),
            **_analysis_context(),
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
        attachments=research_service.attachment_dicts(post.attachments),
        analysis_mode_label={
            "quick": "5분 빠른 분석",
            "focus": "질문 골라 분석",
            "full": "전체 분석",
        }.get(post.analysis_mode, "기존 분석"),
        saved=saved if saved in {"new", "edit"} else "",
    )
