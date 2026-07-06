"""PWA 라우트 — 서비스 워커를 루트 스코프(/)로 서빙.

서비스 워커가 앱 전체(/)를 제어하려면 루트 경로에서 제공하거나
Service-Worker-Allowed 헤더가 필요하다. /static/ 에 두면 스코프가 좁아진다.
매니페스트는 스코프 제약이 없어 /static/manifest.webmanifest 로 링크한다.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()
_STATIC = Path(__file__).resolve().parents[2] / "static"


@router.get("/sw.js", include_in_schema=False)
def service_worker() -> FileResponse:
    return FileResponse(
        _STATIC / "sw.js",
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"},
    )
