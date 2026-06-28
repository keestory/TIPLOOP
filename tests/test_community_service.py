"""커뮤니티 서비스 단위 테스트."""

import pytest

from app.service import community_service
from app.service.community_service import CommunityError


def test_create_and_get_post(make_teacher):
    t = make_teacher(name="이선생")
    pid = community_service.create_post(t.id, "info", "진로 변화 공유", "이렇게 전달했어요")
    post, threads = community_service.get_post_with_threads(pid)
    assert post.title == "진로 변화 공유"
    assert post.author_name == "이선생"
    assert threads == []


def test_seminar_requires_event_detail(make_teacher):
    t = make_teacher()
    with pytest.raises(CommunityError):
        community_service.create_post(t.id, "seminar", "워크숍", "내용")
    pid = community_service.create_post(
        t.id, "seminar", "워크숍", "내용", event_at="7/12 14:00", online_url="https://x.kr"
    )
    post, _ = community_service.get_post_with_threads(pid)
    assert post.event_at == "7/12 14:00"


def test_non_seminar_clears_event_fields(make_teacher):
    t = make_teacher()
    pid = community_service.create_post(
        t.id, "info", "제목", "내용", event_at="버려져야 함", location="여기"
    )
    post, _ = community_service.get_post_with_threads(pid)
    assert post.event_at is None and post.location is None


def test_post_validation(make_teacher):
    t = make_teacher()
    with pytest.raises(CommunityError):
        community_service.create_post(t.id, "info", "", "내용")
    with pytest.raises(CommunityError):
        community_service.create_post(t.id, "bogus", "제목", "내용")


def test_feed_filters_by_category_and_region(make_teacher):
    seoul = make_teacher(level="중학교", region="서울")
    busan = make_teacher(level="고등학교", region="부산")
    community_service.create_post(seoul.id, "info", "서울 정보", "내용")
    community_service.create_post(busan.id, "seminar", "부산 세미나", "내용", location="부산")

    assert len(community_service.list_feed()) == 2
    assert len(community_service.list_feed(category="seminar")) == 1
    assert community_service.list_feed(region="서울")[0].title == "서울 정보"


def test_replies_are_threaded_one_level(make_teacher):
    t = make_teacher()
    other = make_teacher()
    pid = community_service.create_post(t.id, "support", "고민", "내용")
    top = community_service.add_comment(pid, t.id, "최상위 댓글")
    community_service.add_comment(pid, other.id, "답글1", parent_id=top)
    reply2 = community_service.add_comment(pid, t.id, "답글2", parent_id=top)
    community_service.add_comment(pid, other.id, "답답글", parent_id=reply2)  # 최상위로 평탄화

    _, threads = community_service.get_post_with_threads(pid)
    assert len(threads) == 1
    assert threads[0].comment.body == "최상위 댓글"
    assert len(threads[0].replies) == 3


def test_comments_flow(make_teacher):
    t = make_teacher()
    pid = community_service.create_post(t.id, "support", "고민이 있어요", "내용")
    community_service.add_comment(pid, t.id, "응원합니다")
    _, threads = community_service.get_post_with_threads(pid)
    assert len(threads) == 1 and threads[0].comment.body == "응원합니다"
    with pytest.raises(CommunityError):
        community_service.add_comment(pid, t.id, "   ")


def test_profile_lists_own_posts_and_received_reactions(make_teacher):
    t = make_teacher(name="이선생")
    community_service.create_post(t.id, "info", "글1", "내용")
    community_service.create_post(t.id, "info", "글2", "내용")
    teacher, posts, received = community_service.get_profile(t.id)
    assert teacher.name == "이선생"
    assert len(posts) == 2
    assert received == 0


def test_missing_post_raises(make_teacher):
    with pytest.raises(CommunityError):
        community_service.get_post_with_threads(9999)
