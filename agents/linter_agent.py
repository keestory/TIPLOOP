"""
LinterAgent — 아키텍처 린팅 에이전트

아키텍처 경계 위반을 감지하고 에이전트 친화적 오류 메시지를 제공합니다.
"""

from pathlib import Path
from agents.base_agent import BaseAgent


class LinterAgent(BaseAgent):
    name = "linter"
    description = "아키텍처 경계 위반을 감지하고 보고하는 에이전트"

    SYSTEM_PROMPT = """당신은 아키텍처 린팅 에이전트입니다.

## 역할
- 코드의 아키텍처 규칙 위반을 감지합니다.
- 에이전트 친화적인 오류 메시지를 제공합니다.
- 수정 방법을 구체적으로 안내합니다.

## 검사 규칙
1. 레이어 의존성 위반 (상위 레이어가 하위 레이어만 import)
2. 파일 크기 제한 (300줄 초과)
3. 네이밍 컨벤션 위반
4. 하드코딩된 시크릿
5. 순환 의존성
"""

    def get_system_prompt(self) -> str:
        return self.SYSTEM_PROMPT

    async def execute(self, task_description: str, context: dict = None) -> str:
        # 자동 린터 실행 후 결과를 AI에 전달
        lint_results = self.run_all_linters()

        messages = [
            {"role": "user", "content": (
                f"## 태스크\n{task_description}\n\n"
                f"## 린트 결과\n{lint_results}"
            )},
        ]
        result = await self.call_model(messages, max_tokens=4096)
        self.log(f"린팅 완료: {task_description[:50]}")
        return result

    def run_all_linters(self) -> str:
        """모든 린터 실행"""
        results = []

        # 아키텍처 린터
        arch_result = self._check_architecture()
        results.append(f"## 아키텍처 검사\n{arch_result}")

        # 파일 크기 린터
        size_result = self._check_file_sizes()
        results.append(f"## 파일 크기 검사\n{size_result}")

        # 시크릿 검사
        secret_result = self._check_secrets()
        results.append(f"## 시크릿 검사\n{secret_result}")

        return "\n\n".join(results)

    def _check_architecture(self) -> str:
        """아키텍처 규칙 검사"""
        # 레이어 정의 및 허용된 의존성
        layer_order = ["types", "config", "providers", "repo", "service", "runtime", "ui"]
        violations = []

        for py_file in self.project_root.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            try:
                content = py_file.read_text(encoding="utf-8")
            except Exception:
                continue

            rel_path = str(py_file.relative_to(self.project_root))

            # 현재 파일의 레이어 판별
            current_layer = None
            for layer in layer_order:
                if layer in rel_path.lower():
                    current_layer = layer
                    break

            if current_layer is None:
                continue

            current_idx = layer_order.index(current_layer)

            # import 분석
            for line in content.split("\n"):
                line = line.strip()
                if not (line.startswith("from ") or line.startswith("import ")):
                    continue
                for i, layer in enumerate(layer_order):
                    if layer in line.lower() and i > current_idx:
                        violations.append(
                            f"[위반] {rel_path}: "
                            f"'{current_layer}' 레이어에서 '{layer}' 레이어를 import\n"
                            f"  수정: 의존성 방향을 확인하세요. "
                            f"'{current_layer}'는 '{layer}'보다 상위 레이어입니다.\n"
                            f"  라인: {line}"
                        )

        if violations:
            return f"위반 {len(violations)}건 발견:\n\n" + "\n\n".join(violations)
        return "위반 없음"

    def _check_file_sizes(self, max_lines: int = 300) -> str:
        """파일 크기 제한 검사"""
        violations = []
        for py_file in self.project_root.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            try:
                lines = len(py_file.read_text(encoding="utf-8").splitlines())
                if lines > max_lines:
                    rel_path = str(py_file.relative_to(self.project_root))
                    violations.append(
                        f"[위반] {rel_path}: {lines}줄 (최대 {max_lines}줄)\n"
                        f"  수정: 파일을 기능별로 분리하세요."
                    )
            except Exception:
                pass

        if violations:
            return f"위반 {len(violations)}건:\n\n" + "\n\n".join(violations)
        return "위반 없음"

    def _check_secrets(self) -> str:
        """하드코딩된 시크릿 검사"""
        import re
        secret_patterns = [
            (r'(?:api_key|apikey|secret|password|token)\s*=\s*["\'][^"\']{8,}["\']', "하드코딩된 시크릿"),
            (r'sk-[a-zA-Z0-9]{20,}', "OpenAI API 키"),
            (r'AKIA[0-9A-Z]{16}', "AWS 액세스 키"),
        ]

        violations = []
        for py_file in self.project_root.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            try:
                content = py_file.read_text(encoding="utf-8")
                for pattern, desc in secret_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        rel_path = str(py_file.relative_to(self.project_root))
                        violations.append(
                            f"[위반] {rel_path}: {desc} 발견\n"
                            f"  수정: 환경 변수로 이동하세요. os.environ.get() 사용."
                        )
            except Exception:
                pass

        if violations:
            return f"위반 {len(violations)}건:\n\n" + "\n\n".join(violations)
        return "위반 없음"
