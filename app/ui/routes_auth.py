"""인증 라우트 — 구글/Apple 소셜 로그인, 세션, 온보딩.

이메일/비밀번호는 없다. OAuth 자체는 프론트(supabase-js)가 처리하고,
백엔드는 액세스 토큰을 검증해 자체 세션 쿠키를 발급한다.
"""

from __future__ import annotations

from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.config.settings import SESSION_COOKIE, SESSION_COOKIE_SECURE, SESSION_TTL_DAYS
from app.service import account_service, auth_service
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
def login_page(request: Request, deleted: str = ""):
    return _render(request, "login.html", None, account_deleted=deleted == "1")


@router.get("/register")
def register_page():
    # 가입과 로그인은 소셜에서 동일하다 — 로그인 페이지로 통합
    return RedirectResponse("/login", status_code=303)


@router.get("/auth/callback")
def auth_callback(request: Request):
    # supabase-js가 URL의 세션을 파싱해 /auth/session으로 토큰을 보낸다
    return _render(request, "auth_callback.html", None)


def _is_same_origin(request: Request) -> bool:
    """브라우저가 보낸 세션 교환 요청이 현재 앱 출처에서 왔는지 확인한다."""
    source = request.headers.get("origin")
    if not source:
        referer = request.headers.get("referer", "")
        parsed_referer = urlparse(referer)
        if parsed_referer.scheme and parsed_referer.netloc:
            source = f"{parsed_referer.scheme}://{parsed_referer.netloc}"
    if not source:
        return False
    parsed = urlparse(source)
    return (
        parsed.scheme in {"http", "https"}
        and parsed.netloc == request.headers.get("host")
    )


@router.post("/auth/session")
def auth_session(request: Request, access_token: str = Form(...)):
    """프론트가 받은 Supabase 액세스 토큰을 검증하고 세션 쿠키를 심는다."""
    if not _is_same_origin(request):
        return JSONResponse({"error": "허용되지 않은 로그인 요청입니다."}, status_code=403)
    try:
        teacher, cookie = auth_service.establish_session(access_token)
    except AuthError as exc:
        return JSONResponse({"error": str(exc)}, status_code=401)
    # 재방문자(온보딩 완료)는 곧장 피드로. 신규는 약관 → 온보딩 순서.
    if teacher.is_onboarded:
        next_url = "/"
    elif not teacher.agreed_terms:
        next_url = "/terms"
    else:
        next_url = "/onboarding"
    resp = JSONResponse({"next": next_url})
    resp.set_cookie(
        SESSION_COOKIE,
        cookie,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="lax",
        max_age=_MAX_AGE,
    )
    return resp


@router.post("/logout")
def logout(request: Request):
    # 자체 쿠키를 먼저 지운 뒤, 화면에서 Supabase 브라우저 세션도 signOut한다.
    resp = _render(request, "logout.html", None)
    resp.delete_cookie(
        SESSION_COOKIE,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="lax",
    )
    resp.headers["Cache-Control"] = "no-store"
    return resp


@router.post("/account/delete")
def delete_account(
    request: Request,
    access_token: str = Form(...),
    user: Optional[User] = Depends(get_current_user),
):
    """앱 안에서 전체 계정·노트·첨부 삭제를 시작하고 완료한다."""
    if user is None:
        return JSONResponse({"error": "다시 로그인해 주세요."}, status_code=401)
    if not _is_same_origin(request):
        return JSONResponse({"error": "허용되지 않은 요청입니다."}, status_code=403)
    try:
        account_service.delete_current_account(user, access_token)
    except account_service.AccountDeletionError as exc:
        return JSONResponse({"error": str(exc)}, status_code=409)
    resp = JSONResponse({"ok": True, "next": "/login?deleted=1"})
    resp.delete_cookie(
        SESSION_COOKIE,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="lax",
    )
    resp.headers["Cache-Control"] = "no-store"
    return resp


@router.post("/tour/seen")
def tour_seen(user: Optional[User] = Depends(get_current_user)):
    """첫 로그인 코치마크 투어 완료/건너뛰기 저장 (프론트 fetch)."""
    if user is not None:
        auth_service.mark_tour_seen(user.id)
    return JSONResponse({"ok": True})


# ── 약관 동의 (신규 가입 첫 단계) ────────────────────────────────────
@router.get("/terms")
def terms_form(request: Request, user: Optional[User] = Depends(get_current_user)):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    if user.is_onboarded:
        return RedirectResponse("/", status_code=303)
    if user.agreed_terms:
        return RedirectResponse("/onboarding", status_code=303)
    return _render(request, "terms.html", user)


@router.post("/terms")
def terms_submit(user: Optional[User] = Depends(get_current_user)):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    auth_service.agree_terms(user.id)
    return RedirectResponse("/onboarding", status_code=303)


# 법률 문서 — 로그인 없이 열람 가능(App Store 개인정보처리방침 URL로도 사용)
@router.get("/terms/service")
def legal_service(request: Request, user: Optional[User] = Depends(get_current_user)):
    return _render(request, "legal_service.html", user)


@router.get("/terms/privacy")
def legal_privacy(request: Request, user: Optional[User] = Depends(get_current_user)):
    return _render(request, "legal_privacy.html", user)


@router.get("/support")
def support(request: Request, user: Optional[User] = Depends(get_current_user)):
    return _render(request, "support.html", user)


# ── 관심 주제 수정 (온보딩 완료 후 언제든) ──────────────────────────
@router.get("/topics")
def topics_form(request: Request, user: Optional[User] = Depends(get_current_user)):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    if not user.is_onboarded:
        return RedirectResponse("/onboarding", status_code=303)
    return _render(request, "onboarding_topics.html", user, edit=True)


@router.post("/topics")
def topics_submit(
    topics: Optional[list[str]] = Form(None),
    user: Optional[User] = Depends(get_current_user),
):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    auth_service.save_topics(user.id, topics or [])
    return RedirectResponse("/", status_code=303)


# ── 온보딩 ① 관심 주제 (2 / 3) ──────────────────────────────────────
@router.get("/onboarding")
def onboarding_topics(request: Request, user: Optional[User] = Depends(get_current_user)):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    if user.is_onboarded:
        return RedirectResponse("/", status_code=303)
    if not user.agreed_terms:
        return RedirectResponse("/terms", status_code=303)
    return _render(request, "onboarding_topics.html", user)


@router.post("/onboarding")
def onboarding_topics_submit(
    topics: Optional[list[str]] = Form(None),
    user: Optional[User] = Depends(get_current_user),
):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    auth_service.save_topics(user.id, topics or [])
    return RedirectResponse("/onboarding/profile", status_code=303)


# ── 온보딩 ② 프로필 직군·연차·업종 (3 / 3) ─────────────────────────
@router.get("/onboarding/profile")
def onboarding_profile(
    request: Request, edit: str = "", user: Optional[User] = Depends(get_current_user)
):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    # edit 모드(프로필 설정에서 진입)는 온보딩 완료 후에도 열 수 있다.
    if not edit:
        if user.is_onboarded:
            return RedirectResponse("/", status_code=303)
        if not user.agreed_terms:
            return RedirectResponse("/terms", status_code=303)
    return _render(request, "onboarding_profile.html", user, edit=bool(edit))


@router.post("/onboarding/profile")
def onboarding_profile_submit(
    request: Request,
    job_role: str = Form(...),
    years: str = Form(...),
    industry: str = Form(...),
    edit: str = Form(""),
    user: Optional[User] = Depends(get_current_user),
):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    try:
        auth_service.complete_onboarding(user.id, job_role, years, industry)
    except AuthError as exc:
        return _render(request, "onboarding_profile.html", user, edit=bool(edit), error=str(exc))
    # 설정에서 수정했으면 내 프로필로, 최초 온보딩이면 피드로.
    return RedirectResponse(f"/users/{user.id}" if edit else "/", status_code=303)
