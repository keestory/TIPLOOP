"""팔로우 도메인 로직 — 팔로우/언팔로우 + 팔로우 알림."""

from __future__ import annotations

from app.repo import follows, notifications


def toggle(follower_id: int, followee_id: int) -> bool:
    """팔로우 상태를 뒤집는다. 결과(팔로우 중이면 True)를 돌려준다.

    자기 자신은 팔로우할 수 없다. 새로 팔로우하면 상대에게 알림을 남긴다.
    """
    if follower_id == followee_id:
        return False
    if follows.is_following(follower_id, followee_id):
        follows.unfollow(follower_id, followee_id)
        return False
    if follows.follow(follower_id, followee_id):
        notifications.create(followee_id, "follow", actor_id=follower_id)
    return True


def status(viewer_id: int | None, member_id: int) -> dict:
    """프로필 표시용 — 팔로워/팔로잉 수와 내가 팔로우 중인지."""
    return {
        "followers": follows.followers_count(member_id),
        "following": follows.following_count(member_id),
        "is_following": (
            viewer_id is not None
            and viewer_id != member_id
            and follows.is_following(viewer_id, member_id)
        ),
    }
