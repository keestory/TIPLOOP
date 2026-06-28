"""
태스크 분해기 (Task Decomposer)

사용자 프롬프트를 분석하여 실행 가능한 서브태스크로 분해합니다.
각 서브태스크에 적절한 에이전트를 할당하고 의존성 그래프를 생성합니다.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import json
import uuid


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class TaskPriority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class SubTask:
    """분해된 서브태스크"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    description: str = ""
    agent_type: str = "coder"  # planner, coder, reviewer, tester, doc_gardener
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    depends_on: list[str] = field(default_factory=list)
    blocked_by: list[str] = field(default_factory=list)
    output: Optional[str] = None
    files_affected: list[str] = field(default_factory=list)
    context: dict = field(default_factory=dict)

    def is_ready(self, completed_tasks: set[str]) -> bool:
        """의존성이 모두 완료되어 실행 가능한지 확인"""
        return all(dep in completed_tasks for dep in self.depends_on)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "agent_type": self.agent_type,
            "status": self.status.value,
            "priority": self.priority.value,
            "depends_on": self.depends_on,
            "files_affected": self.files_affected,
        }


@dataclass
class TaskPlan:
    """태스크 실행 계획"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    original_prompt: str = ""
    summary: str = ""
    tasks: list[SubTask] = field(default_factory=list)
    decision_log: list[dict] = field(default_factory=list)

    def get_ready_tasks(self) -> list[SubTask]:
        """현재 실행 가능한 태스크 목록"""
        completed = {t.id for t in self.tasks if t.status == TaskStatus.COMPLETED}
        return [
            t for t in self.tasks
            if t.status == TaskStatus.PENDING and t.is_ready(completed)
        ]

    def get_next_batch(self) -> list[SubTask]:
        """병렬 실행 가능한 다음 태스크 배치"""
        ready = self.get_ready_tasks()
        # 우선순위 순으로 정렬
        ready.sort(key=lambda t: list(TaskPriority).index(t.priority))
        return ready

    def is_complete(self) -> bool:
        """모든 태스크 완료 여부"""
        return all(
            t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
            for t in self.tasks
        )

    def log_decision(self, decision: str, reason: str):
        """의사결정 기록"""
        self.decision_log.append({
            "decision": decision,
            "reason": reason,
        })

    def to_markdown(self) -> str:
        """실행 계획을 마크다운으로 변환"""
        lines = [
            f"# 실행 계획: {self.summary}",
            "",
            f"**원본 프롬프트**: {self.original_prompt}",
            "",
            "## 태스크",
            "",
        ]
        for t in self.tasks:
            status_emoji = {
                TaskStatus.PENDING: "[ ]",
                TaskStatus.IN_PROGRESS: "[~]",
                TaskStatus.COMPLETED: "[x]",
                TaskStatus.FAILED: "[!]",
                TaskStatus.BLOCKED: "[-]",
            }[t.status]
            deps = f" (의존: {', '.join(t.depends_on)})" if t.depends_on else ""
            lines.append(f"- {status_emoji} **{t.title}** ({t.agent_type}){deps}")
            lines.append(f"  {t.description}")

        if self.decision_log:
            lines.extend(["", "## 의사결정 로그", ""])
            for d in self.decision_log:
                lines.append(f"- **{d['decision']}**: {d['reason']}")

        return "\n".join(lines)


class TaskDecomposer:
    """사용자 프롬프트를 서브태스크로 분해"""

    # 태스크 유형별 기본 워크플로
    WORKFLOW_TEMPLATES = {
        "feature": [
            ("planner", "실행 계획 수립"),
            ("coder", "코드 구현"),
            ("tester", "테스트 작성 및 실행"),
            ("reviewer", "코드 리뷰"),
        ],
        "bugfix": [
            ("coder", "버그 재현"),
            ("coder", "수정 구현"),
            ("tester", "수정 검증"),
            ("reviewer", "코드 리뷰"),
        ],
        "refactor": [
            ("quality_scorer", "현재 품질 평가"),
            ("planner", "리팩터링 계획"),
            ("coder", "리팩터링 실행"),
            ("tester", "회귀 테스트"),
            ("reviewer", "코드 리뷰"),
        ],
        "docs": [
            ("doc_gardener", "문서 스캔 및 업데이트"),
            ("reviewer", "문서 리뷰"),
        ],
    }

    def __init__(self, client=None):
        self.client = client

    async def decompose(self, prompt: str, context: dict = None) -> TaskPlan:
        """프롬프트를 태스크 플랜으로 분해"""
        if self.client is None:
            return self._rule_based_decompose(prompt, context)
        return await self._ai_decompose(prompt, context)

    def _rule_based_decompose(self, prompt: str, context: dict = None) -> TaskPlan:
        """규칙 기반 태스크 분해 (AI 없이)"""
        prompt_lower = prompt.lower()
        context = context or {}

        # 키워드로 워크플로 유형 결정
        if any(kw in prompt_lower for kw in ["버그", "수정", "fix", "bug", "에러", "error"]):
            workflow_type = "bugfix"
        elif any(kw in prompt_lower for kw in ["리팩터", "refactor", "정리", "개선"]):
            workflow_type = "refactor"
        elif any(kw in prompt_lower for kw in ["문서", "doc", "readme", "가이드"]):
            workflow_type = "docs"
        else:
            workflow_type = "feature"

        template = self.WORKFLOW_TEMPLATES[workflow_type]
        plan = TaskPlan(original_prompt=prompt, summary=f"{workflow_type}: {prompt[:50]}...")

        prev_id = None
        for agent_type, description in template:
            task = SubTask(
                title=description,
                description=f"{description} — {prompt[:100]}",
                agent_type=agent_type,
                depends_on=[prev_id] if prev_id else [],
            )
            plan.tasks.append(task)
            prev_id = task.id

        plan.log_decision(
            f"워크플로 유형: {workflow_type}",
            f"키워드 분석 결과 '{workflow_type}' 워크플로 선택"
        )

        return plan

    async def _ai_decompose(self, prompt: str, context: dict = None) -> TaskPlan:
        """AI 기반 태스크 분해"""
        system_prompt = """당신은 소프트웨어 엔지니어링 태스크 분해 전문가입니다.
사용자의 요청을 분석하여 실행 가능한 서브태스크로 분해하세요.

각 서브태스크에는 다음을 지정하세요:
- title: 태스크 제목
- description: 구체적인 설명
- agent_type: 담당 에이전트 (planner, coder, reviewer, tester, doc_gardener, quality_scorer, linter)
- depends_on: 의존하는 태스크 인덱스 (0-based)
- priority: critical, high, medium, low

JSON 배열로 응답하세요."""

        context_str = json.dumps(context or {}, ensure_ascii=False)
        user_msg = f"프로젝트 컨텍스트:\n{context_str}\n\n요청:\n{prompt}"

        response = await self.client.messages.create(
            model="claude-opus-4-6",
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_msg}],
        )

        # 응답 파싱
        text = response.content[0].text
        # JSON 블록 추출
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        tasks_data = json.loads(text)
        plan = TaskPlan(original_prompt=prompt, summary=prompt[:80])

        task_ids = []
        for i, td in enumerate(tasks_data):
            task = SubTask(
                title=td["title"],
                description=td.get("description", ""),
                agent_type=td.get("agent_type", "coder"),
                priority=TaskPriority(td.get("priority", "medium")),
            )
            task_ids.append(task.id)
            plan.tasks.append(task)

        # 의존성 연결
        for i, td in enumerate(tasks_data):
            deps = td.get("depends_on", [])
            plan.tasks[i].depends_on = [task_ids[d] for d in deps if d < len(task_ids)]

        return plan
