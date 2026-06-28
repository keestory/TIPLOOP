"""인증 도메인 로직 — Supabase 소셜 로그인 + 자체 세션 + 온보딩.

이메일/비밀번호는 없다. 구글·카카오로만 로그인하고, 세션은 서명 쿠키로 유지한다.
"""

from __future__ import annotations

from app.config.settings import (
    REGIONS,
    SCHOOL_LEVELS,
    SESSION_SECRET,
    SESSION_TTL_DAYS,
    SUPABASE_JWT_SECRET,
)
from app.providers.security import read_session, sign_session, verify_supabase_jwt
from app.repo import teachers
from app.types.models import User

_TTL = SESSION_TTL_DAYS * 24 * 60 * 60


class AuthError(ValueError):
    """로그인/온보딩 실패. 메시지는 사용자에게 보여줄 수 있다."""


def _claim_name(claims: dict, meta: dict) -> str:
    for key in ("full_name", "name", "user_name", "nickname"):
        if meta.get(key):
            return str(meta[key])
    email = claims.get("email") or meta.get("email") or ""
    return email.split("@")[0] if email else "선생님"


def establish_session(access_token: str) -> tuple[User, str]:
    """Supabase 액세스 토큰을 검증하고 (교사, 세션 쿠키값)을 돌려준다."""
    claims = verify_supabase_jwt(access_token, SUPABASE_JWT_SECRET)
    if not claims or not claims.get("sub"):
        raise AuthError("로그인 정보를 확인하지 못했습니다. 다시 시도해 주세요.")

    meta = claims.get("user_metadata") or {}
    app_meta = claims.get("app_metadata") or {}
    phone = claims.get("phone") or meta.get("phone_number") or meta.get("phone") or None
    provider = app_meta.get("provider")
    # 카카오는 동의항목으로 검증된 번호를 준다 → verified 처리
    phone_verified = bool(claims.get("phone_verified") or (provider == "kakao" and phone))

    teacher = teachers.upsert_by_auth(
        auth_id=str(claims["sub"]),
        name=_claim_name(claims, meta),
        email=claims.get("email") or meta.get("email"),
        avatar_url=meta.get("avatar_url") or meta.get("picture"),
        provider=provider,
        phone=phone,
        phone_verified=phone_verified,
    )
    return teacher, sign_session(teacher.id, SESSION_SECRET, _TTL)


def current_user(cookie: str | None) -> User | None:
    """세션 쿠키로 현재 교사를 찾는다. 없으면 None."""
    teacher_id = read_session(cookie, SESSION_SECRET)
    if teacher_id is None:
        return None
    return teachers.get(teacher_id)


def complete_onboarding(
    teacher_id: int, school_level: str, region: str, subject: str, phone: str
) -> User:
    """온보딩 — 소셜이 주지 않는 학교급·지역·담당(+필요 시 전화번호)을 채운다."""
    if school_level not in SCHOOL_LEVELS:
        raise AuthError("학교급을 선택해 주세요.")
    if region not in REGIONS:
        raise AuthError("지역을 선택해 주세요.")
    return teachers.complete_profile(
        teacher_id, school_level, region, (subject or "").strip(), (phone or "").strip()
    )
