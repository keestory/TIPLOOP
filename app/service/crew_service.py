"""크루 도메인 로직 — 함께 쓰는 주간 기록과 넛지 (셋로그식).

작은 그룹(2~12명)이 매주 같은 프롬프트에 한 줄씩 남기면
그 주의 '크루 로그'가 완성된다. 참여 도트가 서로를 은은하게 당긴다.
"""

from __future__ import annotations

import secrets
from datetime import date, timedelta

from app.config.settings import CREW_MAX_MEMBERS, CREW_PROMPTS
from app.repo import crews, notifications
from app.types.models import Crew


class CrewError(ValueError):
    """크루 동작 실패. 메시지는 사용자에게 보여줄 수 있다."""


def current_week(today: date | None = None) -> str:
    """ISO 주 키 (예: 2026-W28). 월요일에 주가 바뀐다."""
    today = today or date.today()
    year, week, _ = today.isocalendar()
    return f"{year}-W{week:02d}"


def prompt_for(crew_id: int, week: str) -> str:
    """이번 주 프롬프트 — 주가 바뀌면 자동 로테이션, 크루마다 다른 질문."""
    week_num = int(week.split("-W")[1])
    return CREW_PROMPTS[(crew_id + week_num) % len(CREW_PROMPTS)]


def full_streak(crew_id: int, total: int, today: date | None = None) -> int:
    """연속 '전원 참여' 주 수 (🔥 게임화). 진행 중인 이번 주는 완주 시에만 포함.

    멤버가 없거나 기록이 없으면 0. 최대 52주까지 거슬러 본다.
    """
    if total <= 0:
        return 0
    today = today or date.today()
    streak = 0
    if len(crews.participant_ids(crew_id, current_week(today))) >= total:
        streak += 1
    day = today - timedelta(days=7)
    for _ in range(52):
        if len(crews.participant_ids(crew_id, current_week(day))) >= total:
            streak += 1
            day -= timedelta(days=7)
        else:
            break
    return streak


def create_crew(creator_id: int, name: str, topic: str = "") -> Crew:
    name = (name or "").strip()
    if not name:
        raise CrewError("크루 이름을 입력해 주세요.")
    invite_code = secrets.token_urlsafe(6)
    return crews.create(name[:40], (topic or "").strip()[:20] or None, invite_code, creator_id)


def join_by_code(member_id: int, invite_code: str) -> Crew:
    """초대 링크로 합류. 이미 멤버면 그대로 통과(멱등)."""
    crew = crews.get_by_code(invite_code)
    if crew is None:
        raise CrewError("초대 링크가 유효하지 않습니다.")
    if crews.is_member(crew.id, member_id):
        return crew
    if crew.member_count >= CREW_MAX_MEMBERS:
        raise CrewError(f"크루 정원({CREW_MAX_MEMBERS}명)이 가득 찼습니다.")
    crews.add_member(crew.id, member_id)
    return crew


def my_crews(member_id: int) -> list[dict]:
    """홈 넛지 카드용 — 크루별 이번 주 참여 현황과 프롬프트."""
    week = current_week()
    summaries = []
    for crew in crews.list_for_member(member_id):
        done = crews.participant_ids(crew.id, week)
        summaries.append({
            "crew": crew,
            "prompt": prompt_for(crew.id, week),
            "done": len(done),
            "total": crew.member_count,
            "me_done": member_id in done,
            "streak": full_streak(crew.id, crew.member_count),
        })
    return summaries


def crew_home(crew_id: int, viewer_id: int) -> dict:
    """크루 홈 — 이번 주 프롬프트·참여 도트·기록, 지난 주 로그."""
    crew = crews.get(crew_id)
    if crew is None or not crews.is_member(crew_id, viewer_id):
        raise CrewError("크루를 찾을 수 없습니다.")
    week = current_week()
    done = crews.participant_ids(crew_id, week)
    members = [{**m, "done": m["id"] in done} for m in crews.members_of(crew_id)]
    past = [
        {"week": w, "prompt": prompt_for(crew_id, w), "entries": crews.entries(crew_id, w)}
        for w in crews.recent_weeks(crew_id, 5)
        if w != week
    ]
    return {
        "crew": crew, "week": week, "prompt": prompt_for(crew_id, week),
        "members": members, "entries": crews.entries(crew_id, week),
        "me_done": viewer_id in done, "past": past[:3],
        "streak": full_streak(crew_id, crew.member_count),
    }


def send_weekly_nudges() -> int:
    """주간 마감 넛지 (크론) — 이번 주 미참여 크루원에게 알림. 보낸 수를 돌려준다.

    이미 이번 주에 넛지를 받았거나, 혼자인 크루(기다리는 사람 없음)는 건너뛴다.
    """
    week = current_week()
    sent = 0
    for crew in crews.list_all():
        if crew.member_count < 2:
            continue
        done = crews.participant_ids(crew.id, week)
        if not done:  # 아무도 안 남긴 크루는 '기다리는 사람'이 없다
            continue
        for uid in crews.member_ids(crew.id):
            if uid in done or notifications.crew_nudge_sent_this_week(uid, crew.id):
                continue
            notifications.create(uid, "crew_nudge", topic=crew.name, crew_id=crew.id)
            sent += 1
    return sent


def my_entry(entry_id: int, viewer_id: int):
    """글 발행용 — 내가 쓴 조각만 돌려준다. 아니면 None."""
    entry = crews.get_entry(entry_id)
    if entry is None or entry.author_id != viewer_id:
        return None
    return entry


def add_entry(crew_id: int, author_id: int, body: str) -> int:
    """이번 주 기록 한 조각. 크루원들에게 알림(사회적 당김)."""
    body = (body or "").strip()
    if not body:
        raise CrewError("내용을 입력해 주세요.")
    if len(body) > 300:
        raise CrewError("300자 이내로 남겨 주세요.")
    crew = crews.get(crew_id)
    if crew is None or not crews.is_member(crew_id, author_id):
        raise CrewError("크루 멤버만 남길 수 있습니다.")
    entry_id = crews.add_entry(crew_id, author_id, current_week(), body)
    for uid in crews.member_ids(crew_id):
        notifications.create(uid, "crew", actor_id=author_id, topic=crew.name, crew_id=crew_id)
    return entry_id
