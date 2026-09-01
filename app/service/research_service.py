"""개인 서비스 연구 노트 도메인 로직.

기존 posts 테이블의 ``reference`` 카테고리를 재사용하되, 모든 조회와 수정은
작성자 id를 조건으로 삼는다. 공개 커뮤니티 기능과 개인 노트 경계를 분리하기
위해 라우트는 이 모듈만 사용한다.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from app.config.settings import WRITE_TEMPLATES
from app.repo import posts
from app.types.models import Post


class ResearchError(ValueError):
    """연구 노트 동작 실패. 메시지는 사용자에게 보여줄 수 있다."""


def list_notes(user_id: int, search: str = "") -> list[Post]:
    """내 서비스 분석 노트를 최신순으로 찾는다."""
    return posts.list_posts(
        category="reference",
        author_id=user_id,
        search=search.strip() or None,
        sort="new",
    )


def list_actionable_notes(user_id: int, search: str = "") -> list[Post]:
    """`실제로 적용할 것`을 적은 내 노트만 돌려준다."""
    return [
        post
        for post in list_notes(user_id, search)
        if section_values(post.body).get("실제로 적용할 것", "")
    ]


def get_note(post_id: int, user_id: int) -> Post:
    """내 서비스 분석 노트 한 건. 없거나 남의 글이면 같은 오류를 낸다."""
    post = posts.get_owned_post(post_id, user_id)
    if post is None or post.category != "reference":
        raise ResearchError("연구 노트를 찾을 수 없습니다.")
    return post


def get_owned_record(post_id: int, user_id: int) -> Post:
    """이전 카테고리를 포함해 작성자 본인의 기록만 가져온다."""
    post = posts.get_owned_post(post_id, user_id)
    if post is None:
        raise ResearchError("기록을 찾을 수 없습니다.")
    return post


def create_note(user_id: int, title: str, body: str, link_url: str = "") -> int:
    """검증 후 개인 서비스 분석 노트를 만든다."""
    title, body, link_url = _clean(title, body, link_url)
    return posts.create_post(
        author_id=user_id,
        category="reference",
        title=title,
        body=body,
        link_url=link_url or None,
    )


def update_note(
    post_id: int,
    user_id: int,
    title: str,
    body: str,
    link_url: str = "",
) -> None:
    """소유권을 SQL 조건으로 재검사해 노트를 수정한다."""
    title, body, link_url = _clean(title, body, link_url)
    if not posts.update_owned_post(
        post_id=post_id,
        author_id=user_id,
        title=title,
        body=body,
        link_url=link_url or None,
    ):
        raise ResearchError("연구 노트를 찾을 수 없습니다.")


def _clean(title: str, body: str, link_url: str) -> tuple[str, str, str]:
    title = (title or "").strip()
    body = (body or "").strip()
    link_url = (link_url or "").strip()
    if not title:
        raise ResearchError("서비스명을 입력해 주세요.")
    if not body:
        raise ResearchError("관찰 내용을 한 칸 이상 채워 주세요.")
    if link_url:
        parsed = urlsplit(link_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ResearchError("서비스 링크는 http:// 또는 https:// 주소를 입력해 주세요.")
    return title, body, link_url


def section_values(body: str) -> dict[str, str]:
    """``라벨\n내용`` 블록으로 저장한 본문을 편집 폼 값으로 되돌린다.

    내용 안의 빈 줄은 유지한다. 알 수 없는 예전 라벨은 무시해 과거 데이터가
    새 템플릿 때문에 폼을 깨뜨리지 않게 한다.
    """
    labels = [section["label"] for section in WRITE_TEMPLATES["reference"]]
    values: dict[str, list[str]] = {label: [] for label in labels}
    label_targets = {label: label for label in labels}
    # 공개 커뮤니티 시절 reference 템플릿으로 쓴 데이터도 편집 화면에서 보존한다.
    label_targets.update({
        "무엇을 봤나요": "분석한 이유",
        "핵심 인사이트": "가져올 아이디어",
    })
    current: str | None = None
    for line in (body or "").splitlines():
        if line in label_targets:
            current = label_targets[line]
        elif current is not None:
            values[current].append(line)
    parsed = {label: "\n".join(lines).strip() for label, lines in values.items()}
    if body.strip() and not any(parsed.values()):
        parsed["분석한 이유"] = body.strip()
    return parsed


def legacy_preamble(body: str) -> str:
    """첫 정식 라벨 앞의 이전 자유 형식 메모를 손실 없이 분리한다.

    정식 라벨이 전혀 없는 과거 본문은 ``분석한 이유``로 편집하므로 여기서는
    빈 값을 돌려 중복 저장을 피한다.
    """
    labels = {section["label"] for section in WRITE_TEMPLATES["reference"]}
    labels.update({"무엇을 봤나요", "핵심 인사이트"})
    lines = (body or "").splitlines()
    first_label = next((index for index, line in enumerate(lines) if line in labels), None)
    if first_label in {None, 0}:
        return ""
    return "\n".join(lines[:first_label]).strip()


def detail_groups(body: str) -> list[dict]:
    """값이 있는 그룹만 상세 화면용 구조로 만든다."""
    values = section_values(body)
    groups: list[dict] = []
    legacy = legacy_preamble(body)
    if legacy:
        groups.append({
            "no": "00",
            "name": "이전 메모",
            "items": [{"label": "이전 형식에서 가져온 내용", "value": legacy, "highlight": False}],
        })

    current: dict | None = None
    for section in WRITE_TEMPLATES["reference"]:
        if section.get("group"):
            current = {
                "no": section["group_no"],
                "name": section["group"],
                "items": [],
            }
            groups.append(current)
        value = values.get(section["label"], "")
        if value and current is not None:
            current["items"].append({
                "label": section["label"],
                "value": value,
                "highlight": section.get("hl", False),
            })
    return [group for group in groups if group["items"]]


def progress(post: Post) -> dict[str, int]:
    """노트가 채운 섹션 수와 백분율을 계산한다."""
    values = section_values(post.body)
    total = len(values)
    done = sum(1 for value in values.values() if value)
    percent = round(done / total * 100) if total else 0
    return {"done": done, "total": total, "percent": percent}


def present_notes(items: list[Post]) -> list[dict]:
    """템플릿에서 쓰기 쉬운 노트+진행도 묶음."""
    return [{"post": post, "progress": progress(post)} for post in items]


def dashboard(user_id: int) -> dict:
    """홈 워크벤치용 최근 노트와 최소 지표."""
    items = list_notes(user_id)
    presented = present_notes(items)
    completed = sum(1 for item in presented if item["progress"]["percent"] == 100)
    applied = sum(
        1
        for post in items
        if section_values(post.body).get("실제로 적용할 것", "")
    )
    return {
        "notes": presented,
        "recent": presented[:5],
        "total": len(items),
        "completed": completed,
        "applied": applied,
    }
