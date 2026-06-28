"""커뮤니티 서비스 단위 테스트."""

import pytest

from app.service import auth_service, community_service
from app.service.community_service import CommunityError


def _teacher(email="lee@school.kr", level="고등학교", region="부산"):
    user, _ = auth_service.register(email, "password123", "이선생", level, region, "진로")
    return user


def test_create_and_get_post():
    t = _teacher()
    pid = community_service.create_post(t.id, "info", "진로 변화 공유", "이렇게 전달했어요")
    post, comments = community_service.get_post_with_comments(pid)
    assert post.title == "진로 변화 공유"
    assert post.author_name == "이선생"
    assert comments == []


def test_seminar_requires_event_detail():
    t = _teacher()
    with pytest.raises(CommunityError):
        community_service.create_post(t.id, "seminar", "워크숍", "내용")
    pid = community_service.create_post(
        t.id, "seminar", "워크숍", "내용", event_at="7/12 14:00", online_url="https://x.kr"
    )
    post, _ = community_service.get_post_with_comments(pid)
    assert post.event_at == "7/12 14:00"


def test_non_seminar_clears_event_fields():
    t = _teacher()
    pid = community_service.create_post(
        t.id, "info", "제목", "내용", event_at="버려져야 함", location="여기"
    )
    post, _ = community_service.get_post_with_comments(pid)
    assert post.event_at is None and post.location is None


def test_post_validation():
    t = _teacher()
    with pytest.raises(CommunityError):
        community_service.create_post(t.id, "info", "", "내용")
    with pytest.raises(CommunityError):
        community_service.create_post(t.id, "bogus", "제목", "내용")


def test_feed_filters_by_category_and_region():
    seoul = _teacher("a@s.kr", "중학교", "서울")
    busan = _teacher("b@s.kr", "고등학교", "부산")
    community_service.create_post(seoul.id, "info", "서울 정보", "내용")
    community_service.create_post(busan.id, "seminar", "부산 세미나", "내용", location="부산")

    assert len(community_service.list_feed()) == 2
    assert len(community_service.list_feed(category="seminar")) == 1
    assert community_service.list_feed(region="서울")[0].title == "서울 정보"


def test_comments_flow():
    t = _teacher()
    pid = community_service.create_post(t.id, "support", "고민이 있어요", "내용")
    community_service.add_comment(pid, t.id, "응원합니다")
    _, comments = community_service.get_post_with_comments(pid)
    assert len(comments) == 1 and comments[0].body == "응원합니다"
    with pytest.raises(CommunityError):
        community_service.add_comment(pid, t.id, "   ")


def test_profile_lists_own_posts():
    t = _teacher()
    community_service.create_post(t.id, "info", "글1", "내용")
    community_service.create_post(t.id, "info", "글2", "내용")
    teacher, posts = community_service.get_profile(t.id)
    assert teacher.name == "이선생"
    assert len(posts) == 2


def test_missing_post_raises():
    with pytest.raises(CommunityError):
        community_service.get_post_with_comments(9999)
