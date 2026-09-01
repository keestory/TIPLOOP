"""
네이밍 컨벤션 린터

파일명, 클래스명, 함수명, 변수명의 네이밍 규칙을 검사합니다.

Usage:
    python linters/naming_linter.py [project_root]
"""

import ast
import re
import sys
from pathlib import Path

try:
    from linters.architecture_linter import LintViolation
except ModuleNotFoundError:  # 직접 ``python linters/naming_linter.py`` 실행
    from architecture_linter import LintViolation


# 네이밍 규칙
RULES = {
    "file": re.compile(r'^[a-z][a-z0-9_]*\.py$'),           # snake_case.py
    "class": re.compile(r'^[A-Z][a-zA-Z0-9]+$'),            # PascalCase
    "function": re.compile(r'^_?[a-z][a-z0-9_]*$'),         # snake_case
    "constant": re.compile(r'^[A-Z][A-Z0-9_]+$'),           # UPPER_SNAKE_CASE
    "variable": re.compile(r'^_?[a-z][a-z0-9_]*$'),         # snake_case
}


def check_file_names(project_root: Path) -> list[LintViolation]:
    """파일명 규칙 검사"""
    violations = []

    for py_file in project_root.rglob("*.py"):
        if "__pycache__" in str(py_file) or "venv" in str(py_file):
            continue

        if not RULES["file"].match(py_file.name) and py_file.name != "__init__.py":
            rel_path = str(py_file.relative_to(project_root))
            violations.append(LintViolation(
                file=rel_path,
                line=0,
                rule="NAME-001: 파일명 규칙 위반",
                message=f"'{py_file.name}'는 snake_case가 아닙니다.",
                fix_hint=f"파일명을 snake_case로 변경하세요: {py_file.stem.lower().replace('-', '_')}.py",
                severity="warning",
            ))

    return violations


def check_definitions(project_root: Path) -> list[LintViolation]:
    """클래스, 함수, 변수 네이밍 검사"""
    violations = []

    for py_file in project_root.rglob("*.py"):
        if "__pycache__" in str(py_file) or "venv" in str(py_file):
            continue

        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            continue

        rel_path = str(py_file.relative_to(project_root))

        for node in ast.walk(tree):
            # 클래스명 검사
            if isinstance(node, ast.ClassDef):
                if not RULES["class"].match(node.name):
                    violations.append(LintViolation(
                        file=rel_path,
                        line=node.lineno,
                        rule="NAME-002: 클래스명 규칙 위반",
                        message=f"'{node.name}'는 PascalCase가 아닙니다.",
                        fix_hint=f"클래스명을 PascalCase로 변경하세요.",
                        severity="warning",
                    ))

            # 함수명 검사
            elif isinstance(node, ast.FunctionDef):
                if not RULES["function"].match(node.name):
                    # __dunder__ 메서드 제외
                    if not (node.name.startswith("__") and node.name.endswith("__")):
                        violations.append(LintViolation(
                            file=rel_path,
                            line=node.lineno,
                            rule="NAME-003: 함수명 규칙 위반",
                            message=f"'{node.name}'는 snake_case가 아닙니다.",
                            fix_hint=f"함수명을 snake_case로 변경하세요.",
                            severity="warning",
                        ))

            # 모듈 레벨 상수 검사 (대문자로 시작하는 변수)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        name = target.id
                        # 모듈 레벨이고 대문자로 시작하면 상수로 간주
                        if name[0].isupper() and not RULES["constant"].match(name) and not RULES["class"].match(name):
                            violations.append(LintViolation(
                                file=rel_path,
                                line=node.lineno,
                                rule="NAME-004: 상수명 규칙 위반",
                                message=f"'{name}'는 UPPER_SNAKE_CASE가 아닙니다.",
                                fix_hint=f"상수명을 UPPER_SNAKE_CASE로 변경하세요.",
                                severity="warning",
                            ))

    return violations


def run_all(project_root: Path) -> list[LintViolation]:
    """모든 네이밍 규칙 실행"""
    violations = []
    violations.extend(check_file_names(project_root))
    violations.extend(check_definitions(project_root))
    return violations


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    violations = run_all(root)

    if violations:
        print(f"\n네이밍 린트: {len(violations)}건 위반 발견\n")
        for v in violations:
            print(v.format())
        sys.exit(1)
    else:
        print("네이밍 린트: 위반 없음")
        sys.exit(0)


if __name__ == "__main__":
    main()
