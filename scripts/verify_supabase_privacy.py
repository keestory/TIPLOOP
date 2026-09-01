"""배포 전 TIPLOOP Supabase 개인정보 경계를 검증한다.

사용법: 배포 대상 환경 변수를 로드한 뒤
    python -m scripts.verify_supabase_privacy
"""

from __future__ import annotations

import json
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app.config.settings import (
    DATABASE_URL,
    SUPABASE_ANON_KEY,
    SUPABASE_URL,
    _project_ref_from_database_url,
    _project_ref_from_supabase_url,
)
from app.repo.privacy import verify_privacy_boundaries


def verify_anon_posts_are_private() -> None:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise RuntimeError("SUPABASE_URL과 SUPABASE_PUBLISHABLE_KEY가 필요합니다.")
    request = Request(
        SUPABASE_URL.rstrip("/") + "/rest/v1/posts?select=id&limit=1",
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=15) as response:  # noqa: S310 - 검증 대상 URL은 환경 설정값
            status = response.status
            payload = response.read().decode("utf-8")
    except HTTPError as exc:
        # Data API에 posts 자체가 노출되지 않은 새 프로젝트도 안전한 상태다.
        if exc.code == 404:
            return
        try:
            error_payload = json.loads(exc.read().decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            error_payload = {}
        # 테이블 권한을 명시적으로 회수한 경우 PostgREST의 permission denied도
        # 기대한 차단 결과다.
        if exc.code in {401, 403} and error_payload.get("code") == "42501":
            return
        raise RuntimeError(f"Data API canary 실패: HTTP {exc.code}") from exc

    if status != 200:
        raise RuntimeError(f"Data API canary 실패: HTTP {status}")
    data = json.loads(payload)
    if not isinstance(data, list) or data:
        raise RuntimeError("anon publishable key로 posts 행이 노출됩니다.")


def verify_project_refs_match() -> None:
    api_ref = _project_ref_from_supabase_url(SUPABASE_URL)
    database_ref = _project_ref_from_database_url(DATABASE_URL)
    if not api_ref or not database_ref:
        raise RuntimeError("Supabase API/DB 프로젝트 ref를 연결 문자열에서 확인할 수 없습니다.")
    if api_ref != database_ref:
        raise RuntimeError("SUPABASE_URL과 DATABASE_URL의 프로젝트 ref가 다릅니다.")


def main() -> int:
    try:
        verify_project_refs_match()
        verify_privacy_boundaries()
        verify_anon_posts_are_private()
    except Exception as exc:  # noqa: BLE001 - 배포 게이트는 모든 실패를 차단한다.
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    print("[PASS] 13개 앱 테이블 RLS + anon posts Data API 차단 확인")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
