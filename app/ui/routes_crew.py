"""크루 라우트 — 함께 쓰는 주간 기록 (목록·생성·합류·기록)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.config.settings import CRON_SECRET
from app.service import crew_service
from app.service.crew_service import CrewError
from app.types.models import User
from app.ui.deps import get_current_user

router = APIRouter()


def _render(request: Request, name: str, current_user: Optional[User], **ctx):
    return request.app.state.templates.TemplateResponse(
        request, name, {"current_user": current_user, **ctx}
    )


def _gate(user: Optional[User]) -> Optional[RedirectResponse]:
    if user is None:
        return RedirectResponse("/login", status_code=303)
    if not user.is_onboarded:
        return RedirectResponse("/onboarding", status_code=303)
    return None


@router.get("/cron/weekly-nudge", include_in_schema=False)
def cron_weekly_nudge(request: Request):
    """주간 마감 넛지 (Vercel Cron, 일요일 저녁). Bearer CRON_SECRET 필수."""
    auth = request.headers.get("authorization", "")
    if not CRON_SECRET or auth != f"Bearer {CRON_SECRET}":
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    return JSONResponse({"sent": crew_service.send_weekly_nudges()})


@router.get("/crews")
def crews_list(request: Request, user: Optional[User] = Depends(get_current_user)):
    if gate := _gate(user):
        return gate
    return _render(request, "crews.html", user, summaries=crew_service.my_crews(user.id))


@router.get("/crews/new")
def crew_new_form(request: Request, user: Optional[User] = Depends(get_current_user)):
    if gate := _gate(user):
        return gate
    return _render(request, "crew_new.html", user)


@router.post("/crews")
def crew_create(
    request: Request,
    name: str = Form(...),
    topic: str = Form(""),
    user: Optional[User] = Depends(get_current_user),
):
    if gate := _gate(user):
        return gate
    try:
        crew = crew_service.create_crew(user.id, name, topic)
    except CrewError as exc:
        return _render(request, "crew_new.html", user, error=str(exc), form_name=name, form_topic=topic)
    return RedirectResponse(f"/crews/{crew.id}", status_code=303)


@router.get("/crews/join/{invite_code}")
def crew_join(request: Request, invite_code: str, user: Optional[User] = Depends(get_current_user)):
    """초대 링크 — 로그인/온보딩 게이트 후 합류."""
    if gate := _gate(user):
        return gate
    try:
        crew = crew_service.join_by_code(user.id, invite_code)
    except CrewError as exc:
        return _render(request, "crews.html", user,
                       summaries=crew_service.my_crews(user.id), error=str(exc))
    return RedirectResponse(f"/crews/{crew.id}", status_code=303)


@router.get("/crews/{crew_id}")
def crew_detail(request: Request, crew_id: int, user: Optional[User] = Depends(get_current_user)):
    if gate := _gate(user):
        return gate
    try:
        home = crew_service.crew_home(crew_id, user.id)
    except CrewError:
        return RedirectResponse("/crews", status_code=303)
    return _render(request, "crew_detail.html", user, **home)


@router.post("/crews/{crew_id}/entries")
def crew_add_entry(
    request: Request,
    crew_id: int,
    body: str = Form(...),
    user: Optional[User] = Depends(get_current_user),
):
    if gate := _gate(user):
        return gate
    try:
        crew_service.add_entry(crew_id, user.id, body)
    except CrewError:
        pass  # 빈 내용 등은 조용히 무시하고 크루 홈으로
    return RedirectResponse(f"/crews/{crew_id}", status_code=303)
