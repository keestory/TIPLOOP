"""인증 서비스 단위 테스트 — Supabase 소셜 로그인 흐름."""

import base64
import hashlib
import hmac
import json
import time

import pytest

from app.service import auth_service
from app.service.auth_service import AuthError

SECRET = "test-jwt-secret"  # conftest가 SUPABASE_JWT_SECRET로 설정


def _b64(data: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()


def make_token(secret=SECRET, exp_delta=3600, **claims) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": "auth-abc", "exp": int(time.time()) + exp_delta, **claims}
    signing = f"{_b64(header)}.{_b64(payload)}"
    sig = base64.urlsafe_b64encode(
        hmac.new(secret.encode(), signing.encode(), hashlib.sha256).digest()
    ).rstrip(b"=").decode()
    return f"{signing}.{sig}"


def _google_token(**over):
    claims = {
        "sub": "google-user-1",
        "email": "kim@gmail.com",
        "app_metadata": {"provider": "google"},
        "user_metadata": {"full_name": "김서연", "avatar_url": "http://x/a.png"},
    }
    claims.update(over)
    return make_token(**claims)


def test_google_login_creates_unonboarded_teacher():
    teacher, cookie = auth_service.establish_session(_google_token())
    assert teacher.name == "김서연"
    assert teacher.email == "kim@gmail.com"
    assert teacher.provider == "google"
    assert teacher.is_onboarded is False      # 학교급/지역 아직 없음
    assert auth_service.current_user(cookie).id == teacher.id


def test_login_is_idempotent_by_auth_id():
    t1, _ = auth_service.establish_session(_google_token())
    t2, _ = auth_service.establish_session(_google_token(user_metadata={"full_name": "김서연B"}))
    assert t1.id == t2.id            # 같은 sub → 같은 교사
    assert t2.name == "김서연B"      # 이름은 최신화


def test_kakao_login_sets_provider():
    token = make_token(
        sub="kakao-1", app_metadata={"provider": "kakao"},
        user_metadata={"name": "박지우", "avatar_url": None},
    )
    teacher, _ = auth_service.establish_session(token)
    assert teacher.provider == "kakao"
    assert teacher.name == "박지우"


def test_invalid_signature_rejected():
    bad = make_token(secret="wrong-secret")
    with pytest.raises(AuthError):
        auth_service.establish_session(bad)


def test_expired_token_rejected():
    with pytest.raises(AuthError):
        auth_service.establish_session(_google_token(exp_delta=-10))


def test_current_user_none_for_bad_cookie():
    assert auth_service.current_user(None) is None
    assert auth_service.current_user("garbage.cookie.value") is None


def test_onboarding_completes_profile():
    member, _ = auth_service.establish_session(_google_token())
    done = auth_service.complete_onboarding(member.id, "PM", "3~5년", "커머스")
    assert done.is_onboarded is True
    assert done.job_role == "PM" and done.years == "3~5년"
    assert done.industry == "커머스"


def test_onboarding_rejects_bad_values():
    member, _ = auth_service.establish_session(_google_token())
    with pytest.raises(AuthError):
        auth_service.complete_onboarding(member.id, "사장", "3~5년", "커머스")
    with pytest.raises(AuthError):
        auth_service.complete_onboarding(member.id, "PM", "20년", "커머스")
    with pytest.raises(AuthError):
        auth_service.complete_onboarding(member.id, "PM", "3~5년", "우주")
