"""개인 서비스 연구 노트 도메인 로직.

기존 posts 테이블의 ``reference`` 카테고리를 재사용하되, 모든 조회와 수정은
작성자 id를 조건으로 삼는다. 공개 커뮤니티 기능과 개인 노트 경계를 분리하기
위해 라우트는 이 모듈만 사용한다.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from app.config.settings import (
    REFERENCE_ANALYSIS_MODES,
    REFERENCE_QUESTION_IDS,
    REFERENCE_QUICK_QUESTION_IDS,
    REFERENCE_REQUIRED_FINAL_ID,
    REFERENCE_TEMPLATE_VERSION,
    WRITE_TEMPLATES,
)
from app.repo import posts
from app.service import research_media_service, research_presenter
from app.types.models import MediaAttachment, Post


class ResearchError(ValueError):
    """연구 노트 동작 실패. 메시지는 사용자에게 보여줄 수 있다."""


attachment_dicts = research_media_service.attachment_dicts
section_values = research_presenter.section_values
legacy_preamble = research_presenter.legacy_preamble
detail_groups = research_presenter.detail_groups
progress = research_presenter.progress
present_notes = research_presenter.present_notes


def parse_attachments(payload: str, user_auth_id: str) -> tuple[MediaAttachment, ...]:
    """첨부 검증 오류를 연구 노트의 공개 오류 타입으로 통일한다."""
    try:
        return research_media_service.parse_attachments(payload, user_auth_id)
    except research_media_service.ResearchMediaError as exc:
        raise ResearchError(str(exc)) from exc


def list_notes(user_id: int, search: str = "") -> list[Post]:
    """내 서비스 분석 노트를 최신순으로 찾는다."""
    return posts.list_posts(
        category="reference",
        author_id=user_id,
        search=search.strip() or None,
        sort="new",
    )


def list_actionable_notes(user_id: int, search: str = "") -> list[Post]:
    """`실제로 적용할 것`을 적은 내 노트만 돌려준다."""
    return [
        post
        for post in list_notes(user_id, search)
        if section_values(post.body).get("실제로 적용할 것", "")
    ]


def get_note(post_id: int, user_id: int) -> Post:
    """내 서비스 분석 노트 한 건. 없거나 남의 글이면 같은 오류를 낸다."""
    post = posts.get_owned_post(post_id, user_id)
    if post is None or post.category != "reference":
        raise ResearchError("연구 노트를 찾을 수 없습니다.")
    return post


def get_owned_record(post_id: int, user_id: int) -> Post:
    """이전 카테고리를 포함해 작성자 본인의 기록만 가져온다."""
    post = posts.get_owned_post(post_id, user_id)
    if post is None:
        raise ResearchError("기록을 찾을 수 없습니다.")
    return post


def create_note(
    user_id: int,
    title: str,
    body: str,
    link_url: str = "",
    analysis_mode: str = "quick",
    selected_question_ids: tuple[str, ...] = REFERENCE_QUICK_QUESTION_IDS,
    attachments_json: str = "[]",
    user_auth_id: str = "",
) -> int:
    """검증 후 개인 서비스 분석 노트를 만든다."""
    title, body, link_url = _clean(title, body, link_url)
    analysis_mode, selected_question_ids = normalize_analysis_selection(
        analysis_mode, selected_question_ids, body
    )
    attachments = parse_attachments(attachments_json, user_auth_id)
    _verify_attachments(attachments, user_auth_id)
    return posts.create_post(
        author_id=user_id,
        category="reference",
        title=title,
        body=body,
        link_url=link_url or None,
        analysis_mode=analysis_mode,
        analysis_template_version=REFERENCE_TEMPLATE_VERSION,
        selected_question_ids=selected_question_ids,
        attachments=attachments,
    )


def update_note(
    post_id: int,
    user_id: int,
    title: str,
    body: str,
    link_url: str = "",
    analysis_mode: str = "full",
    selected_question_ids: tuple[str, ...] = REFERENCE_QUESTION_IDS,
    attachments_json: str | None = None,
    user_auth_id: str = "",
) -> None:
    """소유권을 SQL 조건으로 재검사해 노트를 수정한다."""
    title, body, link_url = _clean(title, body, link_url)
    analysis_mode, selected_question_ids = normalize_analysis_selection(
        analysis_mode, selected_question_ids, body
    )
    if attachments_json is None:
        existing = get_note(post_id, user_id)
        attachments = existing.attachments
    else:
        attachments = parse_attachments(attachments_json, user_auth_id)
        _verify_attachments(attachments, user_auth_id)
    if not posts.update_owned_post(
        post_id=post_id,
        author_id=user_id,
        title=title,
        body=body,
        link_url=link_url or None,
        analysis_mode=analysis_mode,
        analysis_template_version=REFERENCE_TEMPLATE_VERSION,
        selected_question_ids=selected_question_ids,
        attachments=attachments,
    ):
        raise ResearchError("연구 노트를 찾을 수 없습니다.")


def _clean(title: str, body: str, link_url: str) -> tuple[str, str, str]:
    title = (title or "").strip()
    body = (body or "").strip()
    link_url = (link_url or "").strip()
    if not title:
        raise ResearchError("서비스명을 입력해 주세요.")
    if not body:
        raise ResearchError("관찰 내용을 한 칸 이상 채워 주세요.")
    if link_url:
        parsed = urlsplit(link_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ResearchError("서비스 링크는 http:// 또는 https:// 주소를 입력해 주세요.")
    return title, body, link_url


def normalize_question_ids(question_ids: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    """제출된 질문 id를 검증하고 템플릿의 고정 순서로 정렬한다."""
    submitted = [str(question_id).strip() for question_id in (question_ids or ())]
    unknown = set(submitted) - set(REFERENCE_QUESTION_IDS)
    if unknown:
        raise ResearchError("알 수 없는 분석 질문이 포함되어 있어요. 다시 선택해 주세요.")
    selected = set(submitted)
    return tuple(question_id for question_id in REFERENCE_QUESTION_IDS if question_id in selected)


def _answered_question_ids(body: str) -> tuple[str, ...]:
    values = section_values(body)
    by_label = {
        section["label"]: section["id"] for section in WRITE_TEMPLATES["reference"]
    }
    return tuple(
        by_label[label] for label, value in values.items() if value and label in by_label
    )


def normalize_analysis_selection(
    analysis_mode: str,
    question_ids: tuple[str, ...] | list[str],
    body: str,
) -> tuple[str, tuple[str, ...]]:
    """프리셋 의미를 지키면서 이미 작성한 답변을 선택 밖으로 버리지 않는다."""
    mode = (analysis_mode or "").strip()
    if mode not in REFERENCE_ANALYSIS_MODES:
        raise ResearchError("분석 방식을 다시 선택해 주세요.")
    submitted = normalize_question_ids(question_ids)
    if mode == "quick":
        selected = set(REFERENCE_QUICK_QUESTION_IDS)
    elif mode == "full":
        selected = set(REFERENCE_QUESTION_IDS)
    else:
        selected = set(submitted)
        if not selected:
            raise ResearchError("답하고 싶은 질문을 한 개 이상 선택해 주세요.")
        selected.add(REFERENCE_REQUIRED_FINAL_ID)

    selected.update(_answered_question_ids(body))
    normalized = tuple(
        question_id for question_id in REFERENCE_QUESTION_IDS if question_id in selected
    )
    if normalized == REFERENCE_QUICK_QUESTION_IDS:
        mode = "quick"
    elif normalized == REFERENCE_QUESTION_IDS:
        mode = "full"
    else:
        mode = "focus"
    return mode, normalized


def _verify_attachments(
    attachments: tuple[MediaAttachment, ...], user_auth_id: str
) -> None:
    try:
        research_media_service.verify_attachments(attachments, user_auth_id)
    except research_media_service.ResearchMediaError as exc:
        raise ResearchError(str(exc)) from exc


def dashboard(user_id: int) -> dict:
    """홈 워크벤치용 최근 노트와 최소 지표."""
    items = list_notes(user_id)
    presented = present_notes(items)
    completed = sum(1 for item in presented if item["progress"]["percent"] == 100)
    applied = sum(
        1
        for post in items
        if section_values(post.body).get("실제로 적용할 것", "")
    )
    return {
        "notes": presented,
        "recent": presented[:5],
        "total": len(items),
        "completed": completed,
        "applied": applied,
    }
