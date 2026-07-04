"""인증 라우트 — 구글/카카오 소셜 로그인, 세션, 온보딩.

이메일/비밀번호는 없다. OAuth 자체는 프론트(supabase-js)가 처리하고,
백엔드는 액세스 토큰을 검증해 자체 세션 쿠키를 발급한다.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.config.settings import SESSION_COOKIE, SESSION_TTL_DAYS
from app.service import auth_service
from app.service.auth_service import AuthError
from app.types.models import User
from app.ui.deps import get_current_user

router = APIRouter()
_MAX_AGE = SESSION_TTL_DAYS * 24 * 60 * 60


def _render(request: Request, name: str, current_user: Optional[User], **ctx):
    return request.app.state.templates.TemplateResponse(
        request, name, {"current_user": current_user, **ctx}
    )


@router.get("/login")
def login_page(request: Request):
    return _render(request, "login.html", None)


@router.get("/register")
def register_page():
    # 가입과 로그인은 소셜에서 동일하다 — 로그인 페이지로 통합
    return RedirectResponse("/login", status_code=303)


@router.get("/auth/callback")
def auth_callback(request: Request):
    # supabase-js가 URL의 세션을 파싱해 /auth/session으로 토큰을 보낸다
    return _render(request, "auth_callback.html", None)


@router.post("/auth/session")
def auth_session(access_token: str = Form(...)):
    """프론트가 받은 Supabase 액세스 토큰을 검증하고 세션 쿠키를 심는다."""
    try:
        teacher, cookie = auth_service.establish_session(access_token)
    except AuthError as exc:
        return JSONResponse({"error": str(exc)}, status_code=401)
    next_url = "/" if teacher.is_onboarded else "/onboarding"
    resp = JSONResponse({"next": next_url})
    resp.set_cookie(SESSION_COOKIE, cookie, httponly=True, samesite="lax", max_age=_MAX_AGE)
    return resp


@router.post("/logout")
def logout():
    resp = RedirectResponse("/", status_code=303)
    resp.delete_cookie(SESSION_COOKIE)
    return resp


@router.get("/onboarding")
def onboarding_form(request: Request, user: Optional[User] = Depends(get_current_user)):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    if user.is_onboarded:
        return RedirectResponse("/", status_code=303)
    return _render(request, "onboarding.html", user)


@router.post("/onboarding")
def onboarding_submit(
    request: Request,
    job_role: str = Form(...),
    years: str = Form(...),
    industry: str = Form(...),
    user: Optional[User] = Depends(get_current_user),
):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    try:
        auth_service.complete_onboarding(user.id, job_role, years, industry)
    except AuthError as exc:
        return _render(request, "onboarding.html", user, error=str(exc))
    return RedirectResponse("/", status_code=303)
