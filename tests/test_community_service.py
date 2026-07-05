"""커뮤니티 서비스 단위 테스트."""

import pytest

from app.service import community_service
from app.service.community_service import CommunityError


def test_create_and_get_post(make_member):
    t = make_member(name="김준")
    pid = community_service.create_post(t.id, "tip", "A/B 테스트 팁", "퍼널을 다 남기세요")
    post, threads = community_service.get_post_with_threads(pid)
    assert post.title == "A/B 테스트 팁"
    assert post.author_name == "김준"
    assert threads == []


def test_home_feed_partitions_hero_and_waiting(make_member):
    from app.types.models import Post

    def _p(pid, cat, comments=0):
        return Post(id=pid, author_id=1, category=cat, title=f"글{pid}",
                    body="x", created_at="2026-07-05", comment_count=comments)

    posts = [_p(1, "tip"), _p(2, "question", 0), _p(3, "reference"),
             _p(4, "question", 2), _p(5, "question", 0)]
    featured, waiting, rest = community_service.home_feed(posts)
    assert featured.id == 1                       # 맨 앞이 히어로
    assert [q.id for q in waiting] == [2, 5]       # 답변 0인 질문만
    assert [r.id for r in rest] == [3, 4]          # 나머지(답변 있는 질문 포함)


def test_home_feed_empty():
    assert community_service.home_feed([]) == (None, [], [])


def test_reference_keeps_link(make_member):
    t = make_member()
    pid = community_service.create_post(
        t.id, "reference", "토스 뜯어보기", "분석", link_url="https://toss.im"
    )
    post, _ = community_service.get_post_with_threads(pid)
    assert post.link_url == "https://toss.im"


def test_image_url_is_stored(make_member):
    t = make_member()
    pid = community_service.create_post(
        t.id, "tip", "스크린샷 팁", "여기 보세요", image_url="https://cdn.example.com/a.png"
    )
    post, _ = community_service.get_post_with_threads(pid)
    assert post.image_url == "https://cdn.example.com/a.png"


def test_non_reference_drops_link(make_member):
    t = make_member()
    pid = community_service.create_post(
        t.id, "tip", "제목", "내용", link_url="https://버려져야.com"
    )
    post, _ = community_service.get_post_with_threads(pid)
    assert post.link_url is None


def test_post_validation(make_member):
    t = make_member()
    with pytest.raises(CommunityError):
        community_service.create_post(t.id, "tip", "", "내용")
    with pytest.raises(CommunityError):
        community_service.create_post(t.id, "bogus", "제목", "내용")


def test_feed_filters_by_category_and_job_role(make_member):
    pm = make_member(job_role="PM", industry="커머스")
    dev = make_member(job_role="개발", industry="핀테크")
    community_service.create_post(pm.id, "tip", "PM 팁", "내용")
    community_service.create_post(dev.id, "reference", "개발 레퍼런스", "내용", link_url="https://x.dev")

    assert len(community_service.list_feed()) == 2
    assert len(community_service.list_feed(category="reference")) == 1
    assert community_service.list_feed(job_role="PM")[0].title == "PM 팁"
    assert community_service.list_feed(industry="핀테크")[0].title == "개발 레퍼런스"


def test_replies_are_threaded_one_level(make_member):
    t = make_member()
    other = make_member()
    pid = community_service.create_post(t.id, "question", "질문", "내용")
    top = community_service.add_comment(pid, t.id, "최상위 댓글")
    community_service.add_comment(pid, other.id, "답글1", parent_id=top)
    reply2 = community_service.add_comment(pid, t.id, "답글2", parent_id=top)
    community_service.add_comment(pid, other.id, "답답글", parent_id=reply2)  # 최상위로 평탄화

    _, threads = community_service.get_post_with_threads(pid)
    assert len(threads) == 1
    assert threads[0].comment.body == "최상위 댓글"
    assert len(threads[0].replies) == 3


def test_comments_flow(make_member):
    t = make_member()
    pid = community_service.create_post(t.id, "retro", "회고", "내용")
    community_service.add_comment(pid, t.id, "응원합니다")
    _, threads = community_service.get_post_with_threads(pid)
    assert len(threads) == 1 and threads[0].comment.body == "응원합니다"
    with pytest.raises(CommunityError):
        community_service.add_comment(pid, t.id, "   ")


def test_profile_lists_own_posts_and_stats(make_member):
    t = make_member(name="이소라")
    community_service.create_post(t.id, "tip", "글1", "내용")
    community_service.create_post(t.id, "tip", "글2", "내용")
    member, posts, stats = community_service.get_profile(t.id)
    assert member.name == "이소라"
    assert len(posts) == 2
    assert stats == {"helpful": 0, "reviews": 0, "reactions": 0, "posts": 2}


def test_review_add_and_list(make_member):
    author = make_member()
    reader = make_member()
    pid = community_service.create_post(author.id, "tip", "팁", "내용")
    community_service.add_review(pid, reader.id, "적용했더니 이탈 12% 감소")
    revs = community_service.list_reviews(pid)
    assert len(revs) == 1 and revs[0].body == "적용했더니 이탈 12% 감소"
    assert revs[0].author_name is not None
    # 후기가 프로필 지표에 반영
    _, _, stats = community_service.get_profile(author.id)
    assert stats["reviews"] == 1
    with pytest.raises(CommunityError):
        community_service.add_review(pid, reader.id, "   ")


def test_missing_post_raises(make_member):
    with pytest.raises(CommunityError):
        community_service.get_post_with_threads(9999)
