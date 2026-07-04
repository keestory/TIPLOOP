"""FastAPI 앱 조립 — 템플릿/정적 파일 마운트, 라우터 등록, DB 초기화."""

from __future__ import annotations


from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config.settings import (
    BRAND,
    CATEGORIES,
    INDUSTRIES,
    JOB_ROLES,
    SUPABASE_ANON_KEY,
    SUPABASE_URL,
    TAGLINE,
    YEARS,
    category_label,
)
from app.repo.database import init_db
from app.ui import routes_auth, routes_community

_ROOT = Path(__file__).resolve().parents[2]


def create_app() -> FastAPI:
    from app.config.settings import DATABASE_URL

    if DATABASE_URL:
        init_db()  # 스키마 보장. DB가 없으면 부팅은 하되 첫 쿼리에서 명확히 실패.

    app = FastAPI(title=f"{BRAND} — 실무자 커뮤니티")

    templates = Jinja2Templates(directory=str(_ROOT / "templates"))
    # 템플릿 전역: 화면 어디서나 라벨/목록을 쓸 수 있게
    templates.env.globals.update(
        categories=CATEGORIES,
        category_label=category_label,
        job_roles=JOB_ROLES,
        years_list=YEARS,
        industries=INDUSTRIES,
        brand=BRAND,
        tagline=TAGLINE,
        supabase_url=SUPABASE_URL,
        supabase_anon_key=SUPABASE_ANON_KEY,
    )
    app.state.templates = templates

    app.mount("/static", StaticFiles(directory=str(_ROOT / "static")), name="static")

    app.include_router(routes_auth.router)
    app.include_router(routes_community.router)
    return app
