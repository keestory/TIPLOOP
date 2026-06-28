"""인증 서비스 단위 테스트."""

import pytest

from app.service import auth_service
from app.service.auth_service import AuthError


def _register():
    return auth_service.register(
        "kim@school.kr", "password123", "김선생", "중학교", "서울", "과학"
    )


def test_register_then_current_user():
    user, token = _register()
    assert user.email == "kim@school.kr"
    assert user.school_level == "중학교"
    assert auth_service.current_user(token).id == user.id


def test_register_rejects_short_password():
    with pytest.raises(AuthError):
        auth_service.register("a@b.kr", "short", "이름", "초등학교", "부산", "")


def test_register_rejects_bad_school_level():
    with pytest.raises(AuthError):
        auth_service.register("a@b.kr", "password123", "이름", "대학교", "부산", "")


def test_register_rejects_duplicate_email():
    _register()
    with pytest.raises(AuthError):
        _register()


def test_login_success_and_failure():
    _register()
    user, token = auth_service.login("kim@school.kr", "password123")
    assert auth_service.current_user(token).id == user.id
    with pytest.raises(AuthError):
        auth_service.login("kim@school.kr", "wrong-password")


def test_logout_invalidates_session():
    _, token = _register()
    auth_service.logout(token)
    assert auth_service.current_user(token) is None


def test_current_user_none_for_missing_token():
    assert auth_service.current_user(None) is None
    assert auth_service.current_user("nope") is None
