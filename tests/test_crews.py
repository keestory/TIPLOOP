"""크루 테스트 — 생성·초대 합류·주간 기록·참여 현황·알림."""

import pytest

from app.service import crew_service
from app.service import notification_service as N
from app.service.crew_service import CrewError


def test_create_crew_creator_is_member(make_member):
    m = make_member(name="리더")
    crew = crew_service.create_crew(m.id, "그로스 스터디", "리텐션")
    assert crew.name == "그로스 스터디"
    assert crew.member_count == 1
    assert len(crew.invite_code) >= 8


def test_create_requires_name(make_member):
    m = make_member()
    with pytest.raises(CrewError):
        crew_service.create_crew(m.id, "   ")


def test_join_by_code_and_idempotent(make_member):
    a = make_member()
    b = make_member()
    crew = crew_service.create_crew(a.id, "회고단")
    joined = crew_service.join_by_code(b.id, crew.invite_code)
    assert joined.id == crew.id
    again = crew_service.join_by_code(b.id, crew.invite_code)  # 중복 합류 무해
    assert again.member_count == 2
    with pytest.raises(CrewError):
        crew_service.join_by_code(b.id, "no-such-code")


def test_join_rejects_full_crew(make_member, monkeypatch):
    monkeypatch.setattr(crew_service, "CREW_MAX_MEMBERS", 2)
    a, b, c = make_member(), make_member(), make_member()
    crew = crew_service.create_crew(a.id, "꽉찬 크루")
    crew_service.join_by_code(b.id, crew.invite_code)
    with pytest.raises(CrewError):
        crew_service.join_by_code(c.id, crew.invite_code)


def test_entry_updates_participation_and_notifies(make_member):
    a = make_member(name="리더")
    b = make_member(name="멤버")
    crew = crew_service.create_crew(a.id, "위클리")
    crew_service.join_by_code(b.id, crew.invite_code)

    crew_service.add_entry(crew.id, a.id, "이번 주 배움: 코호트부터")
    home = crew_service.crew_home(crew.id, b.id)
    assert home["me_done"] is False
    assert [m["done"] for m in home["members"]] == [True, False]
    assert len(home["entries"]) == 1

    # 크루원(b)에게만 알림 — 본인(a) 제외
    assert any(n.kind == "crew" and n.crew_id == crew.id for n in N.list_recent(b.id))
    assert N.unread_count(a.id) == 0


def test_entry_validation_and_membership(make_member):
    a = make_member()
    outsider = make_member()
    crew = crew_service.create_crew(a.id, "크루")
    with pytest.raises(CrewError):
        crew_service.add_entry(crew.id, a.id, "  ")
    with pytest.raises(CrewError):
        crew_service.add_entry(crew.id, a.id, "가" * 301)
    with pytest.raises(CrewError):
        crew_service.add_entry(crew.id, outsider.id, "저는 멤버가 아니에요")


def test_crew_home_hidden_from_non_member(make_member):
    a = make_member()
    outsider = make_member()
    crew = crew_service.create_crew(a.id, "비공개")
    with pytest.raises(CrewError):
        crew_service.crew_home(crew.id, outsider.id)


def test_prompt_rotates_weekly():
    p1 = crew_service.prompt_for(1, "2026-W28")
    assert p1 == crew_service.prompt_for(1, "2026-W28")   # 같은 주 → 같은 질문
    assert p1 != crew_service.prompt_for(1, "2026-W29")   # 주가 바뀌면 로테이션


def test_full_streak_counts_consecutive_full_weeks(make_member):
    from datetime import date, timedelta
    from app.repo import crews as crews_repo

    a = make_member()
    b = make_member()
    crew = crew_service.create_crew(a.id, "스트릭")
    crew_service.join_by_code(b.id, crew.invite_code)

    today = date.today()
    wk = crew_service.current_week
    # 지난 2주 전원 참여 + 이번 주 미완 → 스트릭 2 (진행 중인 주는 미포함)
    for back in (1, 2):
        week = wk(today - timedelta(days=7 * back))
        crews_repo.add_entry(crew.id, a.id, week, "a")
        crews_repo.add_entry(crew.id, b.id, week, "b")
    assert crew_service.full_streak(crew.id, 2, today) == 2

    # 이번 주도 전원 참여하면 3
    crew_service.add_entry(crew.id, a.id, "a 이번주")
    crew_service.add_entry(crew.id, b.id, "b 이번주")
    assert crew_service.full_streak(crew.id, 2, today) == 3

    # 3주 전은 한 명만 → 스트릭은 3에서 멈춘다
    old = wk(today - timedelta(days=21))
    crews_repo.add_entry(crew.id, a.id, old, "혼자")
    assert crew_service.full_streak(crew.id, 2, today) == 3


def test_my_entry_only_returns_own(make_member):
    a = make_member()
    b = make_member()
    crew = crew_service.create_crew(a.id, "발행")
    eid = crew_service.add_entry(crew.id, a.id, "발행할 조각")
    assert crew_service.my_entry(eid, a.id).body == "발행할 조각"
    assert crew_service.my_entry(eid, b.id) is None       # 남의 조각은 안 줌
    assert crew_service.my_entry(99999, a.id) is None


def test_weekly_nudge_targets_only_laggards_once(make_member):
    a = make_member(name="부지런")
    b = make_member(name="미참여")
    solo = make_member(name="혼자")
    crew = crew_service.create_crew(a.id, "넛지")
    crew_service.join_by_code(b.id, crew.invite_code)
    crew_service.create_crew(solo.id, "1인 크루")     # 혼자인 크루는 제외
    crew_service.add_entry(crew.id, a.id, "이번 주 기록")

    assert crew_service.send_weekly_nudges() == 1      # b에게만
    items = [n for n in N.list_recent(b.id) if n.kind == "crew_nudge"]
    assert len(items) == 1 and items[0].crew_id == crew.id
    assert crew_service.send_weekly_nudges() == 0      # 같은 주 중복 발송 없음
    assert not any(n.kind == "crew_nudge" for n in N.list_recent(a.id))
    assert not any(n.kind == "crew_nudge" for n in N.list_recent(solo.id))


def test_my_crews_summary(make_member):
    a = make_member()
    crew = crew_service.create_crew(a.id, "요약")
    crew_service.add_entry(crew.id, a.id, "한 줄")
    (s,) = crew_service.my_crews(a.id)
    assert s["crew"].id == crew.id
    assert s["done"] == 1 and s["total"] == 1 and s["me_done"] is True
    assert s["prompt"]
