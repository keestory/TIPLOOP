"""Supabase Storage 객체의 서버측 소유권·메타데이터 검증."""

from __future__ import annotations

from app.repo.database import get_connection
from app.types.models import MediaAttachment


def attachments_match_storage(
    attachments: tuple[MediaAttachment, ...], auth_id: str
) -> bool:
    """제출된 첨부가 실제 Storage 객체와 정확히 일치하는지 확인한다."""
    if not attachments:
        return True
    buckets = sorted({attachment.bucket for attachment in attachments})
    paths = sorted({attachment.path for attachment in attachments})
    sql = """
        SELECT bucket_id, name, owner_id,
               metadata ->> 'mimetype' AS mime_type,
               metadata ->> 'size' AS size_bytes
          FROM storage.objects
         WHERE bucket_id = ANY(%s) AND name = ANY(%s)
    """
    with get_connection() as conn:
        rows = conn.execute(sql, (buckets, paths)).fetchall()
    found = {(row["bucket_id"], row["name"]): row for row in rows}
    for attachment in attachments:
        row = found.get((attachment.bucket, attachment.path))
        if row is None or row["owner_id"] != auth_id:
            return False
        if row["mime_type"] != attachment.mime_type:
            return False
        try:
            if int(row["size_bytes"]) != attachment.size_bytes:
                return False
        except (TypeError, ValueError):
            return False
    return True
