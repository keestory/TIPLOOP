"""개인 연구 노트를 명시적으로 링크 공개하는 도메인 로직."""

from __future__ import annotations

import base64
import hashlib
import re
import secrets
from dataclasses import asdict

from app.repo import post_shares, posts
from app.types.models import MediaAttachment, Post

_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")


class ResearchShareError(ValueError):
    """공유 링크 생성·조회 실패."""


def hash_token(token: str) -> str:
    clean = (token or "").strip()
    if not _TOKEN_RE.fullmatch(clean):
        raise ResearchShareError("공유가 끝났거나 올바르지 않은 링크예요.")
    return hashlib.sha256(clean.encode("ascii")).hexdigest()


def _media_token(token: str, index: int) -> str:
    digest = hashlib.sha256(
        f"tiploop-media-v1:{token}:{index}".encode("ascii")
    ).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _snapshot(post: Post, owner_auth_id: str, include_media: bool) -> dict:
    return {
        "owner_auth_id": owner_auth_id,
        "post": {
            "title": post.title,
            "body": post.body,
            "created_at": post.created_at,
            "link_url": post.link_url,
            "analysis_mode": post.analysis_mode,
            "analysis_template_version": post.analysis_template_version,
            "selected_question_ids": list(post.selected_question_ids or ()),
        },
        "attachments": (
            [asdict(attachment) for attachment in post.attachments]
            if include_media else []
        ),
    }


def create_link(
    post_id: int,
    author_id: int,
    owner_auth_id: str,
    include_media: bool = True,
) -> str:
    post = posts.get_owned_post(post_id, author_id)
    if post is None or post.category != "reference":
        raise ResearchShareError("서비스 노트를 찾을 수 없습니다.")
    token = secrets.token_urlsafe(32)
    snapshot = _snapshot(post, owner_auth_id, include_media)
    media_hashes = tuple(
        hash_token(_media_token(token, index))
        for index in range(len(snapshot["attachments"]))
    )
    if not post_shares.replace_active(
        post_id,
        author_id,
        hash_token(token),
        bool(include_media),
        snapshot,
        media_hashes,
    ):
        raise ResearchShareError("서비스 노트를 찾을 수 없습니다.")
    return token


def status(post_id: int, author_id: int) -> dict | None:
    return post_shares.active_for_owner(post_id, author_id)


def revoke(post_id: int, author_id: int) -> None:
    if not post_shares.revoke_active(post_id, author_id):
        raise ResearchShareError("활성 공유 링크를 찾을 수 없습니다.")


def shared_note(token: str) -> tuple[Post, tuple[str, ...]]:
    share = post_shares.active_for_hash(hash_token(token))
    if share is None:
        raise ResearchShareError("공유가 끝났거나 올바르지 않은 링크예요.")
    snapshot = share.get("snapshot")
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("post"), dict):
        raise ResearchShareError("공유가 끝났거나 올바르지 않은 링크예요.")
    fields = snapshot["post"]
    attachment_rows = snapshot.get("attachments", [])
    if not isinstance(attachment_rows, list) or len(attachment_rows) > 6:
        raise ResearchShareError("공유가 끝났거나 올바르지 않은 링크예요.")
    try:
        attachments = tuple(MediaAttachment(**item) for item in attachment_rows)
        post = Post(
            id=int(share["post_id"]),
            author_id=0,
            category="reference",
            title=str(fields["title"]),
            body=str(fields["body"]),
            created_at=str(fields["created_at"]),
            link_url=str(fields["link_url"]) if fields.get("link_url") else None,
            analysis_mode=fields.get("analysis_mode"),
            analysis_template_version=fields.get("analysis_template_version"),
            selected_question_ids=tuple(fields.get("selected_question_ids") or ()),
            attachments=attachments,
        )
    except (KeyError, TypeError, ValueError):
        raise ResearchShareError("공유가 끝났거나 올바르지 않은 링크예요.") from None
    media_tokens = tuple(_media_token(token, index) for index in range(len(attachments)))
    return post, media_tokens
