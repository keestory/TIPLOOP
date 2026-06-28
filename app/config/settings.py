"""환경 설정과 도메인 상수.

Types만 import 가능. 시크릿·연결정보는 환경 변수에서만 읽는다.
"""

from __future__ import annotations

import os

# ── Supabase / Postgres ──────────────────────────────────────────────
# 전부 Supabase로 이전: 데이터는 Supabase Postgres, 인증은 Supabase Auth.
DATABASE_URL = os.environ.get("DATABASE_URL", "")  # Supabase Postgres 연결 문자열

# 프론트(supabase-js)에서 OAuth를 시작할 때 필요 — 공개 값
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
# 백엔드에서 액세스 토큰(JWT, HS256)을 검증할 때 쓰는 프로젝트 시크릿
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")

# ── 세션 (우리 자체 서명 쿠키) ──────────────────────────────────────
SESSION_COOKIE = "ieum_session"
SESSION_SECRET = os.environ.get("IEUM_SECRET", "dev-only-change-me")
SESSION_TTL_DAYS = 14

# ── 도메인 상수 — 화면과 검증에서 공유 ──────────────────────────────
SCHOOL_LEVELS = ["유치원", "초등학교", "중학교", "고등학교"]

REGIONS = [
    "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
    "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
]

# 카테고리: 코드값 → 한글 라벨 (글이 세 기능을 통합)
CATEGORIES = {
    "info": "정보공유",
    "seminar": "세미나",
    "support": "고민나눔",
}

# 소셜 로그인 제공자
PROVIDERS = ["google", "kakao"]


def category_label(code: str) -> str:
    """카테고리 코드의 한글 라벨. 모르는 값은 그대로 돌려준다."""
    return CATEGORIES.get(code, code)
