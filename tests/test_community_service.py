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


def test_contribution_heatmap_levels():
    from datetime import date
    from app.types.models import Post

    def _p(days_ago):
        d = date(2026, 7, 5).toordinal() - days_ago
        from datetime import date as _d
        return Post(id=1, author_id=1, category="tip", title="t", body="b",
                    created_at=_d.fromordinal(d).isoformat())

    today = date(2026, 7, 5)
    # 이번 주에 3건 → 레벨 2, 지지난 주 1건 → 레벨 1, 나머지 0
    posts = [_p(0), _p(1), _p(2), _p(15)]
    heat = community_service.contribution_heatmap(posts, weeks=12, today=today)
    assert len(heat) == 12
    assert heat[-1] == 2            # 최근 주(오른쪽 끝) 3건
    assert heat[-3] == 1            # 2주 전 1건
    assert heat[0] == 0            # 11주 전 없음


def test_checklist_progress_and_completion(make_member):
    from app.repo import members
    from app.service import reaction_service as R

    m = make_member()                       # 온보딩 완료, 주제 없음
    cl = community_service.onboarding_checklist(m)
    assert cl["done"] == 1 and cl["total"] == 3       # 프로필만 완료
    assert [i["done"] for i in cl["items"]] == [True, False, False]

    m = members.set_topics(m.id, ["리텐션"])          # 주제 선택 → 2/3
    cl = community_service.onboarding_checklist(m)
    assert cl["done"] == 2

    other = make_member()
    pid = community_service.create_post(other.id, "tip", "글", "본문")
    R.toggle_helpful(pid, m.id)                        # 첫 반응 → 전부 완료
    assert community_service.onboarding_checklist(members.get(m.id)) is None


def test_checklist_hidden_when_dismissed_or_not_onboarded(make_member):
    from app.repo import members

    m = make_member()
    members.dismiss_checklist(m.id)
    assert community_service.onboarding_checklist(members.get(m.id)) is None

    raw = make_member(onboard=False)                   # 온보딩 미완료
    assert community_service.onboarding_checklist(raw) is None
    assert community_service.onboarding_checklist(None) is None


def test_contribution_heatmap_ignores_old_and_bad():
    from datetime import date
    from app.types.models import Post
    old = Post(id=1, author_id=1, category="tip", title="t", body="b", created_at="2020-01-01")
    bad = Post(id=2, author_id=1, category="tip", title="t", body="b", created_at="")
    heat = community_service.contribution_heatmap([old, bad], today=date(2026, 7, 5))
    assert heat == [0] * 12


def test_search_matches_title_and_body(make_member):
    t = make_member()
    community_service.create_post(t.id, "tip", "리텐션 올리는 법", "코호트 분석부터")
    community_service.create_post(t.id, "tip", "결제 팁", "리텐션 지표도 함께 보세요")
    community_service.create_post(t.id, "tip", "무관한 글", "관련 없는 내용")
    hits = community_service.list_feed(search="리텐션")
    assert len(hits) == 2                       # 제목 1 + 본문 1
    titles = {p.title for p in hits}
    assert "무관한 글" not in titles


def test_search_escapes_wildcards(make_member):
    t = make_member()
    community_service.create_post(t.id, "tip", "100% 전환", "완전 전환 달성")
    community_service.create_post(t.id, "tip", "일반 글", "그냥 내용")
    # '%'는 리터럴로 처리 — 모든 글이 걸리면 안 된다
    hits = community_service.list_feed(search="100%")
    assert len(hits) == 1 and hits[0].title == "100% 전환"


def _backdate_post(post_id, days_ago):
    from app.repo.database import get_connection
    with get_connection() as conn:
        conn.execute(
            "UPDATE posts SET created_at = now() - interval '%s days' WHERE id = %s"
            % (days_ago, post_id)
        )


def _backdate_review(review_id, days_ago):
    from app.repo.database import get_connection
    with get_connection() as conn:
        conn.execute(
            "UPDATE reviews SET created_at = now() - interval '%s days' WHERE id = %s"
            % (days_ago, review_id)
        )


def test_week_start_is_monday():
    from datetime import date
    # 2026-07-11은 토요일 → 그 주 월요일은 07-06
    assert community_service.week_start(date(2026, 7, 11)) == date(2026, 7, 6)


def test_weekly_digest_top_post_only_counts_this_week(make_member):
    from app.repo import reactions

    me = make_member()
    old_author = make_member()
    pid_old = community_service.create_post(old_author.id, "tip", "지난주 인기글", "본문")
    reactions.toggle_post_helpful(pid_old, me.id)
    _backdate_post(pid_old, 10)  # 지난 주로 밀어냄

    pid_new = community_service.create_post(old_author.id, "tip", "이번주 글", "본문")
    reactions.toggle_post_helpful(pid_new, me.id)

    d = community_service.weekly_digest(me)
    assert d["top_post"].id == pid_new       # 지난주 글은 helpful이 더 많아도 제외


def test_weekly_digest_followed_posts_excludes_self_and_others(make_member):
    from app.service import follow_service

    me = make_member()
    friend = make_member()
    stranger = make_member()
    follow_service.toggle(me.id, friend.id)
    community_service.create_post(friend.id, "tip", "친구 글", "본문")
    community_service.create_post(stranger.id, "tip", "모르는 사람 글", "본문")
    community_service.create_post(me.id, "tip", "내 글", "본문")

    d = community_service.weekly_digest(me)
    titles = {p.title for p in d["followed_posts"]}
    assert titles == {"친구 글"}


def test_weekly_digest_waiting_excludes_my_own_questions(make_member):
    me = make_member()
    other = make_member()
    community_service.create_post(other.id, "question", "동료 질문", "본문")
    community_service.create_post(me.id, "question", "내 질문", "본문")

    d = community_service.weekly_digest(me)
    titles = {q.title for q in d["waiting"]}
    assert titles == {"동료 질문"}


def test_weekly_digest_my_reviews_since_week_start(make_member):
    me = make_member()
    reviewer = make_member()
    pid = community_service.create_post(me.id, "tip", "내 글", "본문")
    rid_new = community_service.add_review(pid, reviewer.id, "최근 후기")
    rid_old = community_service.add_review(pid, reviewer.id, "오래된 후기")
    _backdate_review(rid_old, 10)

    d = community_service.weekly_digest(me)
    bodies = {r.body for r in d["my_reviews"]}
    assert bodies == {"최근 후기"}
    assert d["my_reviews"][0].post_title == "내 글"


def test_weekly_digest_empty_when_nothing(make_member):
    me = make_member()
    d = community_service.weekly_digest(me)
    assert d["has_any"] is False
    assert d["top_post"] is None
    assert d["followed_posts"] == d["waiting"] == d["my_reviews"] == []


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
