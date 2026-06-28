"""커뮤니티 도메인 로직 — 글·세미나·댓글·프로필.

세 기능(정보공유/세미나/고민나눔)을 글 카테고리로 통합한다.
"""

from app.config.settings import CATEGORIES
from app.repo import comments, posts, users
from app.types.models import Comment, Post, User


class CommunityError(ValueError):
    """커뮤니티 동작 실패. 메시지는 사용자에게 보여줄 수 있다."""


def create_post(
    author_id: int,
    category: str,
    title: str,
    body: str,
    event_at: str = "",
    location: str = "",
    online_url: str = "",
) -> int:
    """글을 작성한다. 세미나면 일시/장소/링크 중 하나는 있어야 한다."""
    title = (title or "").strip()
    body = (body or "").strip()

    if category not in CATEGORIES:
        raise CommunityError("카테고리를 선택해 주세요.")
    if not title:
        raise CommunityError("제목을 입력해 주세요.")
    if not body:
        raise CommunityError("내용을 입력해 주세요.")

    event_at = (event_at or "").strip()
    location = (location or "").strip()
    online_url = (online_url or "").strip()

    if category == "seminar" and not (event_at or location or online_url):
        raise CommunityError("세미나는 일시·장소·온라인 링크 중 하나 이상을 입력해 주세요.")

    # 세미나가 아니면 세미나 전용 필드는 비운다
    if category != "seminar":
        event_at = location = online_url = ""

    return posts.create_post(
        author_id=author_id,
        category=category,
        title=title,
        body=body,
        event_at=event_at or None,
        location=location or None,
        online_url=online_url or None,
    )


def list_feed(
    category: str = "", school_level: str = "", region: str = ""
) -> list[Post]:
    """피드. 빈 문자열 필터는 무시한다."""
    return posts.list_posts(
        category=category or None,
        school_level=school_level or None,
        region=region or None,
    )


def get_post_with_comments(post_id: int) -> tuple[Post, list[Comment]]:
    """글과 댓글을 함께 가져온다. 없으면 CommunityError."""
    post = posts.get_post(post_id)
    if post is None:
        raise CommunityError("글을 찾을 수 없습니다.")
    return post, comments.list_comments(post_id)


def add_comment(post_id: int, author_id: int, body: str) -> int:
    """댓글을 단다. 대상 글이 있어야 한다."""
    body = (body or "").strip()
    if not body:
        raise CommunityError("댓글 내용을 입력해 주세요.")
    if posts.get_post(post_id) is None:
        raise CommunityError("글을 찾을 수 없습니다.")
    return comments.create_comment(post_id, author_id, body)


def get_profile(user_id: int) -> tuple[User, list[Post]]:
    """교사 프로필과 그가 쓴 글. 없으면 CommunityError."""
    user = users.get_user(user_id)
    if user is None:
        raise CommunityError("사용자를 찾을 수 없습니다.")
    return user, posts.list_posts(author_id=user_id)
