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
    SITE_URL,
    SUPABASE_ANON_KEY,
    SUPABASE_URL,
    TAGLINE,
    TOPICS,
    YEARS,
    category_label,
)
from app.repo.database import init_db
from app.ui import routes_auth, routes_community, routes_crew, routes_post, routes_pwa

_ROOT = Path(__file__).resolve().parents[2]


def create_app() -> FastAPI:
    import os

    from app.config.settings import DATABASE_URL

    # 스키마 보장(멱등). 콜드 스타트마다 실행되므로, 스키마가 안정된 뒤에는
    # SKIP_DB_INIT=1 로 꺼서 콜드 스타트 지연을 줄일 수 있다(선택).
    if DATABASE_URL and os.getenv("SKIP_DB_INIT") != "1":
        # 서버리스 콜드 스타트에서 DB가 잠깐 안 붙어도 앱 부팅 자체는 막지 않는다.
        try:
            init_db()
        except Exception as exc:  # noqa: BLE001 - 부팅을 죽이지 않기 위한 광범위 캐치
            print(f"[warn] init_db 건너뜀: {exc}")

    app = FastAPI(title=f"{BRAND} — 실무자 커뮤니티")

    # 요청 하나당 DB 커넥션 하나만 빌려 모든 repo 호출이 재사용하게 한다.
    # 순수 ASGI 미들웨어라 다운스트림과 같은 태스크에서 실행돼 contextvar가
    # 그대로 전파된다(BaseHTTPMiddleware의 전파 문제 회피). DB를 안 쓰는 요청은
    # 지연 획득이라 커넥션을 열지 않는다(오버헤드 0).
    from app.repo import database as _db

    class _DBScope:
        def __init__(self, app):
            self.app = app

        async def __call__(self, scope, receive, send):
            if scope["type"] != "http":
                return await self.app(scope, receive, send)
            _db.begin_request()
            try:
                await self.app(scope, receive, send)
            finally:
                _db.end_request()

    app.add_middleware(_DBScope)

    templates = Jinja2Templates(directory=str(_ROOT / "templates"))
    # 템플릿 전역: 화면 어디서나 라벨/목록을 쓸 수 있게
    templates.env.globals.update(
        categories=CATEGORIES,
        category_label=category_label,
        job_roles=JOB_ROLES,
        years_list=YEARS,
        industries=INDUSTRIES,
        topics_list=TOPICS,
        brand=BRAND,
        tagline=TAGLINE,
        site_url=SITE_URL,
        supabase_url=SUPABASE_URL,
        supabase_anon_key=SUPABASE_ANON_KEY,
    )
    app.state.templates = templates

    app.mount("/static", StaticFiles(directory=str(_ROOT / "static")), name="static")

    app.include_router(routes_pwa.router)
    app.include_router(routes_auth.router)
    app.include_router(routes_crew.router)
    app.include_router(routes_post.router)
    app.include_router(routes_community.router)
    return app
