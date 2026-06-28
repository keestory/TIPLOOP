"""도메인 데이터 구조.

순수 데이터만 담는다. 다른 레이어를 import하지 않는다.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    """가입한 교사."""

    id: int
    email: str
    name: str
    school_level: str  # 유치원 | 초등학교 | 중학교 | 고등학교
    region: str
    subject: str  # 담당 과목/학년 (자유 입력)
    created_at: str


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


@dataclass(frozen=True)
class Comment:
    """글에 달린 댓글."""

    id: int
    post_id: int
    author_id: int
    body: str
    created_at: str
    author_name: str | None = None
    author_school_level: str | None = None
