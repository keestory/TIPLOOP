"""
CodeAgent — 코드 생성 및 수정 에이전트

코드를 작성하고, 버그를 수정하며, 리팩터링을 수행합니다.
아키텍처 규칙과 설계 원칙을 준수합니다.
"""

from pathlib import Path
from agents.base_agent import BaseAgent


class CodeAgent(BaseAgent):
    name = "coder"
    description = "코드 생성, 수정, 리팩터링을 수행하는 에이전트"

    SYSTEM_PROMPT = """당신은 소프트웨어 엔지니어링 코드 에이전트입니다.

## 역할
- 코드를 작성하고, 버그를 수정하며, 리팩터링을 수행합니다.
- 아키텍처 규칙과 설계 원칙을 엄격히 준수합니다.

## 아키텍처 규칙
레이어드 도메인 아키텍처를 따릅니다:
Types → Config → Providers → Repo → Service → Runtime → UI
의존성은 위에서 아래로만 흐릅니다.

## 코딩 규칙
1. 경계에서 데이터 형태를 파싱 (Pydantic 등)
2. 구조화된 로깅 사용
3. 파일당 최대 300줄
4. 단일 책임 원칙
5. 매직 넘버/문자열 금지
6. 테스트 가능한 코드 작성

## 출력 형식
코드 변경사항을 다음 형식으로 제공하세요:

### 파일: <경로>
```<언어>
<코드>
```

### 변경 요약
- 무엇을 변경했는지
- 왜 변경했는지
"""

    def get_system_prompt(self) -> str:
        # AGENTS.md에서 추가 컨텍스트 로드
        agents_md = self.read_agents_md()
        architecture = self.get_architecture()

        return (
            self.SYSTEM_PROMPT
            + "\n\n## 프로젝트 맵\n" + agents_md[:1500]
            + "\n\n## 아키텍처\n" + architecture[:1500]
        )

    async def execute(self, task_description: str, context: dict = None) -> str:
        context = context or {}

        # 관련 파일 읽기
        file_contents = ""
        if "files" in context:
            for f in context["files"][:5]:
                content = self.read_file(f)
                if not content.startswith("[ERROR]"):
                    file_contents += f"\n### 파일: {f}\n```\n{content[:2000]}\n```\n"

        messages = [
            {"role": "user", "content": (
                f"## 태스크\n{task_description}\n\n"
                f"## 관련 파일\n{file_contents}\n\n"
                f"## 추가 컨텍스트\n{context}"
            )},
        ]

        result = await self.call_model(
            messages,
            model="claude-sonnet-4-6",
            max_tokens=8192,
        )

        self.log(f"코드 생성 완료: {task_description[:50]}")
        return result

    async def fix_bug(self, bug_description: str, files: list[str] = None) -> str:
        """버그 수정 특화 메서드"""
        context = {"files": files or [], "mode": "bugfix"}
        return await self.execute(
            f"다음 버그를 수정하세요:\n\n{bug_description}\n\n"
            "1. 먼저 버그를 재현할 수 있는 테스트를 작성하세요\n"
            "2. 버그를 수정하세요\n"
            "3. 테스트가 통과하는지 확인하세요",
            context,
        )

    async def implement_feature(self, spec: str, files: list[str] = None) -> str:
        """기능 구현 특화 메서드"""
        context = {"files": files or [], "mode": "feature"}
        return await self.execute(
            f"다음 기능을 구현하세요:\n\n{spec}\n\n"
            "아키텍처 규칙을 준수하고, 테스트를 함께 작성하세요.",
            context,
        )

    async def refactor(self, target: str, goal: str, files: list[str] = None) -> str:
        """리팩터링 특화 메서드"""
        context = {"files": files or [], "mode": "refactor"}
        return await self.execute(
            f"다음을 리팩터링하세요:\n\n"
            f"대상: {target}\n"
            f"목표: {goal}\n\n"
            "기존 동작을 변경하지 않으면서 코드 품질을 개선하세요.",
            context,
        )
