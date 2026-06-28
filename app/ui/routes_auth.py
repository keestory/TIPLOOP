"""인증 라우트 — 가입·로그인·로그아웃."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.config.settings import SESSION_COOKIE
from app.service import auth_service
from app.service.auth_service import AuthError

router = APIRouter()


def _render(request: Request, name: str, **ctx):
    return request.app.state.templates.TemplateResponse(request, name, ctx)


def _redirect_with_session(url: str, token: str) -> RedirectResponse:
    resp = RedirectResponse(url, status_code=303)
    resp.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 14)
    return resp


@router.get("/register")
def register_form(request: Request):
    return _render(request, "register.html")


@router.post("/register")
def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    name: str = Form(...),
    school_level: str = Form(...),
    region: str = Form(...),
    subject: str = Form(""),
):
    try:
        _, token = auth_service.register(email, password, name, school_level, region, subject)
    except AuthError as exc:
        return _render(request, "register.html", error=str(exc), form={
            "email": email, "name": name, "school_level": school_level,
            "region": region, "subject": subject,
        })
    return _redirect_with_session("/", token)


@router.get("/login")
def login_form(request: Request):
    return _render(request, "login.html")


@router.post("/login")
def login_submit(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        _, token = auth_service.login(email, password)
    except AuthError as exc:
        return _render(request, "login.html", error=str(exc), form={"email": email})
    return _redirect_with_session("/", token)


@router.post("/logout")
def logout(request: Request):
    auth_service.logout(request.cookies.get(SESSION_COOKIE))
    resp = RedirectResponse("/", status_code=303)
    resp.delete_cookie(SESSION_COOKIE)
    return resp
