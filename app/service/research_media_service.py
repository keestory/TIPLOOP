"""개인 연구 노트 첨부의 검증과 Storage 소유권 확인."""

from __future__ import annotations

import json
import re
from dataclasses import asdict

from app.config.settings import (
    REFERENCE_IMAGE_MAX_BYTES,
    REFERENCE_MEDIA_BUCKETS,
    REFERENCE_MEDIA_MAX_FILES,
    REFERENCE_MEDIA_MAX_TOTAL_BYTES,
    REFERENCE_MEDIA_MAX_VIDEOS,
    REFERENCE_MEDIA_TYPES,
    REFERENCE_VIDEO_MAX_BYTES,
)
from app.repo import storage_objects
from app.types.models import MediaAttachment


class ResearchMediaError(ValueError):
    """사용자에게 보여줄 수 있는 첨부 검증 실패."""


_SAFE_PATH_PART = re.compile(r"^[A-Za-z0-9_-]{8,80}$")
_SAFE_FILE_NAME = re.compile(r"^[^\x00-\x1f\x7f]{1,120}$")


def parse_attachments(payload: str, user_auth_id: str) -> tuple[MediaAttachment, ...]:
    """브라우저가 보낸 Storage 메타데이터를 최소 권한 경계에서 검증한다."""
    if not payload:
        return ()
    if len(payload) > 24_000:
        raise ResearchMediaError("첨부 정보가 너무 큽니다. 파일 수를 줄여 주세요.")
    try:
        raw_items = json.loads(payload)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ResearchMediaError(
            "첨부 정보를 읽을 수 없습니다. 파일을 다시 선택해 주세요."
        ) from exc
    if not isinstance(raw_items, list):
        raise ResearchMediaError("첨부 정보 형식이 올바르지 않습니다.")
    if len(raw_items) > REFERENCE_MEDIA_MAX_FILES:
        raise ResearchMediaError(
            f"이미지와 영상은 합쳐서 {REFERENCE_MEDIA_MAX_FILES}개까지 첨부할 수 있어요."
        )

    attachments: list[MediaAttachment] = []
    paths: set[str] = set()
    total_bytes = 0
    video_count = 0
    expected_keys = {
        "bucket", "path", "kind", "mime_type", "file_name", "size_bytes"
    }
    for raw in raw_items:
        if not isinstance(raw, dict) or set(raw) != expected_keys:
            raise ResearchMediaError("첨부 정보 형식이 올바르지 않습니다.")
        bucket = str(raw["bucket"])
        path = str(raw["path"])
        parts = path.split("/")
        if (
            not user_auth_id
            or len(parts) != 4
            or parts[0] != user_auth_id
            or parts[1] != "drafts"
            or not _SAFE_PATH_PART.fullmatch(parts[2])
            or not re.fullmatch(r"[A-Za-z0-9_-]{8,80}\.[a-z0-9]{2,5}", parts[3])
        ):
            raise ResearchMediaError("현재 로그인 계정의 첨부만 저장할 수 있어요.")
        if path in paths:
            raise ResearchMediaError("같은 첨부가 두 번 포함되어 있어요.")
        paths.add(path)

        mime_type = str(raw["mime_type"])
        expected = REFERENCE_MEDIA_TYPES.get(mime_type)
        kind = str(raw["kind"])
        if (
            expected is None
            or kind != expected[0]
            or bucket != REFERENCE_MEDIA_BUCKETS.get(kind)
            or not path.endswith("." + expected[1])
        ):
            raise ResearchMediaError("지원하지 않는 이미지 또는 영상 형식이에요.")
        try:
            size_bytes = int(raw["size_bytes"])
        except (TypeError, ValueError) as exc:
            raise ResearchMediaError("첨부 파일 크기 정보가 올바르지 않습니다.") from exc
        limit = REFERENCE_IMAGE_MAX_BYTES if kind == "image" else REFERENCE_VIDEO_MAX_BYTES
        if size_bytes <= 0 or size_bytes > limit:
            unit = limit // (1024 * 1024)
            kind_label = "이미지" if kind == "image" else "영상"
            raise ResearchMediaError(f"{kind_label}는 파일당 {unit}MB까지 가능해요.")
        total_bytes += size_bytes
        if total_bytes > REFERENCE_MEDIA_MAX_TOTAL_BYTES:
            raise ResearchMediaError("첨부 파일 전체 크기는 100MB까지 가능해요.")
        if kind == "video":
            video_count += 1
            if video_count > REFERENCE_MEDIA_MAX_VIDEOS:
                raise ResearchMediaError("영상은 노트당 1개까지 첨부할 수 있어요.")
        file_name = str(raw["file_name"]).strip()
        if not _SAFE_FILE_NAME.fullmatch(file_name):
            raise ResearchMediaError("첨부 파일 이름을 확인해 주세요.")
        attachments.append(
            MediaAttachment(bucket, path, kind, mime_type, file_name, size_bytes)
        )
    return tuple(attachments)


def attachment_dicts(items: tuple[MediaAttachment, ...]) -> list[dict]:
    """Jinja/JSON 경계에서 쓸 수 있는 단순 사전으로 바꾼다."""
    return [asdict(item) for item in items]


def verify_attachments(
    attachments: tuple[MediaAttachment, ...], user_auth_id: str
) -> None:
    """DB에 쓸 첨부가 실제 Storage의 현재 사용자 객체인지 확인한다."""
    if attachments and not storage_objects.attachments_match_storage(
        attachments, user_auth_id
    ):
        raise ResearchMediaError("첨부 파일을 확인할 수 없습니다. 다시 업로드해 주세요.")
