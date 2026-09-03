"""개인 연구 노트의 접근 경계와 핵심 화면 스모크 테스트."""

import pytest

from app.config.settings import (
    REFERENCE_APPLICATION_LABEL,
    REFERENCE_IMAGE_MAX_BYTES,
    REFERENCE_MEDIA_BUCKETS,
    REFERENCE_MEDIA_MAX_FILES,
    REFERENCE_MEDIA_MAX_TOTAL_BYTES,
    REFERENCE_MEDIA_MAX_VIDEOS,
    REFERENCE_MEDIA_TYPES,
    REFERENCE_QUICK_QUESTION_IDS,
    REFERENCE_REQUIRED_FINAL_ID,
    REFERENCE_TEMPLATE_VERSION,
    REFERENCE_VIDEO_MAX_BYTES,
    WRITE_TEMPLATES,
)
from app.service import research_service
from app.types.models import Post
from app.types.models import MediaAttachment
from app.types.models import User
from app.ui import routes_community, routes_legacy, routes_post, routes_research_share
from app.ui.app_factory import create_app


@pytest.mark.no_db
def test_private_route_functions_redirect_without_session():
    calls = (
        lambda: routes_community.feed(None, user=None),
        lambda: routes_community.explore(None, user=None),
        lambda: routes_post.new_post_write(None, user=None),
        lambda: routes_post.post_detail(None, 1, user=None),
        lambda: routes_post.edit_post(None, 1, user=None),
        lambda: routes_research_share.post_share(None, 1, user=None),
    )
    for call in calls:
        response = call()
        assert response.status_code == 303
        assert response.headers["location"] == "/login"


@pytest.mark.no_db
def test_new_research_route_exposes_complete_media_limits():
    media = routes_post._media_context()

    assert media["image_max_bytes"] == REFERENCE_IMAGE_MAX_BYTES
    assert media["video_max_bytes"] == REFERENCE_VIDEO_MAX_BYTES


@pytest.mark.no_db
def test_research_templates_render_for_signed_in_user():
    user = User(
        id=7,
        auth_id="auth-7",
        name="연구자",
        created_at="2026-09-01",
        job_role="PM",
        years="3~5년",
    )
    env = create_app().state.templates.env
    shared = {"current_user": user, "nav_unread": 0}

    home = env.get_template("index.html").render(
        **shared,
        dashboard={"notes": [], "recent": [], "total": 0, "completed": 0, "applied": 0},
    )
    library = env.get_template("explore.html").render(**shared, q="", focus="", results=[])
    form = env.get_template("post_write.html").render(
        **shared,
        category="reference",
        sections=WRITE_TEMPLATES["reference"],
        form={"link_url": ""},
        section_values={},
        editing=False,
        analysis_mode="quick",
        selected_question_ids=REFERENCE_QUICK_QUESTION_IDS,
        analysis_template_version=REFERENCE_TEMPLATE_VERSION,
        attachments=[],
        quick_question_ids=REFERENCE_QUICK_QUESTION_IDS,
        required_final_id=REFERENCE_REQUIRED_FINAL_ID,
        media_types=REFERENCE_MEDIA_TYPES,
        media_buckets=REFERENCE_MEDIA_BUCKETS,
        media_accept=",".join(REFERENCE_MEDIA_TYPES),
        media_max_files=REFERENCE_MEDIA_MAX_FILES,
        media_max_videos=REFERENCE_MEDIA_MAX_VIDEOS,
        media_max_total_bytes=REFERENCE_MEDIA_MAX_TOTAL_BYTES,
        image_max_bytes=REFERENCE_IMAGE_MAX_BYTES,
        video_max_bytes=REFERENCE_VIDEO_MAX_BYTES,
    )

    assert "좋은 서비스에는" in home
    assert "내 노트" in library
    assert "5분만 쓰기" in form
    assert "골라서 쓰기" in form
    assert REFERENCE_APPLICATION_LABEL in form
    assert ">APPLY<" in form
    assert 'name="selected_question_ids"' in form
    assert "서비스 노트 저장" in form
    assert '/static/research-form.js?v=5' in form
    assert "tiploop:draft:new:user:7" in form
    assert '"tiploop:draft:new"' not in form
    assert 'type="file"' in form
    assert 'accept="image/jpeg,image/png,image/webp,image/gif,video/mp4,video/webm,video/quicktime"' in form
    assert "기본으로 나만 볼 수 있고, 원할 때 공유 링크에 포함" in form

    post = Post(
        id=12,
        author_id=user.id,
        category="reference",
        title="Notion",
        body="분석한 이유\n문서 흐름을 보기 위해",
        created_at="2026-09-01 10:00",
    )
    detail = env.get_template("post_detail.html").render(
        **shared,
        post=post,
        progress=research_service.progress(post),
        groups=research_service.detail_groups(post.body),
        attachments=[],
        analysis_mode_label="이전 방식",
        saved="",
    )
    assert "관찰의 출발점" in detail
    assert "NOTE #012" in detail
    assert "<h2>제품</h2>" not in detail


@pytest.mark.no_db
def test_shared_research_renders_generic_image_and_video_without_private_paths():
    env = create_app().state.templates.env
    post = Post(
        id=12,
        author_id=0,
        category="reference",
        title="서비스 연구",
        body="기획과 UX\n좋은 흐름",
        created_at="2026-09-03 10:00",
        attachments=(
            MediaAttachment(
                "tiploop-research-images", "private/drafts/draft/image.jpg",
                "image", "image/jpeg", "사내화면.jpg", 1024,
            ),
            MediaAttachment(
                "tiploop-research-videos", "private/drafts/draft/video.mp4",
                "video", "video/mp4", "회의영상.mp4", 2048,
            ),
        ),
    )
    attachments = research_service.attachment_dicts(post.attachments)
    html = env.get_template("shared_research.html").render(
        current_user=None,
        site_url="https://tiploop.vercel.app",
        brand="TIPLOOP",
        tagline="서비스 연구",
        post=post,
        progress=research_service.progress(post),
        groups=research_service.detail_groups(post.body),
        attachments=attachments,
        media_tokens=("D" * 43, "E" * 43),
        media_endpoint="https://project.supabase.co/functions/v1/shared-media",
    )

    assert "?grant=" + "D" * 43 in html
    assert "스크린샷 1" in html
    assert "영상 2" in html
    assert "controls playsinline" in html
    assert "사내화면.jpg" not in html
    assert "회의영상.mp4" not in html
    assert "private/drafts" not in html
    assert "SHARED NOTE" in html
    assert "공유된 노트" in html


@pytest.mark.no_db
def test_retired_social_mutations_return_gone():
    user = User(
        id=7,
        auth_id="auth-7",
        name="연구자",
        created_at="2026-09-01",
        job_role="PM",
        years="3~5년",
    )
    assert routes_legacy.react_comment(None, 99, user=user).status_code == 410
    assert routes_community.follow_user(None, 99, user=user).status_code == 410
