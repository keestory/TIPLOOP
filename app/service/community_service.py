"""커뮤니티 도메인 로직 — 글·레퍼런스·댓글·프로필.

카테고리(팁/레퍼런스/질문/회고)로 종류를 나눈다. 레퍼런스는 참고 링크를 붙일 수 있다.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from app.config.settings import CATEGORIES, TOPICS
from app.repo import (
    comments,
    follows,
    media_comments,
    members,
    notifications,
    posts,
    reactions,
    reviews,
)
from app.types.models import MediaComment, Post, Review, Thread, User


class CommunityError(ValueError):
    """커뮤니티 동작 실패. 메시지는 사용자에게 보여줄 수 있다."""


def create_post(
    author_id: int, category: str, title: str, body: str,
    link_url: str = "", image_url: str = "", video_url: str = "",
) -> int:
    """글을 작성한다. 레퍼런스면 참고 링크를, 어느 글이든 주석 이미지·영상을 붙일 수 있다."""
    title = (title or "").strip()
    body = (body or "").strip()
    link_url = (link_url or "").strip()
    image_url = (image_url or "").strip()
    video_url = (video_url or "").strip()

    if category not in CATEGORIES:
        raise CommunityError("카테고리를 선택해 주세요.")
    if not title:
        raise CommunityError("제목을 입력해 주세요.")
    if not body:
        raise CommunityError("내용을 입력해 주세요.")

    # 링크는 레퍼런스에서만 유지
    if category != "reference":
        link_url = ""

    post_id = posts.create_post(
        author_id=author_id, category=category, title=title, body=body,
        link_url=link_url or None, image_url=image_url or None, video_url=video_url or None,
    )
    _notify_topic_subscribers(post_id, author_id, title + " " + body)
    return post_id


def _notify_topic_subscribers(post_id: int, author_id: int, text: str) -> None:
    """글이 언급한 관심 주제를 구독한 회원들에게 새 글 알림(중복 제거)."""
    seen: set[int] = set()
    for topic in TOPICS:
        if topic not in text:
            continue
        for uid in members.subscribers_of_topic(topic):
            if uid in seen:
                continue
            seen.add(uid)
            notifications.create(
                uid, "topic_post", actor_id=author_id, post_id=post_id, topic=topic
            )


def add_media_comment(
    post_id: int, author_id: int, t_seconds: float, x: float, y: float, body: str
) -> MediaComment:
    """영상의 특정 시각·위치에 코멘트를 단다. 대상 글에 영상이 있어야 한다."""
    body = (body or "").strip()
    if not body:
        raise CommunityError("코멘트 내용을 입력해 주세요.")
    post = posts.get_post(post_id)
    if post is None or not post.video_url:
        raise CommunityError("영상을 찾을 수 없습니다.")
    x = min(1.0, max(0.0, x))
    y = min(1.0, max(0.0, y))
    t_seconds = max(0.0, t_seconds)
    return media_comments.create(post_id, author_id, t_seconds, x, y, body)


def list_media_comments(post_id: int) -> list[MediaComment]:
    return media_comments.list_for_post(post_id)


def list_feed(
    category: str = "", job_role: str = "", industry: str = "",
    search: str = "", sort: str = "new",
) -> list[Post]:
    """피드. 빈 문자열 필터는 무시한다. sort: new|top|buzz."""
    return posts.list_posts(
        category=category or None,
        job_role=job_role or None,
        industry=industry or None,
        search=search or None,
        sort=sort,
    )


def home_feed(
    posts: list[Post], waiting_limit: int = 3
) -> tuple[Post | None, list[Post], list[Post]]:
    """홈 화면용 묶음: (오늘의 글, 답변 기다리는 질문들, 나머지 피드).

    맨 앞 글을 히어로로, 답변 0인 질문을 별도 섹션으로 끌어올린다(최대 waiting_limit).
    나머지는 순서대로 피드에 남긴다. 순수 함수 — DB를 건드리지 않는다.
    """
    if not posts:
        return None, [], []
    featured, tail = posts[0], posts[1:]
    waiting: list[Post] = []
    rest: list[Post] = []
    for p in tail:
        if p.category == "question" and p.comment_count == 0 and len(waiting) < waiting_limit:
            waiting.append(p)
        else:
            rest.append(p)
    return featured, waiting, rest


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
    post = posts.get_post(post_id)
    if post is None:
        raise CommunityError("글을 찾을 수 없습니다.")
    parent_author: int | None = None
    if parent_id is not None:
        parent = comments.get_comment(parent_id)
        if parent is None or parent.post_id != post_id:
            parent_id = None
        else:
            parent_author = parent.author_id
            if parent.parent_id is not None:
                parent_id = parent.parent_id  # 답글의 답글은 최상위로 평탄화
    cid = comments.create_comment(post_id, author_id, body, parent_id)
    # 글쓴이에겐 '댓글', 원댓글 작성자에겐 '답글' 알림 (겹치면 댓글만)
    notifications.create(post.author_id, "comment", actor_id=author_id, post_id=post_id)
    if parent_author is not None and parent_author != post.author_id:
        notifications.create(parent_author, "reply", actor_id=author_id, post_id=post_id)
    return cid


def add_review(post_id: int, author_id: int, body: str) -> int:
    """적용 후기를 남긴다. 대상 글이 있어야 한다. 글쓴이에게 알림."""
    body = (body or "").strip()
    if not body:
        raise CommunityError("후기 내용을 입력해 주세요.")
    post = posts.get_post(post_id)
    if post is None:
        raise CommunityError("글을 찾을 수 없습니다.")
    rid = reviews.create(post_id, author_id, body)
    notifications.create(post.author_id, "review", actor_id=author_id, post_id=post_id)
    return rid


def list_reviews(post_id: int) -> list[Review]:
    return reviews.list_for_post(post_id)


def onboarding_checklist(user: User | None) -> dict | None:
    """홈 상단 시작 체크리스트 (8c). 대상이 아니거나 닫았거나 전부 완료면 None.

    항목: 프로필 완성(온보딩에서 이미 완료 — 첫 성취감) → 관심 주제 → 첫 글·반응.
    """
    if user is None or not user.is_onboarded or user.checklist_dismissed:
        return None
    wrote = bool(posts.list_posts(author_id=user.id))
    reacted = bool(reactions.reacted_post_ids(user.id)) or bool(reactions.helpful_post_ids(user.id))
    items = [
        {"label": "프로필 완성", "done": True, "href": None},
        {"label": "관심 주제 고르기", "done": bool(user.topics), "href": "/topics"},
        {"label": "첫 글·반응 남기기", "done": wrote or reacted, "href": "/posts/new"},
    ]
    if all(i["done"] for i in items):
        return None
    return {"items": items, "done": sum(1 for i in items if i["done"]), "total": len(items)}


def week_start(today: date | None = None) -> date:
    """이번 주 월요일 날짜. 다이제스트의 '이번 주' 기준."""
    today = today or date.today()
    return today - timedelta(days=today.weekday())


def weekly_digest(user: User) -> dict:
    """'이번 주 티핑' 요약 (6a) — 가장 도움된 팁 · 팔로우 새 글 · 답변 대기 · 내 글 받은 후기.

    사이트 전체를 훑는 무거운 집계 대신, 최근 글 목록 하나를 여러 조건으로
    나눠 쓰는 방식 — 지금 규모(수십~수백 글/주)에서는 충분히 가볍다.
    """
    start = week_start()
    recent = posts.list_posts(sort="new")
    this_week = [p for p in recent if (_post_date(p.created_at) or date.min) >= start]

    top_post = max(this_week, key=lambda p: p.helpful_count, default=None)
    if top_post is not None and top_post.helpful_count == 0:
        top_post = None

    following = set(follows.followee_ids(user.id))
    followed_posts = [
        p for p in this_week if p.author_id in following and p.author_id != user.id
    ][:5]

    waiting = [
        p for p in recent
        if p.category == "question" and p.comment_count == 0 and p.author_id != user.id
    ][:3]

    my_reviews = reviews.received_since(user.id, start)

    return {
        "week_start": start,
        "top_post": top_post,
        "followed_posts": followed_posts,
        "waiting": waiting,
        "my_reviews": my_reviews,
        "has_any": bool(top_post or followed_posts or waiting or my_reviews),
    }


def _post_date(created_at: str) -> date | None:
    """created_at 문자열(맨 앞 10자 YYYY-MM-DD)만 안전하게 파싱. 3.9 호환."""
    try:
        return datetime.strptime(created_at[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def contribution_heatmap(
    own_posts: list[Post], weeks: int = 12, today: date | None = None
) -> list[int]:
    """최근 N주 기여 강도(주별). 0=없음, 1=1~2건, 2=3건 이상. 오래된→최근 순.

    실제 작성글 날짜로 계산하는 순수 함수 — DB를 건드리지 않는다.
    """
    today = today or date.today()
    counts = [0] * weeks
    for p in own_posts:
        d = _post_date(p.created_at)
        if d is None:
            continue
        w = (today - d).days // 7
        if 0 <= w < weeks:
            counts[weeks - 1 - w] += 1  # 최근 주가 오른쪽 끝
    return [2 if c >= 3 else 1 if c >= 1 else 0 for c in counts]


def get_profile(user_id: int) -> tuple[User, list[Post], dict]:
    """회원 프로필, 쓴 글, 임팩트 지표. 없으면 CommunityError.

    지표: 도움을 준 사람 수(helpful) · 받은 후기 · 받은 공감 · 글 수.
    """
    user = members.get(user_id)
    if user is None:
        raise CommunityError("사용자를 찾을 수 없습니다.")
    own_posts = posts.list_posts(author_id=user_id)
    stats = {
        "helpful": reactions.received_helpful_count(user_id),
        "reviews": reviews.received_count(user_id),
        "reactions": reactions.received_reaction_count(user_id),
        "posts": len(own_posts),
    }
    return user, own_posts, stats
