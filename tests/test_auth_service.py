"""인증 서비스 단위 테스트 — Supabase 소셜 로그인 흐름.

토큰 검증은 Supabase(/auth/v1/user)에 위임하므로, 그 조회를 monkeypatch로 대체한다.
"""

import pytest

from app.providers import security
from app.service import auth_service
from app.service.auth_service import AuthError


def _google_user(sub="google-1", **over):
    u = {
        "id": sub,
        "email": "kim@gmail.com",
        "app_metadata": {"provider": "google"},
        "user_metadata": {"full_name": "김서연", "avatar_url": "http://x/a.png"},
    }
    u.update(over)
    return u


def _patch(monkeypatch, user):
    """token == 'good' 이면 user 반환, 아니면 None(무효 토큰)."""
    monkeypatch.setattr(
        security, "fetch_supabase_user",
        lambda token, url, key: user if token == "good" else None,
    )


def test_google_login_creates_unonboarded_member(monkeypatch):
    _patch(monkeypatch, _google_user())
    member, cookie = auth_service.establish_session("good")
    assert member.name == "김서연"
    assert member.email == "kim@gmail.com"
    assert member.provider == "google"
    assert member.is_onboarded is False
    assert auth_service.current_user(cookie).id == member.id


def test_login_is_idempotent_by_auth_id(monkeypatch):
    _patch(monkeypatch, _google_user())
    t1, _ = auth_service.establish_session("good")
    _patch(monkeypatch, _google_user(user_metadata={"full_name": "김서연B", "avatar_url": None}))
    t2, _ = auth_service.establish_session("good")
    assert t1.id == t2.id            # 같은 id → 같은 회원
    assert t2.name == "김서연B"      # 이름은 최신화


def test_kakao_login_sets_provider(monkeypatch):
    _patch(monkeypatch, {
        "id": "kakao-1", "app_metadata": {"provider": "kakao"},
        "user_metadata": {"name": "박지우"},
    })
    member, _ = auth_service.establish_session("good")
    assert member.provider == "kakao"
    assert member.name == "박지우"


def test_invalid_token_rejected(monkeypatch):
    _patch(monkeypatch, _google_user())
    with pytest.raises(AuthError):
        auth_service.establish_session("bad")


def test_current_user_none_for_bad_cookie():
    assert auth_service.current_user(None) is None
    assert auth_service.current_user("garbage.cookie.value") is None


def test_save_topics_keeps_only_known(monkeypatch):
    _patch(monkeypatch, _google_user())
    member, _ = auth_service.establish_session("good")
    done = auth_service.save_topics(member.id, ["리텐션", "우주여행", "A/B 테스트"])
    assert done.topics == ("리텐션", "A/B 테스트")   # 모르는 주제는 버린다
    assert done.is_onboarded is False               # 주제는 게이트가 아님


def test_save_topics_allows_empty(monkeypatch):
    _patch(monkeypatch, _google_user())
    member, _ = auth_service.establish_session("good")
    done = auth_service.save_topics(member.id, [])
    assert done.topics == ()


def test_tour_seen_flag(monkeypatch):
    from app.repo import members
    _patch(monkeypatch, _google_user())
    member, _ = auth_service.establish_session("good")
    assert member.has_seen_tour is False        # 신규 회원은 투어 미시청
    auth_service.mark_tour_seen(member.id)
    assert members.get(member.id).has_seen_tour is True


def test_onboarding_completes_profile(monkeypatch):
    _patch(monkeypatch, _google_user())
    member, _ = auth_service.establish_session("good")
    done = auth_service.complete_onboarding(member.id, "PM", "3~5년", "커머스")
    assert done.is_onboarded is True
    assert done.job_role == "PM" and done.years == "3~5년"
    assert done.industry == "커머스"


def test_onboarding_rejects_bad_values(monkeypatch):
    _patch(monkeypatch, _google_user())
    member, _ = auth_service.establish_session("good")
    with pytest.raises(AuthError):
        auth_service.complete_onboarding(member.id, "사장", "3~5년", "커머스")
    with pytest.raises(AuthError):
        auth_service.complete_onboarding(member.id, "PM", "20년", "커머스")
    with pytest.raises(AuthError):
        auth_service.complete_onboarding(member.id, "PM", "3~5년", "우주")
