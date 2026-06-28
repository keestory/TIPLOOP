"""
PlannerAgent — 실행 계획 수립 에이전트

복잡한 작업의 실행 계획을 수립하고 docs/exec-plans/에 저장합니다.
사람의 승인이 필요한 낮은 자율성 에이전트입니다.
"""

import time
from pathlib import Path
from agents.base_agent import BaseAgent


class PlannerAgent(BaseAgent):
    name = "planner"
    description = "실행 계획을 수립하고 태스크를 분해하는 에이전트"

    SYSTEM_PROMPT = """당신은 소프트웨어 아키텍트이자 프로젝트 플래너입니다.

## 역할
- 복잡한 작업의 실행 계획을 수립합니다.
- 태스크를 에이전트가 처리 가능한 단위로 분해합니다.
- 리스크와 의존성을 식별합니다.
- 아키텍처 결정을 문서화합니다.

## 계획 원칙
1. 깊이 우선 분해: 큰 목표를 빌딩 블록으로 나누기
2. 검증 가능한 중간 산출물 정의
3. 리스크가 높은 항목 먼저 처리
4. 각 단계의 성공 기준 명시

## 출력 형식

# 실행 계획: <제목>

## 목표
<달성하려는 것>

## 배경
<왜 필요한지>

## 접근법
<어떻게 구현할 것인지>

## 태스크 분해
1. [ ] 태스크 1 (에이전트: coder)
   - 설명
   - 성공 기준
   - 의존성
2. [ ] 태스크 2 ...

## 리스크
- 리스크 1: 대응 방안

## 의사결정 로그
- 결정 1: 이유
"""

    def get_system_prompt(self) -> str:
        architecture = self.get_architecture()
        design = self.read_doc("DESIGN.md")
        return (
            self.SYSTEM_PROMPT
            + "\n\n## 현재 아키텍처\n" + architecture[:2000]
            + "\n\n## 설계 원칙\n" + design[:1000]
        )

    async def execute(self, task_description: str, context: dict = None) -> str:
        context = context or {}

        # 기존 계획 참조
        active_plans = self._list_active_plans()
        plans_context = ""
        if active_plans:
            plans_context = "\n## 진행 중인 계획\n" + "\n".join(f"- {p}" for p in active_plans)

        messages = [
            {"role": "user", "content": (
                f"## 요청\n{task_description}\n\n"
                f"{plans_context}\n\n"
                f"실행 계획을 수립하세요. 각 태스크에 담당 에이전트를 지정하세요."
            )},
        ]

        result = await self.call_model(
            messages,
            model="claude-opus-4-6",  # 복잡한 추론에 Opus 사용
            max_tokens=8192,
        )

        self.log(f"계획 수립 완료: {task_description[:50]}")
        return result

    async def create_exec_plan(self, prompt: str) -> str:
        """실행 계획 생성 및 저장"""
        plan_content = await self.execute(prompt)

        # 파일명 생성
        timestamp = int(time.time())
        safe_title = prompt[:30].replace(" ", "-").replace("/", "-")
        filename = f"plan-{timestamp}-{safe_title}.md"

        # 저장
        plan_path = f"docs/exec-plans/active/{filename}"
        self.write_file(plan_path, plan_content)

        self.log(f"실행 계획 저장: {plan_path}")
        return plan_content

    async def complete_plan(self, plan_filename: str) -> str:
        """계획 완료 처리 (active → completed 이동)"""
        active_path = self.project_root / "docs" / "exec-plans" / "active" / plan_filename
        completed_path = self.project_root / "docs" / "exec-plans" / "completed" / plan_filename

        if not active_path.exists():
            return f"[ERROR] 계획 파일 없음: {plan_filename}"

        content = active_path.read_text(encoding="utf-8")
        completed_path.parent.mkdir(parents=True, exist_ok=True)
        completed_path.write_text(content, encoding="utf-8")
        active_path.unlink()

        return f"계획 완료 처리: {plan_filename}"

    def _list_active_plans(self) -> list[str]:
        """진행 중인 계획 목록"""
        active_dir = self.project_root / "docs" / "exec-plans" / "active"
        if not active_dir.exists():
            return []
        return [f.name for f in active_dir.glob("*.md")]
