"""
TestAgent — 테스트 생성 및 실행 에이전트

테스트를 작성하고 실행하며, 커버리지를 확인합니다.
"""

from pathlib import Path
from agents.base_agent import BaseAgent


class TestAgent(BaseAgent):
    name = "tester"
    description = "테스트 생성, 실행, 커버리지 확인을 수행하는 에이전트"

    SYSTEM_PROMPT = """당신은 소프트웨어 테스트 전문 에이전트입니다.

## 역할
- 테스트를 작성하고 실행합니다.
- 테스트 커버리지를 확인합니다.
- 실패하는 테스트의 원인을 분석합니다.

## 테스트 원칙
1. 경계 조건과 엣지 케이스를 우선 테스트
2. 단위 테스트와 통합 테스트를 구분
3. 테스트는 독립적이고 반복 가능해야 함
4. 의미 있는 assert 메시지 포함
5. 픽스처와 팩토리를 활용하여 중복 최소화

## 출력 형식

### 테스트 파일: <경로>
```python
<테스트 코드>
```

### 실행 결과
- 통과: N개
- 실패: N개
- 커버리지: N%
"""

    def get_system_prompt(self) -> str:
        return self.SYSTEM_PROMPT

    async def execute(self, task_description: str, context: dict = None) -> str:
        context = context or {}

        # 대상 코드 읽기
        code_content = ""
        if "files" in context:
            for f in context["files"][:3]:
                content = self.read_file(f)
                if not content.startswith("[ERROR]"):
                    code_content += f"\n### {f}\n```\n{content[:2000]}\n```\n"

        messages = [
            {"role": "user", "content": (
                f"## 태스크\n{task_description}\n\n"
                f"## 대상 코드\n{code_content}"
            )},
        ]

        result = await self.call_model(messages, max_tokens=8192)
        self.log(f"테스트 생성/실행 완료: {task_description[:50]}")
        return result

    async def generate_tests(self, source_file: str) -> str:
        """소스 파일에 대한 테스트 생성"""
        return await self.execute(
            f"다음 파일에 대한 포괄적인 테스트를 작성하세요: {source_file}",
            {"files": [source_file]},
        )

    async def run_tests(self, test_command: str = "python -m pytest") -> dict:
        """테스트 실행"""
        result = self.run_command(test_command)
        return {
            "success": result["success"],
            "output": result["stdout"],
            "errors": result["stderr"],
        }

    async def check_coverage(self, source_dir: str = ".") -> dict:
        """커버리지 확인"""
        result = self.run_command(f"python -m pytest --cov={source_dir} --cov-report=term-missing")
        return {
            "output": result["stdout"],
            "success": result["success"],
        }
