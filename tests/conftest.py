"""테스트 공통 설정 — 명시적인 테스트 Postgres만 사용한다.

app 모듈이 import 시점에 설정을 읽으므로, import 전에 환경 변수를 채운다.
운영 ``DATABASE_URL``은 절대 테스트 대상으로 삼지 않는다.
"""

import os
from pathlib import Path
from urllib.parse import unquote, urlparse

os.environ.setdefault("SUPABASE_JWT_SECRET", "test-jwt-secret")
os.environ["IEUM_SECRET"] = "tiploop-test-session-secret-32-chars-minimum"
os.environ["SESSION_COOKIE_SECURE"] = "1"

import pytest

_DB = os.environ.get("TEST_DATABASE_URL", "").strip()
_PRODUCTION_DB = os.environ.get("DATABASE_URL", "").strip()
if not _PRODUCTION_DB:
    try:
        from dotenv import dotenv_values

        _PRODUCTION_DB = (dotenv_values(Path(__file__).parents[1] / ".env").get("DATABASE_URL") or "").strip()
    except ImportError:
        pass


def _db_identity(url: str) -> tuple:
    """비밀번호·쿼리 옵션을 빼고 실제 DB 대상을 비교한다."""
    parsed = urlparse(url.replace("postgres://", "postgresql://", 1))
    return (
        (parsed.hostname or "").lower(),
        parsed.port or 5432,
        unquote(parsed.username or ""),
        unquote(parsed.path.rstrip("/")),
    )


def _project_ref(parsed) -> str:
    username = unquote(parsed.username or "")
    if username.startswith("postgres."):
        return username.split(".", 1)[1]
    hostname = (parsed.hostname or "").lower()
    if hostname.endswith(".supabase.co"):
        return hostname.split(".", 1)[0]
    return ""


if _DB:
    parsed = urlparse(_DB)
    database_name = unquote(parsed.path.lstrip("/")).lower()
    is_local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if database_name != "tiploop_test" and not database_name.endswith("_test"):
        pytest.exit(
            "TEST_DATABASE_URL은 tiploop_test 또는 정확히 _test로 끝나는 전용 DB만 허용합니다.",
            returncode=2,
        )
    if os.environ.get("TIPLOOP_TEST_DB_CONFIRM", "").strip().lower() != database_name:
        pytest.exit(
            "TIPLOOP_TEST_DB_CONFIRM에 전용 테스트 DB 이름을 정확히 다시 입력해야 합니다.",
            returncode=2,
        )
    if _PRODUCTION_DB and _db_identity(_DB) == _db_identity(_PRODUCTION_DB):
        pytest.exit("TEST_DATABASE_URL이 현재 DATABASE_URL과 같습니다. 테스트를 중단합니다.", returncode=2)
    if not is_local:
        expected_ref = os.environ.get("TEST_DATABASE_PROJECT_REF", "").strip()
        actual_ref = _project_ref(parsed)
        if (
            os.environ.get("ALLOW_REMOTE_TEST_DB") != "1"
            or not expected_ref
            or actual_ref != expected_ref
        ):
            pytest.exit(
                "원격 테스트 DB는 ALLOW_REMOTE_TEST_DB=1과 정확히 일치하는 "
                "TEST_DATABASE_PROJECT_REF가 모두 필요합니다.",
                returncode=2,
            )

# settings.py의 .env 자동 로딩보다 먼저 빈 값까지 명시한다. 이렇게 해야 로컬
# .env의 실제 DATABASE_URL이 테스트 과정에서 우연히 선택되지 않는다.
os.environ["DATABASE_URL"] = _DB
_TABLES = (
    "notifications, crew_entries, crew_members, crews, follows, media_comments, "
    "reviews, post_helpful, comment_reactions, post_reactions, comments, posts, members"
)


def _reset_schema():
    from app.repo.database import get_connection, init_db

    with get_connection() as conn:
        guard_table = conn.execute(
            "SELECT to_regclass('public.tiploop_test_guard') AS name"
        ).fetchone()
        if not guard_table or guard_table["name"] is None:
            raise RuntimeError(
                "사전에 만든 tiploop_test_guard 안전 마커 테이블이 없습니다. "
                "테스트가 마커를 자동 생성하지 않습니다."
            )
        marker = conn.execute(
            "SELECT marker FROM tiploop_test_guard WHERE marker = 'TIPLOOP_TEST_ONLY'"
        ).fetchone()
        if not marker:
            raise RuntimeError(
                "사전에 만든 tiploop_test_guard 안전 마커가 없습니다. "
                "테스트가 마커를 자동 생성하지 않습니다."
            )
        conn.execute(f"DROP TABLE IF EXISTS {_TABLES} CASCADE")
    init_db()


@pytest.fixture(autouse=True)
def fresh_db(request):
    """각 테스트마다 빈 스키마로 초기화."""
    if request.node.get_closest_marker("no_db"):
        yield
        return
    if not _DB:
        pytest.skip("TEST_DATABASE_URL 미설정 — Postgres가 필요합니다")
    _reset_schema()
    yield


@pytest.fixture
def make_member():
    """테스트용 회원 생성기. onboard=False면 직군/연차 비운 상태."""
    from app.repo import members

    counter = {"n": 0}

    def _make(name="쌤", job_role="PM", years="1~3년", industry="커머스",
              provider="google", onboard=True):
        counter["n"] += 1
        n = counter["n"]
        member = members.upsert_by_auth(
            auth_id=f"auth-{n}", name=name, email=f"t{n}@ex.com",
            avatar_url=None, provider=provider,
        )
        if onboard:
            member = members.complete_profile(member.id, job_role, years, industry)
        return member

    return _make
