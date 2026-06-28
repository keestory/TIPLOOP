"""데모 데이터 시드 — 로컬에서 이음을 둘러볼 때 빈 화면을 피한다.

    python3 scripts/seed_demo.py

기존 데이터가 있으면 건드리지 않고 추가만 한다(이메일 중복은 건너뜀).
"""

from __future__ import annotations


import sqlite3
import sys
from pathlib import Path

# 저장소 루트를 import 경로에 추가 — 어느 위치에서 실행해도 동작하도록
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.repo.database import init_db
from app.service import auth_service as A
from app.service import community_service as C
from app.service import reaction_service as R
from app.service.auth_service import AuthError

TEACHERS = [
    ("kim@s.kr", "김서연", "중학교", "서울", "과학"),
    ("lee@s.kr", "이도현", "고등학교", "부산", "진로"),
    ("park@s.kr", "박지우", "초등학교", "경기", "3학년 담임"),
    ("jung@s.kr", "정민호", "유치원", "대구", "유아"),
]
PASSWORD = "password123"


def _register_all() -> dict[str, int]:
    """이메일 → user_id. 이미 있으면 로그인으로 id를 얻는다."""
    ids: dict[str, int] = {}
    for email, name, level, region, subject in TEACHERS:
        try:
            user, _ = A.register(email, PASSWORD, name, level, region, subject)
        except AuthError:
            user, _ = A.login(email, PASSWORD)
        ids[email] = user.id
    return ids


def main() -> None:
    init_db()
    try:
        ids = _register_all()
    except sqlite3.Error as exc:  # pragma: no cover - 진단용
        print(f"시드 실패: {exc}")
        return
    kim, lee, park, jung = (ids[e] for e in ("kim@s.kr", "lee@s.kr", "park@s.kr", "jung@s.kr"))

    s1 = C.create_post(
        kim, "seminar", "온라인 수업도구 워크숍 — 함께 배우는 에듀테크",
        "요즘 쓰는 도구들을 직접 시연하며 나눕니다. 초보 환영!",
        event_at="7/12 (토) 14:00", location="서울교육연수원 3층",
        online_url="https://meet.example.kr/edutech",
    )
    c1 = C.add_comment(s1, lee, "부산에서도 온라인으로 참여 가능할까요? 너무 좋네요.")
    C.add_comment(s1, kim, "네! 온라인 링크로 어디서든 참여 가능합니다 :)", parent_id=c1)
    C.add_comment(s1, park, "신청합니다! 초등에서도 쓸 만한 도구 있을까요?")
    for u in (lee, park, jung):
        R.toggle_post(s1, u)
    R.toggle_comment(c1, kim)
    R.toggle_comment(c1, park)

    i1 = C.create_post(
        lee, "info", "학교 밖 진로 변화, 이렇게 교실에 전달했어요",
        "변화의 속도가 빠른 진로 정보를 수업에 녹이는 방법을 정리했습니다.",
    )
    C.add_comment(i1, park, "자료 공유 감사합니다. 저도 적용해볼게요!")
    for u in (kim, park, jung):
        R.toggle_post(i1, u)

    su = C.create_post(
        park, "support", "학부모 상담이 너무 힘듭니다",
        "경계를 지키면서도 신뢰를 쌓는 법, 선배 선생님들 조언 구해요.",
    )
    C.add_comment(su, lee, "기록을 남기는 게 큰 도움이 됐어요.")
    R.toggle_post(su, lee)

    C.create_post(kim, "info", "과학 실험 안전 체크리스트 공유", "학기 초에 돌려쓰기 좋은 체크리스트입니다.")

    print("데모 데이터 시드 완료. 로그인: kim@s.kr / password123")


if __name__ == "__main__":
    main()
