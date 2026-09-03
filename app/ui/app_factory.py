"""FastAPI 앱 조립 — 템플릿/정적 파일 마운트, 라우터 등록, DB 초기화."""

from __future__ import annotations


from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config.settings import (
    APPLE_AUTH_ENABLED,
    BRAND,
    CATEGORIES,
    INDUSTRIES,
    JOB_ROLES,
    OPERATOR_NAME,
    SITE_URL,
    SUPPORT_EMAIL,
    SUPPORT_URL,
    SUPABASE_ANON_KEY,
    SUPABASE_URL,
    TAGLINE,
    TOPICS,
    YEARS,
    category_label,
    validate_runtime_security,
)
from app.repo.database import init_db
from app.repo.privacy import verify_privacy_boundaries
from app.ui import (
    routes_auth,
    routes_community,
    routes_post,
    routes_pwa,
    routes_research_share,
)

_ROOT = Path(__file__).resolve().parents[2]


def create_app() -> FastAPI:
    import os

    from app.config.settings import DATABASE_URL

    validate_runtime_security()

    # 개인정보 경계인 RLS까지 확인돼야 앱을 부팅한다. 스키마 초기화를 생략해도
    # 보안 검증은 생략하지 않으며, 실패하면 fail-closed로 시작을 중단한다.
    if DATABASE_URL:
        if os.getenv("SKIP_DB_INIT") != "1":
            init_db()
        verify_privacy_boundaries()

    app = FastAPI(title=f"{BRAND} — 개인 서비스 노트")

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
        apple_auth_enabled=APPLE_AUTH_ENABLED,
        operator_name=OPERATOR_NAME,
        support_email=SUPPORT_EMAIL,
        support_url=SUPPORT_URL,
    )
    app.state.templates = templates

    app.mount("/static", StaticFiles(directory=str(_ROOT / "static")), name="static")

    app.include_router(routes_pwa.router)
    app.include_router(routes_auth.router)
    app.include_router(routes_post.router)
    app.include_router(routes_research_share.router)
    # App Store 첫 버전은 개인 서비스 노트에만 집중한다. 이전 커뮤니티/크루
    # 모듈은 데이터 호환을 위해 저장소에 남기되 HTTP 라우트에는 연결하지 않는다.
    app.include_router(routes_community.router)
    return app
