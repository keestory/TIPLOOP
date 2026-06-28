"""
에이전트 러너 (Agent Runner)

에이전트 생명주기를 관리하고, 병렬 실행을 지원합니다.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from orchestrator.config import OrchestratorConfig, AgentConfig
from orchestrator.task_decomposer import SubTask, TaskStatus

logger = logging.getLogger("harness.runner")


@dataclass
class AgentResult:
    """에이전트 실행 결과"""
    task_id: str
    agent_type: str
    success: bool
    output: str = ""
    files_changed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    tokens_used: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class AgentContext:
    """에이전트에 전달되는 컨텍스트 (점진적 공개)"""
    task: SubTask
    project_root: Path
    agents_md: str = ""
    relevant_docs: list[str] = field(default_factory=list)
    relevant_files: list[str] = field(default_factory=list)
    previous_results: list[AgentResult] = field(default_factory=list)

    def build_system_prompt(self) -> str:
        """에이전트 시스템 프롬프트 구성"""
        parts = [
            "당신은 소프트웨어 엔지니어링 에이전트입니다.",
            f"역할: {self.task.agent_type}",
            f"태스크: {self.task.title}",
            "",
            "## 프로젝트 맵 (AGENTS.md 요약)",
            self.agents_md[:2000] if self.agents_md else "(AGENTS.md 없음)",
        ]

        if self.relevant_docs:
            parts.append("\n## 관련 문서")
            for doc in self.relevant_docs[:3]:  # 최대 3개 문서만 (컨텍스트 절약)
                parts.append(f"\n### {doc}")

        if self.previous_results:
            parts.append("\n## 이전 에이전트 결과")
            for r in self.previous_results[-3:]:  # 최근 3개만
                parts.append(f"- [{r.agent_type}] {'성공' if r.success else '실패'}: {r.output[:200]}")

        return "\n".join(parts)

    def build_user_prompt(self) -> str:
        """사용자 프롬프트 구성"""
        parts = [
            f"## 태스크",
            f"**{self.task.title}**",
            "",
            self.task.description,
        ]

        if self.task.files_affected:
            parts.append(f"\n## 관련 파일: {', '.join(self.task.files_affected)}")

        if self.task.context:
            parts.append(f"\n## 추가 컨텍스트")
            parts.append(json.dumps(self.task.context, ensure_ascii=False, indent=2))

        return "\n".join(parts)


class AgentRunner:
    """에이전트 실행 관리자"""

    def __init__(self, config: OrchestratorConfig, client=None):
        self.config = config
        self.client = client
        self._running: dict[str, asyncio.Task] = {}
        self._results: dict[str, AgentResult] = {}

    async def run_task(self, task: SubTask, context: AgentContext) -> AgentResult:
        """단일 태스크 실행"""
        agent_config = self.config.get_agent_config(task.agent_type)
        task.status = TaskStatus.IN_PROGRESS

        logger.info(f"[{task.id}] 에이전트 시작: {task.agent_type} — {task.title}")
        start_time = time.time()

        try:
            result = await self._execute_agent(task, context, agent_config)
            task.status = TaskStatus.COMPLETED
            task.output = result.output
            logger.info(f"[{task.id}] 에이전트 완료: {task.agent_type} ({result.duration_seconds:.1f}s)")
        except Exception as e:
            result = AgentResult(
                task_id=task.id,
                agent_type=task.agent_type,
                success=False,
                errors=[str(e)],
                duration_seconds=time.time() - start_time,
            )
            task.status = TaskStatus.FAILED
            logger.error(f"[{task.id}] 에이전트 실패: {task.agent_type} — {e}")

        self._results[task.id] = result
        return result

    async def run_batch(self, tasks: list[SubTask], contexts: dict[str, AgentContext]) -> list[AgentResult]:
        """병렬 태스크 배치 실행"""
        semaphore = asyncio.Semaphore(self.config.max_concurrent_agents)

        async def _run_with_limit(task: SubTask) -> AgentResult:
            async with semaphore:
                ctx = contexts.get(task.id)
                if ctx is None:
                    ctx = AgentContext(task=task, project_root=self.config.project_root)
                return await self.run_task(task, ctx)

        results = await asyncio.gather(
            *[_run_with_limit(t) for t in tasks],
            return_exceptions=True,
        )

        final_results = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                final_results.append(AgentResult(
                    task_id=tasks[i].id,
                    agent_type=tasks[i].agent_type,
                    success=False,
                    errors=[str(r)],
                ))
            else:
                final_results.append(r)

        return final_results

    async def _execute_agent(
        self, task: SubTask, context: AgentContext, agent_config: AgentConfig
    ) -> AgentResult:
        """에이전트 API 호출 실행"""
        start_time = time.time()

        if self.client is None:
            # 드라이런 모드 — API 없이 시뮬레이션
            return AgentResult(
                task_id=task.id,
                agent_type=task.agent_type,
                success=True,
                output=f"[DRY RUN] {task.title} 완료 시뮬레이션",
                duration_seconds=time.time() - start_time,
            )

        system_prompt = context.build_system_prompt()
        user_prompt = context.build_user_prompt()

        response = await self.client.messages.create(
            model=agent_config.model,
            max_tokens=agent_config.max_tokens,
            temperature=agent_config.temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        output = response.content[0].text
        tokens_used = response.usage.input_tokens + response.usage.output_tokens

        return AgentResult(
            task_id=task.id,
            agent_type=task.agent_type,
            success=True,
            output=output,
            duration_seconds=time.time() - start_time,
            tokens_used=tokens_used,
        )

    def get_result(self, task_id: str) -> Optional[AgentResult]:
        """태스크 결과 조회"""
        return self._results.get(task_id)

    def get_all_results(self) -> dict[str, AgentResult]:
        """전체 결과 조회"""
        return dict(self._results)
