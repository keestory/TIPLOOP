"""RLS fail-closed 경계의 순수 회귀 테스트."""

import pytest
from starlette.requests import Request

from app.config import settings
from app.repo import privacy
from app.ui import app_factory
from app.ui import routes_auth
from app.types.models import User


class Rows:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class Connection:
    def __init__(self, states, policies, privileges):
        self.states = states
        self.policies = policies
        self.privileges = privileges

    def execute(self, query, _params):
        if "pg_class" in query:
            return Rows(self.states)
        if "has_table_privilege" in query:
            return Rows(self.privileges)
        return Rows(self.policies)


class ConnectionContext:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self.connection

    def __exit__(self, *_exc):
        return False


def _connection(states, policies=(), privileges=()):
    return lambda: ConnectionContext(Connection(states, policies, privileges))


@pytest.mark.no_db
def test_privacy_check_requires_rls_on_every_table(monkeypatch):
    incomplete = [{"relname": "posts", "relrowsecurity": True}]
    monkeypatch.setattr(privacy, "get_connection", _connection(incomplete))
    with pytest.raises(RuntimeError, match="RLS 보안 경계"):
        privacy.verify_privacy_boundaries()


@pytest.mark.no_db
def test_privacy_check_rejects_browser_role_policy(monkeypatch):
    states = [
        {"relname": table, "relrowsecurity": True}
        for table in privacy.RLS_TABLES
    ]
    policies = [{"tablename": "posts", "policyname": "public read", "roles": ["anon"]}]
    monkeypatch.setattr(privacy, "get_connection", _connection(states, policies))
    with pytest.raises(RuntimeError, match="브라우저 역할"):
        privacy.verify_privacy_boundaries()


@pytest.mark.no_db
def test_privacy_check_rejects_browser_table_privilege(monkeypatch):
    states = [
        {"relname": table, "relrowsecurity": True}
        for table in privacy.RLS_TABLES
    ]
    privileges = [{"role_name": "anon", "table_name": "posts"}]
    monkeypatch.setattr(
        privacy,
        "get_connection",
        _connection(states, privileges=privileges),
    )
    with pytest.raises(RuntimeError, match="직접 테이블 권한"):
        privacy.verify_privacy_boundaries()


@pytest.mark.no_db
def test_runtime_rejects_mismatched_supabase_projects(monkeypatch):
    monkeypatch.setattr(
        settings,
        "SUPABASE_URL",
        "https://api-project.supabase.co",
    )
    monkeypatch.setattr(
        settings,
        "DATABASE_URL",
        "postgresql://postgres.db-project:secret@pooler.supabase.com:6543/postgres",
    )
    monkeypatch.setattr(settings, "SESSION_SECRET", "x" * 32)
    with pytest.raises(RuntimeError, match="서로 다른 Supabase 프로젝트"):
        settings.validate_runtime_security()


@pytest.mark.no_db
def test_database_url_mask_hides_at_sign_in_password():
    from scripts.check_db import mask_database_url

    masked = mask_database_url(
        "postgresql://postgres.project:secret@part@pooler.supabase.com:6543/postgres"
    )
    assert masked == (
        "postgresql://postgres.project:***@pooler.supabase.com:6543/postgres"
    )
    assert "secret" not in masked


@pytest.mark.no_db
def test_app_boot_is_fail_closed_when_schema_init_fails(monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_URL", "postgresql://test.invalid/tiploop_test")

    def fail():
        raise RuntimeError("migration failed")

    monkeypatch.setattr(app_factory, "init_db", fail)
    with pytest.raises(RuntimeError, match="migration failed"):
        app_factory.create_app()


@pytest.mark.no_db
def test_app_boot_rejects_weak_session_secret(monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_URL", "postgresql://test.invalid/tiploop_test")
    monkeypatch.setattr(settings, "SESSION_SECRET", "dev-only-change-me")
    with pytest.raises(RuntimeError, match="32자 이상의 IEUM_SECRET"):
        app_factory.create_app()


@pytest.mark.no_db
def test_auth_session_cookie_is_secure(monkeypatch):
    user = User(
        id=7,
        auth_id="auth-7",
        name="연구자",
        created_at="2026-09-01",
        job_role="PM",
        years="3~5년",
    )
    monkeypatch.setattr(
        routes_auth.auth_service,
        "establish_session",
        lambda _token: (user, "signed-session"),
    )
    request = Request({
        "type": "http",
        "method": "POST",
        "scheme": "https",
        "path": "/auth/session",
        "headers": [
            (b"host", b"tiploop.vercel.app"),
            (b"origin", b"https://tiploop.vercel.app"),
        ],
        "server": ("tiploop.vercel.app", 443),
    })
    response = routes_auth.auth_session(request, "access-token")
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=lax" in cookie


@pytest.mark.no_db
def test_auth_session_rejects_cross_origin(monkeypatch):
    monkeypatch.setattr(
        routes_auth.auth_service,
        "establish_session",
        lambda _token: pytest.fail("교차 출처 토큰을 검증하면 안 됩니다."),
    )
    request = Request({
        "type": "http",
        "method": "POST",
        "scheme": "https",
        "path": "/auth/session",
        "headers": [
            (b"host", b"tiploop.vercel.app"),
            (b"origin", b"https://attacker.example"),
        ],
        "server": ("tiploop.vercel.app", 443),
    })
    response = routes_auth.auth_session(request, "attacker-token")
    assert response.status_code == 403
