"""연구 노트 본문을 화면과 진행도 구조로 변환한다."""

from __future__ import annotations

from app.config.settings import REFERENCE_QUESTION_IDS, WRITE_TEMPLATES
from app.types.models import Post


def section_values(body: str) -> dict[str, str]:
    """``라벨\n내용`` 블록을 편집 폼 값으로 되돌린다."""
    labels = [section["label"] for section in WRITE_TEMPLATES["reference"]]
    values: dict[str, list[str]] = {label: [] for label in labels}
    label_targets = {label: label for label in labels}
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
    """첫 정식 라벨 앞의 이전 자유 형식 메모를 손실 없이 분리한다."""
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
            "items": [{
                "label": "이전 형식에서 가져온 내용",
                "value": legacy,
                "highlight": False,
            }],
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
    """선택된 질문을 기준으로 채운 섹션 수와 백분율을 계산한다."""
    values = section_values(post.body)
    stored = post.selected_question_ids
    if not stored or not set(stored).issubset(REFERENCE_QUESTION_IDS):
        selected = REFERENCE_QUESTION_IDS
    else:
        selected_set = set(stored)
        selected = tuple(
            question_id for question_id in REFERENCE_QUESTION_IDS
            if question_id in selected_set
        )
    label_by_id = {
        section["id"]: section["label"] for section in WRITE_TEMPLATES["reference"]
    }
    total = len(selected)
    done = sum(1 for question_id in selected if values.get(label_by_id[question_id], ""))
    percent = round(done / total * 100) if total else 0
    return {"done": done, "total": total, "percent": percent}


def present_notes(items: list[Post]) -> list[dict]:
    """템플릿에서 쓰기 쉬운 노트+진행도 묶음."""
    return [{"post": post, "progress": progress(post)} for post in items]
