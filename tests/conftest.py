"""테스트 공통 설정 — Supabase Postgres(로컬 PG로 대체) 격리.

app 모듈이 import 시점에 설정을 읽으므로, import 전에 환경 변수를 채운다.
DATABASE_URL은 러너가 제공한다(없으면 DB 의존 테스트는 skip).
"""

import os

os.environ.setdefault("SUPABASE_JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("IEUM_SECRET", "test-session-secret")

import pytest

_DB = os.environ.get("DATABASE_URL")
_TABLES = (
    "media_comments, reviews, post_helpful, comment_reactions, post_reactions, "
    "comments, posts, members"
)


def _reset_schema():
    from app.repo.database import get_connection, init_db

    with get_connection() as conn:
        conn.execute(f"DROP TABLE IF EXISTS {_TABLES} CASCADE")
    init_db()


@pytest.fixture(autouse=True)
def fresh_db():
    """각 테스트마다 빈 스키마로 초기화."""
    if not _DB:
        pytest.skip("DATABASE_URL 미설정 — Postgres가 필요합니다")
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
