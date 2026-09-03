"""공유 링크 저장소의 DB 드라이버 호환성 회귀 테스트."""

from __future__ import annotations

from contextlib import nullcontext

import pytest

from app.repo import post_shares


class FakeResult:
    def __init__(self, row=None):
        self._row = row

    def fetchone(self):
        return self._row


class FakeCursor:
    def __init__(self):
        self.batch = None

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def executemany(self, query, params):
        self.batch = (query, list(params))


class FakePsycopgConnection:
    """운영 psycopg Connection처럼 batch 실행은 cursor에만 제공한다."""

    def __init__(self):
        self.cursor_instance = FakeCursor()

    def transaction(self):
        return nullcontext()

    def execute(self, query, _params):
        if "SELECT id FROM posts" in query:
            return FakeResult({"id": 12})
        if "INSERT INTO post_shares" in query:
            return FakeResult({"id": 88})
        return FakeResult()

    def cursor(self):
        return self.cursor_instance


@pytest.mark.no_db
def test_replace_active_uses_psycopg_cursor_for_media_grant_batch(monkeypatch):
    conn = FakePsycopgConnection()
    monkeypatch.setattr(post_shares, "get_connection", lambda: nullcontext(conn))

    created = post_shares.replace_active(
        12,
        7,
        "share-hash",
        True,
        {"post": {"title": "Notion"}, "attachments": [{}, {}]},
        ("media-hash-1", "media-hash-2"),
    )

    assert created is True
    query, params = conn.cursor_instance.batch
    assert "INSERT INTO post_share_media_grants" in query
    assert params == [
        (88, 0, "media-hash-1"),
        (88, 1, "media-hash-2"),
    ]
