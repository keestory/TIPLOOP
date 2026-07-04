"""영상 첨부와 지점 코멘트 테스트."""

import pytest

from app.service import community_service
from app.service.community_service import CommunityError


def _video_post(make_member):
    m = make_member()
    pid = community_service.create_post(
        m.id, "reference", "영상글", "내용", video_url="https://cdn.example.com/x.mp4"
    )
    return m, pid


def test_video_url_stored(make_member):
    _, pid = _video_post(make_member)
    post, _ = community_service.get_post_with_threads(pid)
    assert post.video_url == "https://cdn.example.com/x.mp4"


def test_add_and_list_media_comment(make_member):
    m, pid = _video_post(make_member)
    mc = community_service.add_media_comment(pid, m.id, 12.5, 0.3, 0.7, "여기 인터랙션 좋다")
    assert mc.t_seconds == 12.5 and mc.body == "여기 인터랙션 좋다"
    assert mc.author_name is not None
    lst = community_service.list_media_comments(pid)
    assert len(lst) == 1 and lst[0].x == 0.3


def test_media_comment_clamps_coords(make_member):
    m, pid = _video_post(make_member)
    mc = community_service.add_media_comment(pid, m.id, -5, 1.5, -0.2, "범위 밖")
    assert mc.t_seconds == 0.0 and mc.x == 1.0 and mc.y == 0.0


def test_media_comment_requires_video(make_member):
    m = make_member()
    pid = community_service.create_post(m.id, "tip", "영상 없음", "내용")
    with pytest.raises(CommunityError):
        community_service.add_media_comment(pid, m.id, 1, 0.5, 0.5, "x")


def test_media_comment_requires_body(make_member):
    m, pid = _video_post(make_member)
    with pytest.raises(CommunityError):
        community_service.add_media_comment(pid, m.id, 1, 0.5, 0.5, "   ")
