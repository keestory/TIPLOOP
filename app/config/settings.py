"""환경 설정과 도메인 상수.

Types만 import 가능. 시크릿은 환경 변수에서만 읽는다.
"""

from __future__ import annotations


import os
from pathlib import Path

# DB 위치 — 환경 변수로 덮어쓸 수 있게, 기본은 저장소 내 파일
DB_PATH = os.environ.get("IEUM_DB_PATH", str(Path(__file__).resolve().parents[2] / "ieum.db"))

# 세션 쿠키
SESSION_COOKIE = "ieum_session"
SESSION_SECRET = os.environ.get("IEUM_SECRET", "dev-only-change-me")

# 비밀번호 해시 파라미터
PBKDF2_ITERATIONS = 200_000

# 도메인 상수 — 화면과 검증에서 공유
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


def category_label(code: str) -> str:
    """카테고리 코드의 한글 라벨. 모르는 값은 그대로 돌려준다."""
    return CATEGORIES.get(code, code)
