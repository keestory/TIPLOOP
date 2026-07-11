"""공유 카드 도메인 로직 — 인스타 스토리 등에 자랑할 성취를 카드 스펙으로 변환.

실제 렌더링(캔버스 애니메이션·영상/이미지 추출)은 프론트(static/share-card.js)가
담당한다. 여기서는 순수 데이터 조립만 한다 — 도메인 객체를 화면이 그대로
그릴 수 있는 평평한 dict(숫자·헤드라인·서브텍스트)로 바꾼다.
"""

from __future__ import annotations

from app.types.models import Crew, Post, User

_CATEGORY_LABEL = {"tip": "팁", "reference": "레퍼런스", "question": "질문", "retro": "회고"}


def post_card(post: Post) -> dict:
    """글 임팩트 카드 — '이 팁, N명에게 도움이 됐어요'."""
    label = _CATEGORY_LABEL.get(post.category, post.category)
    return {
        "kind": "post",
        "eyebrow": f"티핑 · {label}",
        "big": post.helpful_count,
        "unit": "명에게 도움",
        "headline": post.title,
        "sub": f"{post.author_name} 님의 글" if post.author_name else "",
    }


def profile_card(user: User, helpful_count: int) -> dict:
    """프로필 임팩트 카드 — '나는 N명에게 도움을 줬어요'."""
    sub_parts = [p for p in (user.job_role, user.years) if p]
    return {
        "kind": "profile",
        "eyebrow": "티핑",
        "big": helpful_count,
        "unit": "명에게 도움을 줬어요",
        "headline": user.name,
        "sub": " · ".join(sub_parts),
    }


def crew_card(crew: Crew, streak: int, prompt: str) -> dict:
    """크루 스트릭 카드 — '🔥 N주 연속 전원 참여'."""
    return {
        "kind": "crew",
        "eyebrow": f"티핑 크루 · {crew.name}",
        "big": streak,
        "unit": "주 연속 전원 참여",
        "headline": prompt,
        "sub": f"멤버 {crew.member_count}명",
    }
