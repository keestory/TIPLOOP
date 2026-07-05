"""공감 도메인 로직 — 글/댓글 반응 토글과 조회."""

from __future__ import annotations


from app.repo import comments, notifications, posts, reactions


def toggle_post(post_id: int, user_id: int) -> bool:
    """글 공감 토글. 대상 글이 있을 때만. 반환: 토글 후 켜짐 여부."""
    if posts.get_post(post_id) is None:
        return False
    return reactions.toggle_post_reaction(post_id, user_id)


def toggle_comment(comment_id: int, user_id: int) -> int | None:
    """댓글 공감 토글. 반환: 돌아갈 글 id(없으면 None)."""
    comment = comments.get_comment(comment_id)
    if comment is None:
        return None
    reactions.toggle_comment_reaction(comment_id, user_id)
    return comment.post_id


def viewer_post_reactions(user_id: int | None) -> set[int]:
    return reactions.reacted_post_ids(user_id) if user_id else set()


def viewer_comment_reactions(user_id: int | None, post_id: int) -> set[int]:
    return reactions.reacted_comment_ids(user_id, post_id) if user_id else set()


def received_count(user_id: int) -> int:
    return reactions.received_reaction_count(user_id)


def toggle_helpful(post_id: int, user_id: int) -> bool:
    """'도움됐어요' 토글. 대상 글이 있을 때만. 새로 켜면 글쓴이에게 알림."""
    post = posts.get_post(post_id)
    if post is None:
        return False
    now_on = reactions.toggle_post_helpful(post_id, user_id)
    if now_on:
        notifications.create(post.author_id, "helpful", actor_id=user_id, post_id=post_id)
    return now_on


def viewer_helpful(user_id: int | None) -> set[int]:
    return reactions.helpful_post_ids(user_id) if user_id else set()


def received_helpful(user_id: int) -> int:
    return reactions.received_helpful_count(user_id)
