"""연구 노트의 취소 가능한 secret-link 공유 화면."""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from app.config.settings import SITE_URL, SUPABASE_URL
from app.service import research_service, research_share_service
from app.service.research_service import ResearchError
from app.service.research_share_service import ResearchShareError
from app.types.models import User
from app.ui.deps import get_current_user
from app.ui.render import gate, render

router = APIRouter()

_SHARE_TOKEN_WITH_TEXT_RE = re.compile(
    r"^(?P<token>[A-Za-z0-9_-]{43})(?:\s+.+)?$", re.DOTALL
)


def _share_token_from_path(value: str) -> str:
    """iOS 공유 시트가 URL 뒤에 본문을 붙인 옛 링크를 정규화한다.

    비밀 토큰 자체는 기존 43자 형식을 그대로 요구하고, 뒤에 공백으로
    구분된 공유 문구가 있는 경우에만 그 문구를 버린다.
    """
    match = _SHARE_TOKEN_WITH_TEXT_RE.fullmatch((value or "").strip())
    return match.group("token") if match else value


def _is_same_origin(request: Request) -> bool:
    """세션 쿠키를 쓰는 공유 변경 요청은 앱 화면에서 온 POST만 허용한다."""
    source = request.headers.get("origin", "")
    if not source:
        referer = urlparse(request.headers.get("referer", ""))
        if referer.scheme and referer.netloc:
            source = f"{referer.scheme}://{referer.netloc}"
    if not source:
        return False
    parsed = urlparse(source)
    request_origin = f"{request.url.scheme}://{request.url.netloc}"
    allowed = {request_origin.rstrip("/"), SITE_URL.rstrip("/")}
    return parsed.scheme in {"http", "https"} and source.rstrip("/") in allowed


def _no_store(response):
    response.headers["Cache-Control"] = "private, no-store, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response


@router.get("/posts/{post_id}/share")
def post_share(
    request: Request,
    post_id: int,
    user: Optional[User] = Depends(get_current_user),
):
    """소유자가 링크 공개 범위를 확인하고 생성·중지하는 화면."""
    if g := gate(user):
        return g
    try:
        post = research_service.get_note(post_id, user.id)
    except ResearchError as exc:
        return render(request, "not_found.html", user, status_code=404, message=str(exc))
    return _no_store(
        render(
            request,
            "research_share.html",
            user,
            post=post,
            active_share=research_share_service.status(post_id, user.id),
            share_url="",
        )
    )


@router.post("/posts/{post_id}/share")
def create_post_share(
    request: Request,
    post_id: int,
    include_media: bool = Form(False),
    user: Optional[User] = Depends(get_current_user),
):
    if g := gate(user):
        return g
    if not _is_same_origin(request):
        return PlainTextResponse("허용되지 않은 공유 요청입니다.", status_code=403)
    try:
        post = research_service.get_note(post_id, user.id)
        include_media = include_media and bool(post.attachments)
        token = research_share_service.create_link(
            post_id, user.id, user.auth_id, include_media
        )
    except (ResearchError, ResearchShareError) as exc:
        return render(request, "not_found.html", user, status_code=404, message=str(exc))
    share_url = f"{SITE_URL.rstrip('/')}/s/{token}"
    return _no_store(
        render(
            request,
            "research_share.html",
            user,
            post=post,
            active_share={"include_media": include_media},
            share_url=share_url,
        )
    )


@router.post("/posts/{post_id}/share/revoke")
def revoke_post_share(
    request: Request,
    post_id: int,
    user: Optional[User] = Depends(get_current_user),
):
    if g := gate(user):
        return g
    if not _is_same_origin(request):
        return PlainTextResponse("허용되지 않은 공유 요청입니다.", status_code=403)
    try:
        research_share_service.revoke(post_id, user.id)
    except ResearchShareError:
        pass
    return RedirectResponse(f"/posts/{post_id}/share", status_code=303)


@router.get("/s/{token}", name="shared_research_note")
def shared_research_note(request: Request, token: str):
    """링크 보유자가 로그인 없이 보는 공개 연구 노트."""
    try:
        post, media_tokens = research_share_service.shared_note(
            _share_token_from_path(token)
        )
    except ResearchShareError as exc:
        response = render(
            request,
            "shared_not_found.html",
            None,
            status_code=404,
            message=str(exc),
        )
    else:
        attachments = research_service.attachment_dicts(post.attachments)
        response = render(
            request,
            "shared_research.html",
            None,
            post=post,
            progress=research_service.progress(post),
            groups=research_service.detail_groups(post.body),
            attachments=attachments,
            media_tokens=media_tokens,
            media_endpoint=(
                f"{SUPABASE_URL.rstrip('/')}/functions/v1/shared-media"
                if attachments and SUPABASE_URL
                else ""
            ),
        )
    _no_store(response)
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response
