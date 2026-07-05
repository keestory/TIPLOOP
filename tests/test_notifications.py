"""알림·팔로우 시스템 테스트 — 활동이 알림을 만드는지, 팔로우 토글."""

from app.repo import members
from app.service import community_service as C
from app.service import follow_service as Fs
from app.service import notification_service as N
from app.service import reaction_service as R


def test_review_notifies_author(make_member):
    a = make_member(name="글쓴이")
    b = make_member(name="후기어")
    pid = C.create_post(a.id, "tip", "제목", "본문")
    C.add_review(pid, b.id, "효과 봤어요")
    items = N.list_recent(a.id)
    assert any(n.kind == "review" and n.actor_name == "후기어" for n in items)
    assert N.unread_count(a.id) == 1


def test_helpful_notifies_only_on_toggle_on(make_member):
    a = make_member()
    b = make_member()
    pid = C.create_post(a.id, "tip", "제목", "본문")
    R.toggle_helpful(pid, b.id)   # on  → 알림 1
    R.toggle_helpful(pid, b.id)   # off → 알림 없음
    R.toggle_helpful(pid, b.id)   # on  → 알림 1
    helpful = [n for n in N.list_recent(a.id) if n.kind == "helpful"]
    assert len(helpful) == 2


def test_self_action_does_not_notify(make_member):
    a = make_member()
    pid = C.create_post(a.id, "tip", "제목", "본문")
    R.toggle_helpful(pid, a.id)
    C.add_review(pid, a.id, "내 글 내가 후기")
    C.add_comment(pid, a.id, "내 댓글")
    assert N.unread_count(a.id) == 0


def test_comment_notifies_author_and_reply_notifies_parent(make_member):
    a = make_member(name="글쓴이")
    b = make_member(name="댓글1")
    c = make_member(name="댓글2")
    pid = C.create_post(a.id, "tip", "제목", "본문")
    c1 = C.add_comment(pid, b.id, "첫 댓글")          # a에게 '댓글'
    C.add_comment(pid, c.id, "답글", parent_id=c1)    # a에게 '댓글', b에게 '답글'
    assert len([n for n in N.list_recent(a.id) if n.kind == "comment"]) == 2
    b_items = N.list_recent(b.id)
    assert [n.kind for n in b_items] == ["reply"]     # 원댓글 작성자는 '답글'만


def test_follow_toggle_status_and_notify(make_member):
    a = make_member(name="대상")
    b = make_member(name="팔로워")
    assert Fs.toggle(b.id, a.id) is True
    st = Fs.status(b.id, a.id)
    assert st["is_following"] and st["followers"] == 1 and st["following"] == 0
    assert any(n.kind == "follow" and n.actor_name == "팔로워" for n in N.list_recent(a.id))
    assert Fs.toggle(b.id, a.id) is False              # 언팔로우
    assert Fs.status(b.id, a.id)["followers"] == 0


def test_follow_self_is_noop(make_member):
    a = make_member()
    assert Fs.toggle(a.id, a.id) is False
    assert Fs.status(a.id, a.id)["followers"] == 0


def test_topic_post_notifies_subscribers(make_member):
    author = make_member(name="글쓴이")
    sub = make_member(name="구독자")
    other = make_member(name="무관")
    members.set_topics(sub.id, ["리텐션"])
    C.create_post(author.id, "tip", "리텐션 올리는 법", "코호트 분석")
    subs = [n for n in N.list_recent(sub.id) if n.kind == "topic_post"]
    assert len(subs) == 1 and subs[0].topic == "리텐션"
    assert N.unread_count(other.id) == 0


def test_mark_all_read(make_member):
    a = make_member()
    b = make_member()
    pid = C.create_post(a.id, "tip", "제목", "본문")
    R.toggle_helpful(pid, b.id)
    assert N.unread_count(a.id) == 1
    N.mark_all_read(a.id)
    assert N.unread_count(a.id) == 0
