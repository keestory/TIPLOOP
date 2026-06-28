"""데모 데이터 시드 — 로컬에서 이음을 둘러볼 때 빈 화면을 피한다.

    DATABASE_URL=... python3 scripts/seed_demo.py

인증(구글/카카오)은 외부 Supabase가 맡으므로, 여기선 교사 프로필을 직접 만들어
글·세미나·댓글·공감 예시를 채운다. 같은 auth_id는 갱신만 하므로 재실행도 안전.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.repo import teachers
from app.repo.database import init_db
from app.service import community_service as C
from app.service import reaction_service as R

TEACHERS = [
    ("seed-kim", "김서연", "google", "중학교", "서울", "과학"),
    ("seed-lee", "이도현", "kakao", "고등학교", "부산", "진로"),
    ("seed-park", "박지우", "google", "초등학교", "경기", "3학년 담임"),
    ("seed-jung", "정민호", "kakao", "유치원", "대구", "유아"),
]


def _seed_teacher(auth_id, name, provider, level, region, subject):
    t = teachers.upsert_by_auth(
        auth_id=auth_id, name=name, email=f"{auth_id}@example.kr",
        avatar_url=None, provider=provider, phone=None, phone_verified=False,
    )
    return teachers.complete_profile(t.id, level, region, subject, "")


def main() -> None:
    init_db()
    kim, lee, park, jung = (_seed_teacher(*row) for row in TEACHERS)

    s1 = C.create_post(
        kim.id, "seminar", "온라인 수업도구 워크숍 — 함께 배우는 에듀테크",
        "요즘 쓰는 도구들을 직접 시연하며 나눕니다. 초보 환영!",
        event_at="7/12 (토) 14:00", location="서울교육연수원 3층",
        online_url="https://meet.example.kr/edutech",
    )
    c1 = C.add_comment(s1, lee.id, "부산에서도 온라인으로 참여 가능할까요? 너무 좋네요.")
    C.add_comment(s1, kim.id, "네! 온라인 링크로 어디서든 참여 가능합니다 :)", parent_id=c1)
    C.add_comment(s1, park.id, "신청합니다! 초등에서도 쓸 만한 도구 있을까요?")
    for u in (lee, park, jung):
        R.toggle_post(s1, u.id)
    R.toggle_comment(c1, kim.id)
    R.toggle_comment(c1, park.id)

    i1 = C.create_post(
        lee.id, "info", "학교 밖 진로 변화, 이렇게 교실에 전달했어요",
        "변화의 속도가 빠른 진로 정보를 수업에 녹이는 방법을 정리했습니다.",
    )
    C.add_comment(i1, park.id, "자료 공유 감사합니다. 저도 적용해볼게요!")
    for u in (kim, park, jung):
        R.toggle_post(i1, u.id)

    su = C.create_post(
        park.id, "support", "학부모 상담이 너무 힘듭니다",
        "경계를 지키면서도 신뢰를 쌓는 법, 선배 선생님들 조언 구해요.",
    )
    C.add_comment(su, lee.id, "기록을 남기는 게 큰 도움이 됐어요.")
    R.toggle_post(su, lee.id)

    C.create_post(kim.id, "info", "과학 실험 안전 체크리스트 공유", "학기 초에 돌려쓰기 좋은 체크리스트입니다.")
    print("데모 데이터 시드 완료.")


if __name__ == "__main__":
    main()
