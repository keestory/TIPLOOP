"""공감(반응)과 피드 정렬 테스트."""

from app.service import community_service, reaction_service


def test_toggle_post_reaction_on_off_and_count(make_teacher):
    author = make_teacher()
    reactor = make_teacher()
    pid = community_service.create_post(author.id, "info", "글", "내용")

    assert reaction_service.toggle_post(pid, reactor.id) is True   # 켜짐
    post, _ = community_service.get_post_with_threads(pid)
    assert post.reaction_count == 1
    assert pid in reaction_service.viewer_post_reactions(reactor.id)

    assert reaction_service.toggle_post(pid, reactor.id) is False  # 다시 끔
    post, _ = community_service.get_post_with_threads(pid)
    assert post.reaction_count == 0


def test_reaction_is_one_per_user(make_teacher):
    author = make_teacher()
    r1 = make_teacher()
    r2 = make_teacher()
    pid = community_service.create_post(author.id, "info", "글", "내용")
    reaction_service.toggle_post(pid, r1.id)
    reaction_service.toggle_post(pid, r1.id)  # 같은 사람 두 번 → 0
    reaction_service.toggle_post(pid, r2.id)  # 다른 사람 → +1
    post, _ = community_service.get_post_with_threads(pid)
    assert post.reaction_count == 1


def test_received_reaction_count_sums_posts_and_comments(make_teacher):
    author = make_teacher()
    fan = make_teacher()
    pid = community_service.create_post(author.id, "info", "글", "내용")
    cid = community_service.add_comment(pid, author.id, "내 댓글")
    reaction_service.toggle_post(pid, fan.id)
    reaction_service.toggle_comment(cid, fan.id)
    assert reaction_service.received_count(author.id) == 2


def test_toggle_comment_returns_post_id(make_teacher):
    author = make_teacher()
    pid = community_service.create_post(author.id, "info", "글", "내용")
    cid = community_service.add_comment(pid, author.id, "댓글")
    assert reaction_service.toggle_comment(cid, author.id) == pid
    assert reaction_service.toggle_comment(9999, author.id) is None


def test_feed_sort_top_orders_by_reactions(make_teacher):
    a = make_teacher()
    fan = make_teacher()
    community_service.create_post(a.id, "info", "공감없음", "내용")
    high = community_service.create_post(a.id, "info", "공감많음", "내용")
    reaction_service.toggle_post(high, fan.id)

    top = community_service.list_feed(sort="top")
    assert top[0].title == "공감많음"
    new = community_service.list_feed(sort="new")
    assert new[0].id == high


def test_feed_sort_buzz_orders_by_comments(make_teacher):
    a = make_teacher()
    community_service.create_post(a.id, "info", "조용", "내용")
    loud = community_service.create_post(a.id, "info", "북적", "내용")
    community_service.add_comment(loud, a.id, "댓글1")
    community_service.add_comment(loud, a.id, "댓글2")
    buzz = community_service.list_feed(sort="buzz")
    assert buzz[0].title == "북적"
