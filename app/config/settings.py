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

# 글쓰기 템플릿 — 유형별 안내 섹션. 여러 칸을 하나의 body로 합쳐 저장한다.
# hl=True 이면 "결과는 숫자로" 처럼 형광펜 강조로 임팩트 신호를 유도.
WRITE_TEMPLATES = {
    "tip": [
        {"label": "상황", "hint": "어떤 맥락이었나요?", "ph": "예: 결제 전환율이 정체돼 있었어요"},
        {"label": "팁", "hint": "무엇을 하면 되나요?", "ph": "핵심 방법을 적어주세요"},
        {"label": "결과", "hint": "숫자로 남기면 후기가 붙어요", "ph": "예: 이탈률 12% ↓", "hl": True},
    ],
    "reference": [
        {"label": "무엇을 봤나요", "hint": "서비스·아티클·사례", "ph": "예: 토스 온보딩 플로우"},
        {"label": "핵심 인사이트", "hint": "내 일에 어떻게 적용할까", "ph": "배운 점과 적용 아이디어", "hl": True},
    ],
    "question": [
        {"label": "상황", "hint": "어떤 걸 겪고 있나요?", "ph": "배경을 적어주세요"},
        {"label": "궁금한 점", "hint": "무엇이 가장 알고 싶나요?", "ph": "구체적으로 물으면 좋은 답이 와요", "hl": True},
    ],
    "retro": [
        {"label": "상황", "hint": "무엇을 했나요?", "ph": "프로젝트·실험 개요"},
        {"label": "잘한 것", "hint": "효과가 있었던 것", "ph": ""},
        {"label": "아쉬운 것 · 배운 것", "hint": "다음엔 이렇게", "ph": "", "hl": True},
    ],
}


def category_label(code: str) -> str:
    """카테고리 코드의 한글 라벨. 모르는 값은 그대로 돌려준다."""
    return CATEGORIES.get(code, code)
