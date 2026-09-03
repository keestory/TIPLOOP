"""인증 도메인 로직 — Supabase 소셜 로그인 + 자체 세션 + 온보딩.

이메일/비밀번호는 없다. 구글과 준비 완료된 Apple로 로그인하고, 세션은 서명 쿠키로 유지한다.
"""

from __future__ import annotations

from app.config.settings import (
    INDUSTRIES,
    JOB_ROLES,
    PROVIDERS,
    SESSION_SECRET,
    SESSION_TTL_DAYS,
    SUPABASE_ANON_KEY,
    SUPABASE_URL,
    TOPICS,
    YEARS,
)
from app.providers import security
from app.providers.security import read_session, sign_session
from app.repo import members
from app.types.models import User

_TTL = SESSION_TTL_DAYS * 24 * 60 * 60


class AuthError(ValueError):
    """로그인/온보딩 실패. 메시지는 사용자에게 보여줄 수 있다."""


def _claim_name(claims: dict, meta: dict) -> str:
    for key in ("full_name", "name", "user_name", "nickname"):
        if meta.get(key):
            return str(meta[key])
    email = claims.get("email") or meta.get("email") or ""
    return email.split("@")[0] if email else "회원"


def establish_session(access_token: str) -> tuple[User, str]:
    """Supabase 액세스 토큰을 검증(=사용자 조회)하고 (회원, 세션 쿠키값)을 돌려준다."""
    info = security.fetch_supabase_user(access_token, SUPABASE_URL, SUPABASE_ANON_KEY)
    if not info or not info.get("id"):
        raise AuthError("로그인 정보를 확인하지 못했습니다. 다시 시도해 주세요.")

    meta = info.get("user_metadata") or {}
    app_meta = info.get("app_metadata") or {}
    provider = str(app_meta.get("provider") or "")
    if provider not in PROVIDERS:
        raise AuthError("현재 지원하지 않는 로그인 방식입니다.")

    member = members.upsert_by_auth(
        auth_id=str(info["id"]),
        name=_claim_name(info, meta),
        email=info.get("email") or meta.get("email"),
        avatar_url=meta.get("avatar_url") or meta.get("picture"),
        provider=provider,
    )
    return member, sign_session(member.id, SESSION_SECRET, _TTL)


def current_user(cookie: str | None) -> User | None:
    """세션 쿠키로 현재 회원을 찾는다. 없으면 None."""
    member_id = read_session(cookie, SESSION_SECRET)
    if member_id is None:
        return None
    return members.get(member_id)


def agree_terms(member_id: int) -> None:
    """약관·개인정보 동의를 저장한다(신규 가입 첫 단계)."""
    members.agree_terms(member_id)


def mark_tour_seen(member_id: int) -> None:
    """첫 로그인 코치마크 투어 시청 완료(또는 건너뛰기)를 저장한다."""
    members.mark_tour_seen(member_id)


def dismiss_checklist(member_id: int) -> None:
    """홈 시작 체크리스트 닫기를 저장한다(다시 안 뜸)."""
    members.dismiss_checklist(member_id)


def save_topics(member_id: int, topics: list[str]) -> User:
    """온보딩 1단계 — 관심 주제를 저장한다. 아는 주제만 통과시킨다(빈 값 허용)."""
    clean = [t for t in topics if t in TOPICS]
    return members.set_topics(member_id, clean)


def complete_onboarding(member_id: int, job_role: str, years: str, industry: str) -> User:
    """온보딩 — 소셜이 주지 않는 직군·연차·업종을 채운다."""
    if job_role not in JOB_ROLES:
        raise AuthError("직군을 선택해 주세요.")
    if years not in YEARS:
        raise AuthError("연차를 선택해 주세요.")
    if industry not in INDUSTRIES:
        raise AuthError("업종을 선택해 주세요.")
    return members.complete_profile(member_id, job_role, years, industry)
