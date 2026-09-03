"""데모 데이터 시드 — 로컬에서 티핑을 둘러볼 때 빈 화면을 피한다.

    DATABASE_URL=... python3 scripts/seed_demo.py

인증(Google/Apple)은 외부 Supabase가 맡으므로, 여기선 회원 프로필을 직접 만들어
팁·레퍼런스·질문·회고 예시를 채운다. 같은 auth_id는 갱신만 하므로 재실행도 안전.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.repo import members
from app.repo.database import init_db
from app.service import community_service as C
from app.service import follow_service as F
from app.service import reaction_service as R

MEMBERS = [
    ("seed-jun", "김준", "google", "PM", "3~5년", "커머스"),
    ("seed-sora", "이소라", "google", "디자인", "5~10년", "SaaS"),
    ("seed-min", "박민", "google", "개발", "1~3년", "핀테크"),
    ("seed-hyun", "정현", "google", "마케팅", "5~10년", "콘텐츠·미디어"),
]


def _seed_member(auth_id, name, provider, job_role, years, industry):
    m = members.upsert_by_auth(
        auth_id=auth_id, name=name, email=f"{auth_id}@example.com",
        avatar_url=None, provider=provider,
    )
    return members.complete_profile(m.id, job_role, years, industry)


def main() -> None:
    init_db()
    jun, sora, minp, hyun = (_seed_member(*row) for row in MEMBERS)

    r1 = C.create_post(
        sora.id, "reference", "토스 온보딩 뜯어보기 — 마찰을 줄이는 3가지 장치",
        "토스 가입 플로우를 단계별로 캡처하며 분석했어요. 특히 '지금 안 해도 돼요' 패턴이 인상적.",
        link_url="https://toss.im",
    )
    c1 = C.add_comment(r1, jun.id, "이 패턴 우리 결제 플로우에도 적용해봤는데 이탈이 확 줄었어요.")
    C.add_comment(r1, sora.id, "오 결과 공유 가능하실까요? 수치가 궁금해요.", parent_id=c1)
    C.add_comment(r1, minp.id, "레퍼런스 정리 깔끔하네요. 저장!")
    for u in (jun, minp, hyun):
        R.toggle_post(r1, u.id)
    R.toggle_comment(c1, sora.id)
    R.toggle_comment(c1, hyun.id)

    t1 = C.create_post(
        jun.id, "tip", "커머스 A/B 테스트, 이 3가지만은 꼭 로깅하세요",
        "전환율만 보면 놓치는 게 많아요. 노출·클릭·장바구니·결제 단계별 퍼널을 다 남겨야 원인이 보입니다.",
    )
    C.add_comment(t1, hyun.id, "퍼널 단계 로깅 정말 중요… 뒤늦게 붙이느라 고생했어요.")
    for u in (sora, minp, hyun):
        R.toggle_post(t1, u.id)          # 공감
        R.toggle_helpful(t1, u.id)       # 도움됐어요
    C.add_review(t1, hyun.id, "이 퍼널 로깅대로 붙였더니 이탈 지점이 바로 보였어요. 결제 단계 이탈 -12%.")
    C.add_review(t1, minp.id, "장바구니 단계 로깅 추가했더니 원인 파악이 훨씬 빨라졌습니다.")

    q1 = C.create_post(
        minp.id, "question", "결제 실패 재시도, 어디까지 자동화하세요?",
        "카드사 오류일 때 자동 재시도 vs 사용자 안내, 다들 어떤 기준으로 나누시나요?",
    )
    C.add_comment(q1, jun.id, "저희는 네트워크성 오류만 1회 자동 재시도, 나머지는 안내로 분기해요.")
    R.toggle_post(q1, jun.id)

    C.create_post(
        hyun.id, "retro", "첫 라이브커머스 론칭 회고 — 잘한 것과 삽질",
        "3주 만에 붙인 라이브 방송 기능. 트래픽 예측을 너무 낙관했던 게 가장 큰 실수였어요.",
    )

    # 팔로우 — 프로필 지표와 팔로우 알림 예시
    F.toggle(sora.id, jun.id)
    F.toggle(minp.id, jun.id)
    F.toggle(jun.id, sora.id)

    print("데모 데이터 시드 완료.")


if __name__ == "__main__":
    main()
