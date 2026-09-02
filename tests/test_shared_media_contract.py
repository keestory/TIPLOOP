"""공개 미디어 Edge Function의 비공개·회수 가능 스트리밍 경계."""

from pathlib import Path

import pytest


@pytest.mark.no_db
def test_shared_media_uses_scoped_grant_and_snapshot_streaming():
    root = Path(__file__).resolve().parents[1]
    source = (root / "supabase/functions/shared-media/index.ts").read_text(
        encoding="utf-8"
    )

    assert "post_share_media_grants" in source
    assert "url.searchParams.get('grant')" in source
    assert "url.searchParams.get('token')" not in source
    assert "snapshot?.attachments" in source
    assert "parts[0] === ownerAuthId" in source
    assert "Number.isFinite(expiresMs)" in source
    assert "origin.body" in source
    assert "createSignedUrl" not in source
    assert "private, no-store" in source
    assert "range.includes(',')" in source
