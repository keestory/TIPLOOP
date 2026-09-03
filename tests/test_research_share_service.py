"""비공개 연구 노트의 스냅샷 링크 공유 계약."""

from __future__ import annotations

import re

import pytest

from app.service import research_share_service
from app.service.research_share_service import ResearchShareError
from app.types.models import MediaAttachment, Post


def _post() -> Post:
    return Post(
        id=12,
        author_id=7,
        category="reference",
        title="Notion",
        body="기획과 UX\n빈 화면에서 다음 행동을 보여준다",
        created_at="2026-09-03 10:00",
        link_url="https://notion.so",
        analysis_mode="focus",
        selected_question_ids=("ref.planning_ux", "ref.next_action"),
        attachments=(
            MediaAttachment(
                bucket="tiploop-research-images",
                path="auth-7/drafts/draft-1/object-1.jpg",
                kind="image",
                mime_type="image/jpeg",
                file_name="내부 화면 이름.jpg",
                size_bytes=1024,
            ),
            MediaAttachment(
                bucket="tiploop-research-videos",
                path="auth-7/drafts/draft-1/object-2.mp4",
                kind="video",
                mime_type="video/mp4",
                file_name="원본 영상 이름.mp4",
                size_bytes=4096,
            ),
        ),
    )


@pytest.mark.no_db
def test_share_creation_stores_snapshot_and_hashes_only(monkeypatch):
    captured = {}
    monkeypatch.setattr(research_share_service.posts, "get_owned_post", lambda *_: _post())
    monkeypatch.setattr(research_share_service.secrets, "token_urlsafe", lambda _n: "A" * 43)

    def replace(*args):
        captured["args"] = args
        return True

    monkeypatch.setattr(research_share_service.post_shares, "replace_active", replace)
    token = research_share_service.create_link(12, 7, "auth-7", True)

    assert token == "A" * 43
    _, _, token_hash, include_media, snapshot, media_hashes = captured["args"]
    assert token not in repr(captured)
    assert re.fullmatch(r"[0-9a-f]{64}", token_hash)
    assert include_media is True
    assert snapshot["post"]["title"] == "Notion"
    assert snapshot["owner_auth_id"] == "auth-7"
    assert len(snapshot["attachments"]) == 2
    assert len(set(media_hashes)) == 2
    assert all(re.fullmatch(r"[0-9a-f]{64}", value) for value in media_hashes)


@pytest.mark.no_db
def test_public_share_is_frozen_snapshot_with_scoped_media_tokens(monkeypatch):
    original = _post()
    snapshot = research_share_service._snapshot(original, "auth-7", True)
    monkeypatch.setattr(
        research_share_service.post_shares,
        "active_for_hash",
        lambda _hash: {"id": 4, "post_id": 12, "include_media": True, "snapshot": snapshot},
    )

    shared, grants = research_share_service.shared_note("B" * 43)

    assert shared.title == "Notion"
    assert [item.kind for item in shared.attachments] == ["image", "video"]
    assert len(grants) == 2
    assert grants[0] != grants[1]
    assert all(re.fullmatch(r"[A-Za-z0-9_-]{43}", value) for value in grants)


@pytest.mark.no_db
def test_created_token_round_trips_to_public_lookup(monkeypatch):
    stored = {}
    monkeypatch.setattr(
        research_share_service.posts, "get_owned_post", lambda *_: _post()
    )
    monkeypatch.setattr(
        research_share_service.secrets, "token_urlsafe", lambda _n: "R" * 43
    )

    def replace(
        post_id, _author_id, token_hash, include_media, snapshot, _media_hashes
    ):
        stored[token_hash] = {
            "id": 9,
            "post_id": post_id,
            "include_media": include_media,
            "snapshot": snapshot,
        }
        return True

    monkeypatch.setattr(research_share_service.post_shares, "replace_active", replace)
    monkeypatch.setattr(
        research_share_service.post_shares,
        "active_for_hash",
        lambda token_hash: stored.get(token_hash),
    )

    token = research_share_service.create_link(12, 7, "auth-7", True)
    shared, grants = research_share_service.shared_note(token)

    assert shared.title == "Notion"
    assert len(grants) == 2
    assert grants == tuple(
        research_share_service._media_token("R" * 43, index)
        for index in range(2)
    )


@pytest.mark.no_db
def test_share_rejects_bad_or_unknown_token(monkeypatch):
    with pytest.raises(ResearchShareError):
        research_share_service.shared_note("too-short")

    monkeypatch.setattr(
        research_share_service.post_shares, "active_for_hash", lambda _hash: None
    )
    with pytest.raises(ResearchShareError):
        research_share_service.shared_note("C" * 43)


@pytest.mark.no_db
def test_non_owner_cannot_create_share(monkeypatch):
    monkeypatch.setattr(research_share_service.posts, "get_owned_post", lambda *_: None)
    monkeypatch.setattr(
        research_share_service.post_shares,
        "replace_active",
        lambda *_: pytest.fail("소유권 확인 전에 공유 행을 만들면 안 됩니다."),
    )
    with pytest.raises(ResearchShareError):
        research_share_service.create_link(12, 99, "auth-99", True)
