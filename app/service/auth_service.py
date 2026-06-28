"""인증 도메인 로직 — 가입·로그인·로그아웃·현재 사용자.

경계에서 입력을 검증한다. 실패는 ValueError로 알린다.
"""

from __future__ import annotations


import sqlite3

from app.config.settings import REGIONS, SCHOOL_LEVELS
from app.providers.security import generate_token, hash_password, verify_password
from app.repo import sessions, users
from app.types.models import User


class AuthError(ValueError):
    """가입/로그인 실패. 메시지는 사용자에게 보여줄 수 있다."""


def register(
    email: str, password: str, name: str, school_level: str, region: str, subject: str
) -> tuple[User, str]:
    """가입 후 (사용자, 세션 토큰)을 돌려준다."""
    email = (email or "").strip().lower()
    name = (name or "").strip()
    subject = (subject or "").strip()

    if "@" not in email or "." not in email:
        raise AuthError("올바른 이메일을 입력해 주세요.")
    if len(password or "") < 8:
        raise AuthError("비밀번호는 8자 이상이어야 합니다.")
    if not name:
        raise AuthError("이름을 입력해 주세요.")
    if school_level not in SCHOOL_LEVELS:
        raise AuthError("학교급을 선택해 주세요.")
    if region not in REGIONS:
        raise AuthError("지역을 선택해 주세요.")

    try:
        user = users.create_user(email, hash_password(password), name, school_level, region, subject)
    except sqlite3.IntegrityError as exc:
        raise AuthError("이미 가입된 이메일입니다.") from exc

    token = _start_session(user.id)
    return user, token


def login(email: str, password: str) -> tuple[User, str]:
    """로그인 후 (사용자, 세션 토큰)을 돌려준다."""
    email = (email or "").strip().lower()
    found = users.get_credentials_by_email(email)
    if not found or not verify_password(password or "", found[1]):
        raise AuthError("이메일 또는 비밀번호가 올바르지 않습니다.")
    user = found[0]
    return user, _start_session(user.id)


def logout(token: str | None) -> None:
    if token:
        sessions.delete_session(token)


def current_user(token: str | None) -> User | None:
    """세션 토큰으로 현재 사용자를 찾는다. 없으면 None."""
    if not token:
        return None
    user_id = sessions.get_user_id(token)
    if user_id is None:
        return None
    return users.get_user(user_id)


def _start_session(user_id: int) -> str:
    token = generate_token()
    sessions.create_session(token, user_id)
    return token
