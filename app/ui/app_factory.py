"""FastAPI 앱 조립 — 템플릿/정적 파일 마운트, 라우터 등록, DB 초기화."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config.settings import CATEGORIES, REGIONS, SCHOOL_LEVELS, category_label
from app.repo.database import init_db
from app.ui import routes_auth, routes_community

_ROOT = Path(__file__).resolve().parents[2]


def create_app() -> FastAPI:
    init_db()

    app = FastAPI(title="이음 — 선생님 커뮤니티")

    templates = Jinja2Templates(directory=str(_ROOT / "templates"))
    # 템플릿 전역: 화면 어디서나 라벨/목록을 쓸 수 있게
    templates.env.globals.update(
        categories=CATEGORIES,
        category_label=category_label,
        school_levels=SCHOOL_LEVELS,
        regions=REGIONS,
        brand="이음",
    )
    app.state.templates = templates

    app.mount("/static", StaticFiles(directory=str(_ROOT / "static")), name="static")

    app.include_router(routes_auth.router)
    app.include_router(routes_community.router)
    return app
