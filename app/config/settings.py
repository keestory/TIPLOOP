"""환경 설정과 도메인 상수.

Types만 import 가능. 시크릿·연결정보는 환경 변수에서만 읽는다.
"""

from __future__ import annotations

import os
from pathlib import Path

# .env 자동 로딩 (있으면) — 매번 export 하지 않아도 되도록
try:
    from dotenv import load_dotenv

    _env_file = Path(__file__).resolve().parents[2] / ".env"
    if _env_file.exists():
        load_dotenv(_env_file)
except ImportError:
    pass

# ── 브랜드 ────────────────────────────────────────────────────────────
BRAND = "티핑"
TAGLINE = "실무 팁과 레퍼런스를 쌓고 나누는 곳"

# ── Supabase / Postgres ──────────────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL", "")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")

# ── 세션 (자체 서명 쿠키) ────────────────────────────────────────────
SESSION_COOKIE = "tipping_session"
SESSION_SECRET = os.environ.get("IEUM_SECRET", "dev-only-change-me")
SESSION_TTL_DAYS = 14

# ── 도메인 상수 — 화면과 검증에서 공유 ──────────────────────────────
# 온보딩에서 받는 프로필 (소셜이 주지 않는 값)
JOB_ROLES = ["PM", "개발", "디자인", "마케팅", "데이터", "기획", "MD", "운영", "기타"]
YEARS = ["1년 미만", "1~3년", "3~5년", "5~10년", "10년+"]
INDUSTRIES = ["커머스", "핀테크", "SaaS", "콘텐츠·미디어", "광고·마케팅", "교육", "게임", "기타"]

# 온보딩 2단계 — 관심 주제(피드 개인화 씨앗). 게이트가 아닌 추가 신호.
TOPICS = [
    "리텐션", "퍼널 분석", "체크아웃", "CS 자동화", "SQL",
    "A/B 테스트", "온보딩", "광고 효율", "가격 실험", "리서치",
]

# 글 카테고리: 코드값 → 한글 라벨
CATEGORIES = {
    "tip": "팁",
    "reference": "레퍼런스",
    "question": "질문",
    "retro": "회고",
}

# 소셜 로그인 제공자
PROVIDERS = ["google", "kakao"]


def category_label(code: str) -> str:
    """카테고리 코드의 한글 라벨. 모르는 값은 그대로 돌려준다."""
    return CATEGORIES.get(code, code)
