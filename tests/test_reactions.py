"""공감(반응)과 피드 정렬 테스트."""

from app.service import community_service, reaction_service


def test_toggle_post_reaction_on_off_and_count(make_member):
    author = make_member()
    reactor = make_member()
    pid = community_service.create_post(author.id, "tip", "글", "내용")

    assert reaction_service.toggle_post(pid, reactor.id) is True   # 켜짐
    post, _ = community_service.get_post_with_threads(pid)
    assert post.reaction_count == 1
    assert pid in reaction_service.viewer_post_reactions(reactor.id)

    assert reaction_service.toggle_post(pid, reactor.id) is False  # 다시 끔
    post, _ = community_service.get_post_with_threads(pid)
    assert post.reaction_count == 0


def test_reaction_is_one_per_user(make_member):
    author = make_member()
    r1 = make_member()
    r2 = make_member()
    pid = community_service.create_post(author.id, "tip", "글", "내용")
    reaction_service.toggle_post(pid, r1.id)
    reaction_service.toggle_post(pid, r1.id)  # 같은 사람 두 번 → 0
    reaction_service.toggle_post(pid, r2.id)  # 다른 사람 → +1
    post, _ = community_service.get_post_with_threads(pid)
    assert post.reaction_count == 1


def test_received_reaction_count_sums_posts_and_comments(make_member):
    author = make_member()
    fan = make_member()
    pid = community_service.create_post(author.id, "tip", "글", "내용")
    cid = community_service.add_comment(pid, author.id, "내 댓글")
    reaction_service.toggle_post(pid, fan.id)
    reaction_service.toggle_comment(cid, fan.id)
    assert reaction_service.received_count(author.id) == 2


def test_helpful_is_separate_from_reaction(make_member):
    author = make_member()
    reader = make_member()
    pid = community_service.create_post(author.id, "tip", "글", "내용")

    # 공감과 도움됐어요는 독립적으로 집계
    reaction_service.toggle_post(pid, reader.id)      # 공감만
    post, _ = community_service.get_post_with_threads(pid)
    assert post.reaction_count == 1 and post.helpful_count == 0

    assert reaction_service.toggle_helpful(pid, reader.id) is True
    post, _ = community_service.get_post_with_threads(pid)
    assert post.reaction_count == 1 and post.helpful_count == 1
    assert pid in reaction_service.viewer_helpful(reader.id)


def test_received_helpful_counts_across_posts(make_member):
    author = make_member()
    r1 = make_member()
    r2 = make_member()
    p1 = community_service.create_post(author.id, "tip", "a", "내용")
    p2 = community_service.create_post(author.id, "tip", "b", "내용")
    reaction_service.toggle_helpful(p1, r1.id)
    reaction_service.toggle_helpful(p1, r2.id)
    reaction_service.toggle_helpful(p2, r1.id)
    assert reaction_service.received_helpful(author.id) == 3


def test_toggle_comment_returns_post_id(make_member):
    author = make_member()
    pid = community_service.create_post(author.id, "tip", "글", "내용")
    cid = community_service.add_comment(pid, author.id, "댓글")
    assert reaction_service.toggle_comment(cid, author.id) == pid
    assert reaction_service.toggle_comment(9999, author.id) is None


def test_feed_sort_top_orders_by_reactions(make_member):
    a = make_member()
    fan = make_member()
    community_service.create_post(a.id, "tip", "공감없음", "내용")
    high = community_service.create_post(a.id, "tip", "공감많음", "내용")
    reaction_service.toggle_post(high, fan.id)

    top = community_service.list_feed(sort="top")
    assert top[0].title == "공감많음"
    new = community_service.list_feed(sort="new")
    assert new[0].id == high


def test_feed_sort_buzz_orders_by_comments(make_member):
    a = make_member()
    community_service.create_post(a.id, "tip", "조용", "내용")
    loud = community_service.create_post(a.id, "tip", "북적", "내용")
    community_service.add_comment(loud, a.id, "댓글1")
    community_service.add_comment(loud, a.id, "댓글2")
    buzz = community_service.list_feed(sort="buzz")
    assert buzz[0].title == "북적"
