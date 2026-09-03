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
from app.repo.database import get_connection
from app.repo.privacy import verify_privacy_boundaries

_MEDIA_BUCKETS = {
    "tiploop-research-images": 10 * 1024 * 1024,
    "tiploop-research-videos": 50 * 1024 * 1024,
}
_MEDIA_POLICIES = {
    "research_media_insert_own": "INSERT",
    "research_media_select_own": "SELECT",
    "research_media_delete_own": "DELETE",
}


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


def verify_private_media_storage() -> None:
    """연구 미디어 버킷이 비공개이고 브라우저 공개 정책이 없는지 확인한다."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, public, file_size_limit
              FROM storage.buckets
             WHERE id = ANY(%s)
            """,
            (list(_MEDIA_BUCKETS),),
        ).fetchall()
        policies = conn.execute(
            """
            SELECT policyname, cmd, roles, qual, with_check
              FROM pg_policies
             WHERE schemaname = 'storage'
               AND tablename = 'objects'
               AND roles && ARRAY['anon'::name, 'public'::name, 'authenticated'::name]
            """
        ).fetchall()
    by_id = {row["id"]: row for row in rows}
    if set(by_id) != set(_MEDIA_BUCKETS):
        raise RuntimeError("연구 미디어 Storage 버킷이 모두 존재하지 않습니다.")
    for bucket, expected_limit in _MEDIA_BUCKETS.items():
        row = by_id[bucket]
        if row["public"] or int(row["file_size_limit"] or 0) != expected_limit:
            raise RuntimeError(f"{bucket}의 private/파일 제한 설정이 올바르지 않습니다.")
    by_name = {row["policyname"]: row for row in policies}
    if set(by_name) != set(_MEDIA_POLICIES):
        raise RuntimeError("Storage objects의 브라우저 정책 목록이 승인된 3개와 다릅니다.")
    for name, command in _MEDIA_POLICIES.items():
        row = by_name[name]
        expression = f"{row['qual'] or ''} {row['with_check'] or ''}"
        if (
            row["cmd"] != command
            or list(row["roles"]) != ["authenticated"]
            or "tiploop-research-images" not in expression
            or "tiploop-research-videos" not in expression
            or "storage.foldername(name)" not in expression
            or "auth.uid()" not in expression
            or (
                command == "INSERT"
                and "tiploop_account_accepts_storage" not in expression
            )
        ):
            raise RuntimeError(f"{name} Storage 소유자 정책이 예상 범위와 다릅니다.")


def main() -> int:
    try:
        verify_project_refs_match()
        verify_privacy_boundaries()
        verify_anon_posts_are_private()
        verify_private_media_storage()
    except Exception as exc:  # noqa: BLE001 - 배포 게이트는 모든 실패를 차단한다.
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    print(
        "[PASS] 15개 앱 테이블 RLS + Data API/비공개 Storage + "
        "계정 삭제 gate 확인"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
