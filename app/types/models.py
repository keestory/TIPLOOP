"""도메인 데이터 구조.

순수 데이터만 담는다. 다른 레이어를 import하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    """가입한 실무자 회원. 인증은 Supabase(구글/카카오), 프로필은 우리가 보관."""

    id: int
    auth_id: str  # Supabase auth 사용자 id
    name: str
    created_at: str
    email: str | None = None
    avatar_url: str | None = None
    provider: str | None = None  # google | kakao
    # 온보딩에서 채우는 값 (소셜이 주지 않음) — 완료 전엔 None
    job_role: str | None = None   # 직군
    years: str | None = None      # 연차
    industry: str | None = None   # 업종

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
