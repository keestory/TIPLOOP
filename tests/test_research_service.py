"""TIPLOOP 개인 연구 노트 서비스 테스트."""

import json

import pytest

from app.config.settings import REFERENCE_QUESTION_IDS, REFERENCE_QUICK_QUESTION_IDS
from app.service import research_service
from app.service.research_service import ResearchError
from app.types.models import Post


@pytest.mark.no_db
def test_section_values_round_trip_and_progress():
    body = (
        "분석한 이유\n첫 줄\n둘째 줄\n\n"
        "핵심 기능과 흐름\n가입 뒤 바로 템플릿을 보여준다\n\n"
        "실제로 적용할 것\n다음 랜딩에서 가치 제안을 한 문장으로 줄인다"
    )
    values = research_service.section_values(body)
    assert values["분석한 이유"] == "첫 줄\n둘째 줄"
    assert values["핵심 기능과 흐름"] == "가입 뒤 바로 템플릿을 보여준다"
    assert values["실제로 적용할 것"].startswith("다음 랜딩")

    post = Post(
        id=1, author_id=1, category="reference", title="Notion",
        body=body, created_at="2026-09-01",
    )
    result = research_service.progress(post)
    assert result["done"] == 3
    assert result["total"] == 12
    assert result["percent"] == 25


@pytest.mark.no_db
def test_unknown_legacy_preamble_is_preserved():
    body = "옛날 라벨\n예전 내용\n\n기획과 UX\n좋은 흐름"
    values = research_service.section_values(body)
    assert values["기획과 UX"] == "좋은 흐름"
    assert research_service.legacy_preamble(body) == "옛날 라벨\n예전 내용"
    groups = research_service.detail_groups(body)
    assert groups[0]["name"] == "이전 메모"
    assert groups[0]["items"][0]["value"] == "옛날 라벨\n예전 내용"
    assert [group["name"] for group in groups] == ["이전 메모", "경험"]


@pytest.mark.no_db
def test_legacy_reference_sections_are_preserved_for_editing():
    body = "무엇을 봤나요\n토스 온보딩\n\n핵심 인사이트\n첫 성공 경험을 앞당긴다"
    values = research_service.section_values(body)
    assert values["분석한 이유"] == "토스 온보딩"
    assert values["가져올 아이디어"] == "첫 성공 경험을 앞당긴다"

    freeform = research_service.section_values("예전 자유 형식 메모")
    assert freeform["분석한 이유"] == "예전 자유 형식 메모"


@pytest.mark.no_db
def test_note_link_allows_only_http_urls():
    with pytest.raises(ResearchError):
        research_service._clean("서비스", "분석한 이유\n관찰", "javascript:alert(1)")
    title, body, link = research_service._clean(
        "서비스", "분석한 이유\n관찰", "https://example.com/path"
    )
    assert (title, body, link) == (
        "서비스", "분석한 이유\n관찰", "https://example.com/path"
    )


@pytest.mark.no_db
def test_question_selection_presets_and_focus_order():
    mode, selected = research_service.normalize_analysis_selection(
        "quick", (), "타깃과 문제\n사용자"
    )
    assert mode == "quick"
    assert selected == REFERENCE_QUICK_QUESTION_IDS

    mode, selected = research_service.normalize_analysis_selection(
        "focus", ("ref.business_model", "ref.planning_ux"),
        "비즈니스 모델\n구독",
    )
    assert mode == "focus"
    assert selected == (
        "ref.planning_ux", "ref.business_model", "ref.next_action"
    )

    mode, selected = research_service.normalize_analysis_selection("full", (), "분석한 이유\n관찰")
    assert mode == "full"
    assert selected == REFERENCE_QUESTION_IDS


@pytest.mark.no_db
def test_unknown_or_empty_focus_questions_are_rejected():
    with pytest.raises(ResearchError):
        research_service.normalize_analysis_selection("focus", (), "분석한 이유\n관찰")
    with pytest.raises(ResearchError):
        research_service.normalize_analysis_selection(
            "focus", ("ref.not_real",), "분석한 이유\n관찰"
        )


@pytest.mark.no_db
def test_quick_progress_uses_selected_question_count():
    post = Post(
        id=2,
        author_id=1,
        category="reference",
        title="서비스",
        body="타깃과 문제\n문제\n\n핵심 기능과 흐름\n흐름",
        created_at="2026-09-02",
        analysis_mode="quick",
        selected_question_ids=REFERENCE_QUICK_QUESTION_IDS,
    )
    assert research_service.progress(post) == {"done": 2, "total": 3, "percent": 67}


@pytest.mark.no_db
def test_attachment_metadata_requires_owned_private_path():
    payload = json.dumps([
        {
            "bucket": "tiploop-research-images",
            "path": "auth-user/drafts/12345678/abcdefgh.jpg",
            "kind": "image",
            "mime_type": "image/jpeg",
            "file_name": "화면 <1>.jpg",
            "size_bytes": 1024,
        }
    ])
    parsed = research_service.parse_attachments(payload, "auth-user")
    assert parsed[0].path.endswith("abcdefgh.jpg")
    assert parsed[0].bucket == "tiploop-research-images"

    with pytest.raises(ResearchError):
        research_service.parse_attachments(payload, "other-user")


@pytest.mark.no_db
@pytest.mark.parametrize("mutation", [
    {"bucket": "tiploop-research-videos"},
    {"mime_type": "image/svg+xml"},
    {"path": "auth-user/../12345678/abcdefgh.jpg"},
    {"size_bytes": 11 * 1024 * 1024},
])
def test_attachment_metadata_rejects_tampering(mutation):
    item = {
        "bucket": "tiploop-research-images",
        "path": "auth-user/drafts/12345678/abcdefgh.jpg",
        "kind": "image",
        "mime_type": "image/jpeg",
        "file_name": "화면.jpg",
        "size_bytes": 1024,
    }
    item.update(mutation)
    with pytest.raises(ResearchError):
        research_service.parse_attachments(json.dumps([item]), "auth-user")


def test_notes_are_scoped_to_owner_and_editable(make_member):
    owner = make_member(name="연구자")
    other = make_member(name="다른 사람")
    note_id = research_service.create_note(
        owner.id,
        "Notion",
        "분석한 이유\n협업 문서 흐름을 보기 위해",
        "https://notion.so",
    )
    research_service.create_note(other.id, "Linear", "분석한 이유\n이슈 흐름")

    assert [note.title for note in research_service.list_notes(owner.id)] == ["Notion"]
    assert research_service.get_note(note_id, owner.id).link_url == "https://notion.so"
    with pytest.raises(ResearchError):
        research_service.get_note(note_id, other.id)

    research_service.update_note(
        note_id,
        owner.id,
        "Notion 업데이트",
        "분석한 이유\n편집 흐름 확인",
        "https://www.notion.so",
    )
    updated = research_service.get_note(note_id, owner.id)
    assert updated.title == "Notion 업데이트"
    assert updated.body.endswith("편집 흐름 확인")


def test_other_user_cannot_update_note(make_member):
    owner = make_member()
    other = make_member()
    note_id = research_service.create_note(owner.id, "서비스", "분석한 이유\n관찰")

    with pytest.raises(ResearchError):
        research_service.update_note(note_id, other.id, "변조", "분석한 이유\n변조")
    assert research_service.get_note(note_id, owner.id).title == "서비스"


def test_non_reference_post_cannot_be_updated_as_research(make_member):
    from app.repo import posts

    owner = make_member()
    legacy_id = posts.create_post(owner.id, "tip", "레거시 팁", "상황\n원문")
    with pytest.raises(ResearchError):
        research_service.update_note(
            legacy_id, owner.id, "변조", "분석한 이유\n연구 노트로 변조"
        )
    assert posts.get_post(legacy_id).title == "레거시 팁"


def test_reference_attachments_survive_text_edit(make_member):
    from app.repo import posts

    owner = make_member()
    note_id = posts.create_post(
        owner.id,
        "reference",
        "이전 연구",
        "분석한 이유\n원문",
        image_url="https://cdn.example.com/old.png",
        video_url="https://cdn.example.com/old.mp4",
    )
    research_service.update_note(note_id, owner.id, "수정", "분석한 이유\n수정 본문")
    updated = research_service.get_note(note_id, owner.id)
    assert updated.image_url == "https://cdn.example.com/old.png"
    assert updated.video_url == "https://cdn.example.com/old.mp4"
