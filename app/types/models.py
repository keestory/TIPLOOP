"""도메인 데이터 구조.

순수 데이터만 담는다. 다른 레이어를 import하지 않는다.
"""

from __future__ import annotations


from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    """가입한 교사. 인증은 Supabase(구글/카카오), 프로필은 우리가 보관."""

    id: int
    auth_id: str  # Supabase auth 사용자 id
    name: str
    created_at: str
    email: str | None = None
    avatar_url: str | None = None
    provider: str | None = None  # google | kakao
    phone: str | None = None
    phone_verified: bool = False
    # 온보딩에서 채우는 값 (소셜이 주지 않음) — 완료 전엔 None
    school_level: str | None = None
    region: str | None = None
    subject: str = ""

    @property
    def is_onboarded(self) -> bool:
        """학교급·지역을 채웠으면 온보딩 완료."""
        return bool(self.school_level and self.region)


@dataclass(frozen=True)
class Post:
    """글. 카테고리(정보공유/세미나/고민나눔)로 세 기능을 통합한다."""

    id: int
    author_id: int
    category: str  # info | seminar | support
    title: str
    body: str
    created_at: str
    # 세미나 전용 (nullable)
    event_at: str | None = None
    location: str | None = None
    online_url: str | None = None
    # 조회 시 채워지는 작성자 표시 정보 (join 결과)
    author_name: str | None = None
    author_school_level: str | None = None
    author_region: str | None = None
    # 인게이지먼트 지표 (집계 결과)
    reaction_count: int = 0
    comment_count: int = 0


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
    author_school_level: str | None = None
    reaction_count: int = 0


@dataclass(frozen=True)
class Thread:
    """최상위 댓글 + 그 답글들. 화면 렌더링용 묶음."""

    comment: Comment
    replies: tuple[Comment, ...] = ()
