"""린터 패키지.

개별 린터가 공통 ``LintViolation``을 import할 때 순환 import가 생기지 않도록
진입점은 지연 import한다.
"""


def run_architecture_lint(project_root):
    from linters.architecture_linter import run_all

    return run_all(project_root)


def run_naming_lint(project_root):
    from linters.naming_linter import run_all

    return run_all(project_root)


def run_structure_validation(project_root):
    from linters.structure_validator import run_all

    return run_all(project_root)

__all__ = [
    "run_architecture_lint",
    "run_naming_lint",
    "run_structure_validation",
]
