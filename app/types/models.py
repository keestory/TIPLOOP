"""도메인 데이터 구조.

순수 데이터만 담는다. 다른 레이어를 import하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MediaAttachment:
    """비공개 Supabase Storage에 둔 연구 노트 첨부 메타데이터."""

    bucket: str
    path: str
    kind: str  # image | video
    mime_type: str
    file_name: str
    size_bytes: int


@dataclass(frozen=True)
class User:
    """가입한 실무자 회원. 인증은 Supabase(Google), 프로필은 우리가 보관."""

    id: int
    auth_id: str  # Supabase auth 사용자 id
    name: str
    created_at: str
    email: str | None = None
    avatar_url: str | None = None
    provider: str | None = None  # google
    # 온보딩에서 채우는 값 (소셜이 주지 않음) — 완료 전엔 None
    job_role: str | None = None   # 직군
    years: str | None = None      # 연차
    industry: str | None = None   # 업종
    topics: tuple[str, ...] = ()  # 관심 주제 (온보딩 2단계, 피드 개인화 씨앗)
    agreed_terms: bool = False    # 약관·개인정보 동의 (신규 가입 첫 단계)
    has_seen_tour: bool = False   # 첫 로그인 코치마크 투어를 봤는지
    checklist_dismissed: bool = False  # 홈 시작 체크리스트를 닫았는지

    @property
    def is_onboarded(self) -> bool:
        """직군·연차를 채웠으면 온보딩 완료."""
        return bool(self.job_role and self.years)


@dataclass(frozen=True)
class Post:
    """글. 카테고리(팁/레퍼런스/질문/회고)로 종류를 나눈다."""

    id: int
    author_id: int
    category: str  # tip | reference | question | retro
    title: str
    body: str
    created_at: str
    link_url: str | None = None   # 레퍼런스 참고 링크 (선택)
    image_url: str | None = None  # 주석 이미지 (선택)
    video_url: str | None = None  # 첨부 영상 (선택)
    # 조회 시 채워지는 작성자 표시 정보 (join 결과)
    author_name: str | None = None
    author_job_role: str | None = None
    author_years: str | None = None
    # 인게이지먼트 지표 (집계 결과)
    reaction_count: int = 0   # 공감(♥)
    comment_count: int = 0
    helpful_count: int = 0    # 도움됐어요(💡)
    review_count: int = 0     # 적용 후기
    analysis_mode: str | None = None
    analysis_template_version: str | None = None
    selected_question_ids: tuple[str, ...] | None = None
    attachments: tuple[MediaAttachment, ...] = ()


@dataclass(frozen=True)
class Comment:
    """글에 달린 댓글. parent_id가 있으면 답글이다."""

    id: int
    post_id: int
    author_id: int
    body: str
    created_at: str
    parent_id: int | None = None
    author_name: str | None = None
    author_job_role: str | None = None
    reaction_count: int = 0


@dataclass(frozen=True)
class Review:
    """적용 후기 — 글을 실제로 써보고 남기는 결과/후기."""

    id: int
    post_id: int
    author_id: int
    body: str
    created_at: str
    author_name: str | None = None
    author_job_role: str | None = None
    post_title: str | None = None  # 주간 다이제스트 등 글 목록 없이 보여줄 때만 채움


@dataclass(frozen=True)
class MediaComment:
    """영상 위 특정 시각·위치에 달린 코멘트."""

    id: int
    post_id: int
    author_id: int
    t_seconds: float
    x: float
    y: float
    body: str
    created_at: str
    author_name: str | None = None


@dataclass(frozen=True)
class Thread:
    """최상위 댓글 + 그 답글들. 화면 렌더링용 묶음."""

    comment: Comment
    replies: tuple[Comment, ...] = ()


@dataclass(frozen=True)
class Crew:
    """크루 — 동료들과 함께 쓰는 주간 기록 공간 (2~12명)."""

    id: int
    name: str
    invite_code: str
    created_by: int
    created_at: str
    topic: str | None = None
    member_count: int = 0


@dataclass(frozen=True)
class CrewEntry:
    """크루의 주간 기록 한 조각 — 한 줄 팁·배움·근황."""

    id: int
    crew_id: int
    author_id: int
    week: str  # ISO 주 (예: 2026-W28)
    body: str
    created_at: str
    author_name: str | None = None


@dataclass(frozen=True)
class Notification:
    """활동 알림. 내 글에 달린 후기·도움·댓글, 팔로우, 구독 주제의 새 글."""

    id: int
    user_id: int                     # 받는 사람
    kind: str                        # review | helpful | comment | reply | follow | topic_post | crew
    created_at: str
    actor_id: int | None = None      # 행동한 사람 (topic_post는 글쓴이)
    post_id: int | None = None       # 관련 글
    topic: str | None = None         # 관련 주제 (topic_post) 또는 크루 이름 (crew)
    crew_id: int | None = None       # 관련 크루
    read_at: str | None = None       # 읽은 시각 (안 읽었으면 None)
    # 조회 시 채워지는 표시 정보 (join)
    actor_name: str | None = None
    post_title: str | None = None
    ago: str | None = None           # "5분 전" 등 표시용

    @property
    def is_unread(self) -> bool:
        return self.read_at is None
