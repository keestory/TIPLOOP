"""App Store 계정 삭제 요구사항의 보안·흐름 회귀 테스트."""

import json
from pathlib import Path

import pytest
from starlette.requests import Request

from app.config import settings
from app.providers import security
from app.service import account_service
from app.types.models import User
from app.ui import routes_auth


def _request(origin: str) -> Request:
    return Request({
        "type": "http",
        "method": "POST",
        "scheme": "https",
        "path": "/account/delete",
        "headers": [
            (b"host", b"tiploop.vercel.app"),
            (b"origin", origin.encode()),
        ],
        "server": ("tiploop.vercel.app", 443),
    })


def _user() -> User:
    return User(id=7, auth_id="auth-7", name="사용자", created_at="2026-09-03")


@pytest.mark.no_db
def test_account_delete_requires_same_origin(monkeypatch):
    monkeypatch.setattr(
        routes_auth.account_service,
        "delete_current_account",
        lambda *_args: pytest.fail("교차 출처에서 삭제를 실행하면 안 됩니다."),
    )

    response = routes_auth.delete_account(
        _request("https://attacker.example"), "access-token", _user()
    )

    assert response.status_code == 403


@pytest.mark.no_db
def test_account_delete_clears_app_session_cookie(monkeypatch):
    user = _user()
    called = []
    monkeypatch.setattr(
        routes_auth.account_service,
        "delete_current_account",
        lambda actual_user, token: called.append((actual_user, token)),
    )

    response = routes_auth.delete_account(
        _request("https://tiploop.vercel.app"), "access-token", user
    )

    assert response.status_code == 200
    assert called == [(user, "access-token")]
    cookie = response.headers["set-cookie"]
    assert f"{settings.SESSION_COOKIE}=\"\"" in cookie
    assert "Max-Age=0" in cookie


@pytest.mark.no_db
def test_account_service_revalidates_user_and_deletes_storage_before_account(monkeypatch):
    user = _user()
    events = []
    monkeypatch.setattr(
        account_service.security,
        "fetch_supabase_user",
        lambda *_args: {"id": "auth-7"},
    )
    monkeypatch.setattr(
        account_service.account_deletion,
        "start_account_deletion",
        lambda member_id, auth_id: events.append(("started", member_id, auth_id)),
    )
    monkeypatch.setattr(
        account_service.account_deletion,
        "owned_storage_paths",
        lambda _auth_id: {"research-media": ["auth-7/a.png"]},
    )
    monkeypatch.setattr(
        account_service.security,
        "delete_storage_paths",
        lambda _token, _url, _key, bucket, paths: events.append(
            ("storage", bucket, paths)
        ) or True,
    )
    monkeypatch.setattr(
        account_service.account_deletion,
        "delete_account",
        lambda member_id, auth_id: events.append(("account", member_id, auth_id)),
    )

    account_service.delete_current_account(user, "fresh-token")

    assert events == [
        ("started", 7, "auth-7"),
        ("storage", "research-media", ["auth-7/a.png"]),
        ("account", 7, "auth-7"),
    ]


@pytest.mark.no_db
def test_account_service_rejects_token_for_another_user(monkeypatch):
    monkeypatch.setattr(
        account_service.security,
        "fetch_supabase_user",
        lambda *_args: {"id": "auth-8"},
    )
    monkeypatch.setattr(
        account_service.account_deletion,
        "owned_storage_paths",
        lambda _auth_id: pytest.fail("다른 사용자 토큰으로 저장소를 조회하면 안 됩니다."),
    )

    with pytest.raises(account_service.AccountDeletionError, match="로그인 정보"):
        account_service.delete_current_account(_user(), "wrong-token")


@pytest.mark.no_db
def test_storage_delete_batches_at_supabase_limit(monkeypatch):
    batches = []

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def fake_urlopen(request, timeout):
        assert timeout == 20
        batches.append(json.loads(request.data.decode("utf-8"))["prefixes"])
        return Response()

    monkeypatch.setattr(security.urllib.request, "urlopen", fake_urlopen)
    paths = [f"auth-7/drafts/abcdefgh/file-{index}.png" for index in range(2001)]

    assert security.delete_storage_paths(
        "token", "https://project.supabase.co", "publishable", "bucket", paths
    )
    assert [len(batch) for batch in batches] == [1000, 1000, 1]


@pytest.mark.no_db
def test_storage_gate_serializes_upload_with_deletion_start():
    root = Path(__file__).resolve().parents[1]
    migration = (root / "supabase" / "migrations" / "20260903093000_guard_storage_during_account_deletion.sql").read_text(
        encoding="utf-8"
    )

    assert "deletion_started_at IS NULL" in migration
    assert "FOR SHARE;" in migration
    assert "FOR KEY SHARE;" not in migration
