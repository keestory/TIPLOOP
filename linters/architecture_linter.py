"""
아키텍처 린터

레이어 의존성 규칙을 기계적으로 강제합니다.
위반 시 에이전트 친화적 오류 메시지를 제공합니다.

Usage:
    python linters/architecture_linter.py [project_root]
"""

import ast
import os
import sys
from dataclasses import dataclass
from pathlib import Path


# 레이어 정의: 인덱스가 낮을수록 상위 레이어 (다른 레이어에 의존하면 안 됨)
LAYER_ORDER = {
    "types": 0,
    "config": 1,
    "providers": 2,
    "repo": 3,
    "service": 4,
    "runtime": 5,
    "ui": 6,
}

# 특별 허용: 어떤 레이어든 import 가능한 모듈
EXEMPT_MODULES = {"typing", "dataclasses", "abc", "enum", "pathlib", "os", "json", "logging"}
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache"}


def iter_python_files(project_root: Path):
    """생성물·의존성 디렉터리를 순회 전에 제외한다."""
    for root, directories, files in os.walk(project_root):
        directories[:] = [name for name in directories if name not in SKIP_DIRS]
        for name in files:
            if name.endswith(".py"):
                yield Path(root) / name


@dataclass
class LintViolation:
    """린트 위반"""
    file: str
    line: int
    rule: str
    message: str
    fix_hint: str
    severity: str = "error"  # error, warning

    def format(self) -> str:
        """에이전트 친화적 오류 메시지"""
        return (
            f"[{self.severity.upper()}] {self.file}:{self.line}\n"
            f"  규칙: {self.rule}\n"
            f"  메시지: {self.message}\n"
            f"  수정 방법: {self.fix_hint}\n"
        )


def detect_layer(file_path: str) -> str | None:
    """파일 경로에서 레이어 판별"""
    path_lower = file_path.lower()
    for layer in LAYER_ORDER:
        if f"/{layer}/" in path_lower or f"/{layer}." in path_lower:
            return layer
    return None


def extract_imports(file_path: Path) -> list[tuple[int, str]]:
    """AST를 사용하여 import 추출"""
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append((node.lineno, node.module))

    return imports


def check_layer_dependencies(project_root: Path) -> list[LintViolation]:
    """레이어 의존성 위반 검사"""
    violations = []

    for py_file in iter_python_files(project_root):

        rel_path = str(py_file.relative_to(project_root))
        current_layer = detect_layer(rel_path)
        if current_layer is None:
            continue

        current_idx = LAYER_ORDER[current_layer]
        imports = extract_imports(py_file)

        for line_no, module_name in imports:
            # 표준 라이브러리/외부 패키지 무시
            top_module = module_name.split(".")[0]
            if top_module in EXEMPT_MODULES:
                continue

            # import된 모듈의 레이어 판별
            for layer, idx in LAYER_ORDER.items():
                if layer in module_name.lower() and idx > current_idx:
                    violations.append(LintViolation(
                        file=rel_path,
                        line=line_no,
                        rule="ARCH-001: 레이어 의존성 위반",
                        message=(
                            f"'{current_layer}' 레이어(#{current_idx})에서 "
                            f"'{layer}' 레이어(#{idx})를 import했습니다."
                        ),
                        fix_hint=(
                            f"의존성 방향은 위에서 아래로만 허용됩니다.\n"
                            f"  허용: types → config → providers → repo → service → runtime → ui\n"
                            f"  현재: '{current_layer}' → '{layer}' (역방향, 금지)\n"
                            f"  해결: 공통 인터페이스를 상위 레이어에 정의하거나, "
                            f"의존성 주입 패턴을 사용하세요."
                        ),
                    ))

    return violations


def check_file_sizes(project_root: Path, max_lines: int = 300) -> list[LintViolation]:
    """파일 크기 제한 검사"""
    violations = []

    for py_file in iter_python_files(project_root):

        try:
            lines = py_file.read_text(encoding="utf-8").splitlines()
            if len(lines) > max_lines:
                rel_path = str(py_file.relative_to(project_root))
                violations.append(LintViolation(
                    file=rel_path,
                    line=len(lines),
                    rule="SIZE-001: 파일 크기 초과",
                    message=f"{len(lines)}줄 (최대 {max_lines}줄)",
                    fix_hint=(
                        f"파일을 기능별로 분리하세요.\n"
                        f"  - 클래스별로 별도 파일 생성\n"
                        f"  - 헬퍼 함수를 utils 모듈로 이동\n"
                        f"  - 상수/설정을 config 모듈로 분리"
                    ),
                    severity="warning",
                ))
        except Exception:
            pass

    return violations


def run_all(project_root: Path) -> list[LintViolation]:
    """모든 린트 규칙 실행"""
    violations = []
    violations.extend(check_layer_dependencies(project_root))
    violations.extend(check_file_sizes(project_root))
    return violations


def main():
    """CLI 진입점"""
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    violations = run_all(root)

    if violations:
        print(f"\n아키텍처 린트: {len(violations)}건 위반 발견\n")
        for v in violations:
            print(v.format())
        sys.exit(1)
    else:
        print("아키텍처 린트: 위반 없음")
        sys.exit(0)


if __name__ == "__main__":
    main()
