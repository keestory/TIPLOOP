"""커뮤니티 도메인 로직 — 글·레퍼런스·댓글·프로필.

카테고리(팁/레퍼런스/질문/회고)로 종류를 나눈다. 레퍼런스는 참고 링크를 붙일 수 있다.
"""

from __future__ import annotations

from app.config.settings import CATEGORIES
from app.repo import comments, members, posts, reactions
from app.types.models import Post, Thread, User


class CommunityError(ValueError):
    """커뮤니티 동작 실패. 메시지는 사용자에게 보여줄 수 있다."""


def create_post(
    author_id: int, category: str, title: str, body: str,
    link_url: str = "", image_url: str = "",
) -> int:
    """글을 작성한다. 레퍼런스면 참고 링크를, 어느 글이든 주석 이미지를 붙일 수 있다."""
    title = (title or "").strip()
    body = (body or "").strip()
    link_url = (link_url or "").strip()
    image_url = (image_url or "").strip()

    if category not in CATEGORIES:
        raise CommunityError("카테고리를 선택해 주세요.")
    if not title:
        raise CommunityError("제목을 입력해 주세요.")
    if not body:
        raise CommunityError("내용을 입력해 주세요.")

    # 링크는 레퍼런스에서만 유지
    if category != "reference":
        link_url = ""

    return posts.create_post(
        author_id=author_id, category=category, title=title, body=body,
        link_url=link_url or None, image_url=image_url or None,
    )


def list_feed(
    category: str = "", job_role: str = "", industry: str = "", sort: str = "new"
) -> list[Post]:
    """피드. 빈 문자열 필터는 무시한다. sort: new|top|buzz."""
    return posts.list_posts(
        category=category or None,
        job_role=job_role or None,
        industry=industry or None,
        sort=sort,
    )


def get_post_with_threads(post_id: int) -> tuple[Post, list[Thread]]:
    """글과, 답글까지 묶은 댓글 스레드를 가져온다. 없으면 CommunityError."""
    post = posts.get_post(post_id)
    if post is None:
        raise CommunityError("글을 찾을 수 없습니다.")
    flat = comments.list_comments(post_id)
    replies_by_parent: dict[int, list] = {}
    for c in flat:
        if c.parent_id is not None:
            replies_by_parent.setdefault(c.parent_id, []).append(c)
    threads = [
        Thread(comment=c, replies=tuple(replies_by_parent.get(c.id, ())))
        for c in flat
        if c.parent_id is None
    ]
    return post, threads


def add_comment(post_id: int, author_id: int, body: str, parent_id: int | None = None) -> int:
    """댓글/답글을 단다. 답글은 항상 최상위 댓글에 붙인다(1단계 스레드)."""
    body = (body or "").strip()
    if not body:
        raise CommunityError("댓글 내용을 입력해 주세요.")
    if posts.get_post(post_id) is None:
        raise CommunityError("글을 찾을 수 없습니다.")
    if parent_id is not None:
        parent = comments.get_comment(parent_id)
        if parent is None or parent.post_id != post_id:
            parent_id = None
        elif parent.parent_id is not None:
            parent_id = parent.parent_id  # 답글의 답글은 최상위로 평탄화
    return comments.create_comment(post_id, author_id, body, parent_id)


def get_profile(user_id: int) -> tuple[User, list[Post], int]:
    """회원 프로필, 쓴 글, 받은 공감 합계. 없으면 CommunityError."""
    user = members.get(user_id)
    if user is None:
        raise CommunityError("사용자를 찾을 수 없습니다.")
    return user, posts.list_posts(author_id=user_id), reactions.received_reaction_count(user_id)
