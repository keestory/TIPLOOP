"""
구조 검증기

프로젝트의 디렉토리 구조와 필수 파일이 올바른지 검증합니다.
지식 베이스(docs/)의 구조와 교차 링크를 검증합니다.

Usage:
    python linters/structure_validator.py [project_root]
"""

import re
import sys
from pathlib import Path

try:
    from linters.architecture_linter import LintViolation
except ModuleNotFoundError:  # 직접 ``python linters/structure_validator.py`` 실행
    from architecture_linter import LintViolation


# 필수 파일 정의
REQUIRED_FILES = [
    "AGENTS.md",
    "ARCHITECTURE.md",
    "docs/DESIGN.md",
    "docs/QUALITY_SCORE.md",
    "docs/SECURITY.md",
    "docs/RELIABILITY.md",
    "docs/PLANS.md",
    "docs/PRODUCT_SENSE.md",
    "docs/design-docs/index.md",
    "docs/design-docs/core-beliefs.md",
    "docs/product-specs/index.md",
    "docs/exec-plans/tech-debt-tracker.md",
]

# 필수 디렉토리
REQUIRED_DIRS = [
    "docs",
    "docs/design-docs",
    "docs/exec-plans",
    "docs/exec-plans/active",
    "docs/exec-plans/completed",
    "docs/product-specs",
    "docs/references",
    "docs/generated",
]


def check_required_files(project_root: Path) -> list[LintViolation]:
    """필수 파일 존재 검사"""
    violations = []

    for required in REQUIRED_FILES:
        full_path = project_root / required
        if not full_path.exists():
            violations.append(LintViolation(
                file=required,
                line=0,
                rule="STRUCT-001: 필수 파일 부재",
                message=f"'{required}'가 존재하지 않습니다.",
                fix_hint=f"'{required}' 파일을 생성하세요. 템플릿은 templates/ 디렉토리를 참조하세요.",
            ))

    return violations


def check_required_dirs(project_root: Path) -> list[LintViolation]:
    """필수 디렉토리 존재 검사"""
    violations = []

    for required in REQUIRED_DIRS:
        full_path = project_root / required
        if not full_path.exists():
            violations.append(LintViolation(
                file=required,
                line=0,
                rule="STRUCT-002: 필수 디렉토리 부재",
                message=f"'{required}/' 디렉토리가 존재하지 않습니다.",
                fix_hint=f"'{required}/' 디렉토리를 생성하세요.",
            ))

    return violations


def check_doc_links(project_root: Path) -> list[LintViolation]:
    """문서 내 교차 링크 유효성 검사"""
    violations = []

    for md_file in project_root.rglob("*.md"):
        if (
            "venv" in str(md_file)
            or "node_modules" in str(md_file)
            or ".vercel" in str(md_file)
        ):
            continue

        try:
            content = md_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        rel_path = str(md_file.relative_to(project_root))

        # 마크다운 링크 추출: [text](path)
        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)

        for line_idx, line in enumerate(content.splitlines(), 1):
            for text, href in re.findall(r'\[([^\]]+)\]\(([^)]+)\)', line):
                # 외부 링크 무시
                if href.startswith("http") or href.startswith("#"):
                    continue

                # 상대 경로 해석
                linked_path = (md_file.parent / href).resolve()
                if not linked_path.exists():
                    violations.append(LintViolation(
                        file=rel_path,
                        line=line_idx,
                        rule="STRUCT-003: 깨진 문서 링크",
                        message=f"'{text}' → '{href}'가 존재하지 않습니다.",
                        fix_hint=f"링크 대상 파일을 생성하거나 경로를 수정하세요.",
                        severity="warning",
                    ))

    return violations


def check_agents_md_freshness(project_root: Path) -> list[LintViolation]:
    """AGENTS.md가 현재 구조를 반영하는지 검사"""
    violations = []
    agents_path = project_root / "AGENTS.md"

    if not agents_path.exists():
        return violations

    content = agents_path.read_text(encoding="utf-8")

    # AGENTS.md에 언급된 디렉토리가 실제 존재하는지
    mentioned_dirs = re.findall(r'`(\w+)/`', content)
    for d in mentioned_dirs:
        if not (project_root / d).exists():
            violations.append(LintViolation(
                file="AGENTS.md",
                line=0,
                rule="STRUCT-004: AGENTS.md 불일치",
                message=f"AGENTS.md에서 언급된 '{d}/' 디렉토리가 존재하지 않습니다.",
                fix_hint="AGENTS.md를 현재 프로젝트 구조에 맞게 업데이트하세요.",
                severity="warning",
            ))

    # AGENTS.md 크기 검사 (목차 역할이므로 200줄 이하 권장)
    lines = content.splitlines()
    if len(lines) > 200:
        violations.append(LintViolation(
            file="AGENTS.md",
            line=len(lines),
            rule="STRUCT-005: AGENTS.md 크기 초과",
            message=f"AGENTS.md가 {len(lines)}줄입니다 (권장: 200줄 이하).",
            fix_hint=(
                "AGENTS.md는 목차(맵)이지 백과사전이 아닙니다.\n"
                "  상세 내용은 docs/ 디렉토리의 개별 문서로 이동하세요."
            ),
            severity="warning",
        ))

    return violations


def run_all(project_root: Path) -> list[LintViolation]:
    """모든 구조 검증 실행"""
    violations = []
    violations.extend(check_required_files(project_root))
    violations.extend(check_required_dirs(project_root))
    violations.extend(check_doc_links(project_root))
    violations.extend(check_agents_md_freshness(project_root))
    return violations


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    violations = run_all(root)

    if violations:
        errors = [v for v in violations if v.severity == "error"]
        warnings = [v for v in violations if v.severity == "warning"]

        print(f"\n구조 검증: {len(errors)}건 오류, {len(warnings)}건 경고\n")
        for v in violations:
            print(v.format())

        if errors:
            sys.exit(1)
    else:
        print("구조 검증: 통과")

    sys.exit(0)


if __name__ == "__main__":
    main()
