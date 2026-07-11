"""공유 카드 도메인 로직 테스트 — 도메인 객체 → 카드 스펙 변환(순수 함수)."""

from app.service import share_service
from app.types.models import Crew, Post, User


def _post(**over):
    base = dict(
        id=1, author_id=1, category="tip", title="이탈률 12% 줄인 온보딩 팁",
        body="본문", created_at="2026-07-05", author_name="김PO",
        author_job_role="PM", author_years="3년", helpful_count=24,
    )
    base.update(over)
    return Post(**base)


def _user(**over):
    base = dict(
        id=1, auth_id="a1", name="박그로스", created_at="2026-01-01",
        job_role="그로스", years="6년",
    )
    base.update(over)
    return User(**base)


def _crew(**over):
    base = dict(
        id=1, name="그로스 스터디", invite_code="abc123",
        created_by=1, created_at="2026-07-01", topic="리텐션", member_count=3,
    )
    base.update(over)
    return Crew(**base)


def test_post_card_shape():
    card = share_service.post_card(_post())
    assert card["kind"] == "post"
    assert card["big"] == 24
    assert card["unit"] == "명에게 도움"
    assert card["headline"] == "이탈률 12% 줄인 온보딩 팁"
    assert card["eyebrow"] == "티핑 · 팁"
    assert "김PO" in card["sub"]


def test_post_card_unknown_category_falls_back_to_code():
    card = share_service.post_card(_post(category="weird"))
    assert card["eyebrow"] == "티핑 · weird"


def test_post_card_handles_missing_author_name():
    card = share_service.post_card(_post(author_name=None))
    assert card["sub"] == ""


def test_profile_card_shape():
    card = share_service.profile_card(_user(), 127)
    assert card["kind"] == "profile"
    assert card["big"] == 127
    assert card["unit"] == "명에게 도움을 줬어요"
    assert card["headline"] == "박그로스"
    assert card["sub"] == "그로스 · 6년"


def test_profile_card_handles_missing_job_fields():
    card = share_service.profile_card(_user(job_role=None, years=None), 3)
    assert card["sub"] == ""


def test_crew_card_shape():
    card = share_service.crew_card(_crew(), 4, "동료에게 추천하고 싶은 최근 읽은·본 것")
    assert card["kind"] == "crew"
    assert card["big"] == 4
    assert card["unit"] == "주 연속 전원 참여"
    assert card["eyebrow"] == "티핑 크루 · 그로스 스터디"
    assert card["sub"] == "멤버 3명"
