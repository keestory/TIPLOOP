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


def test_reference_keeps_link(make_member):
    t = make_member()
    pid = community_service.create_post(
        t.id, "reference", "토스 뜯어보기", "분석", link_url="https://toss.im"
    )
    post, _ = community_service.get_post_with_threads(pid)
    assert post.link_url == "https://toss.im"


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


def test_profile_lists_own_posts_and_received_reactions(make_member):
    t = make_member(name="이소라")
    community_service.create_post(t.id, "tip", "글1", "내용")
    community_service.create_post(t.id, "tip", "글2", "내용")
    member, posts, received = community_service.get_profile(t.id)
    assert member.name == "이소라"
    assert len(posts) == 2
    assert received == 0


def test_missing_post_raises(make_member):
    with pytest.raises(CommunityError):
        community_service.get_post_with_threads(9999)
