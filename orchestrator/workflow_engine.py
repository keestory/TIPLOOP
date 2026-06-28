"""
워크플로 엔진 v2

이전: 에이전트 리스트를 순차 실행
이후: 병렬 트랙, 게이트, 분기, 핸드오프 프로토콜을 지원

워크플로 구성요소:
  - Step: 단일 에이전트 실행
  - Parallel: 여러 에이전트 동시 실행
  - Gate: go/no-go 판단 (실패 시 재작업 또는 중단)
  - Branch: 조건에 따라 다른 경로
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Union

from orchestrator.claude_runner import ClaudeRunner, ClaudeResult
from orchestrator.handoff import build_handoff_prompt, AGENT_CONTRACTS

logger = logging.getLogger("harness.workflow")


# ── 워크플로 노드 타입 ──

class GateAction(Enum):
    PROCEED = "proceed"         # 다음 단계로
    RETRY = "retry"             # 현재 단계 재시도
    LOOP_BACK = "loop_back"     # 지정된 단계로 돌아감
    ESCALATE = "escalate"       # 사람에게 에스컬레이션
    ABORT = "abort"             # 워크플로 중단


@dataclass
class Step:
    """단일 에이전트 실행"""
    id: str
    agent: str
    label: str
    max_turns: int = 10
    max_budget_usd: float = 3.0
    prompt_override: str = ""    # 기본 프롬프트 대신 사용할 프롬프트


@dataclass
class Parallel:
    """여러 에이전트 동시 실행"""
    id: str
    steps: list[Step]
    label: str = ""


@dataclass
class Gate:
    """
    go/no-go 판단

    check: "lint" | "test" | "review" | "custom"
    on_fail: 실패 시 행동
    retry_step_id: LOOP_BACK일 때 돌아갈 step id
    max_retries: 최대 재시도 횟수
    """
    id: str
    check: str              # lint, test, review, budget, custom
    label: str = ""
    on_fail: GateAction = GateAction.RETRY
    retry_step_id: str = ""
    max_retries: int = 2


@dataclass
class Branch:
    """조건 분기"""
    id: str
    condition: str           # 평가할 조건 키워드
    if_true: list = field(default_factory=list)
    if_false: list = field(default_factory=list)


# 워크플로 노드 타입
WorkflowNode = Union[Step, Parallel, Gate, Branch]


@dataclass
class WorkflowResult:
    """워크플로 실행 결과"""
    success: bool
    workflow_name: str
    agent_results: dict[str, ClaudeResult] = field(default_factory=dict)
    gate_results: dict[str, str] = field(default_factory=dict)
    total_cost_usd: float = 0.0
    total_duration: float = 0.0
    aborted: bool = False
    escalated: bool = False

    def to_markdown(self) -> str:
        lines = [
            f"# 워크플로 결과: {self.workflow_name}",
            f"**결과**: {'성공' if self.success else '실패'}",
            f"**비용**: ${self.total_cost_usd:.4f}",
            f"**소요**: {self.total_duration:.1f}초",
        ]
        if self.escalated:
            lines.append("**에스컬레이션**: 사람 검토 필요")

        lines.append("\n## 단계별 결과")
        for step_id, result in self.agent_results.items():
            status = "성공" if result.success else "실패"
            lines.append(f"- **{step_id}** [{result.agent}] {status} ({result.duration_seconds:.1f}s)")

        if self.gate_results:
            lines.append("\n## 게이트")
            for gate_id, verdict in self.gate_results.items():
                lines.append(f"- **{gate_id}**: {verdict}")

        return "\n".join(lines)


class WorkflowEngine:
    """
    워크플로 실행 엔진

    병렬 실행, 게이트, 분기, 핸드오프 프로토콜을 지원.
    """

    def __init__(self, project_root: Path, runner: ClaudeRunner = None):
        self.project_root = project_root
        self.runner = runner or ClaudeRunner(project_root)
        self._outputs: dict[str, str] = {}      # agent_name → output
        self._results: dict[str, ClaudeResult] = {}
        self._gate_results: dict[str, str] = {}
        self._retry_counts: dict[str, int] = {}

    async def execute(
        self,
        workflow_name: str,
        nodes: list[WorkflowNode],
        prompt: str,
    ) -> WorkflowResult:
        """워크플로 실행"""
        start_time = time.time()
        self._outputs = {}
        self._results = {}
        self._gate_results = {}
        self._retry_counts = {}

        logger.info(f"워크플로 시작: {workflow_name} ({len(nodes)}개 노드)")

        i = 0
        while i < len(nodes):
            node = nodes[i]

            if isinstance(node, Step):
                result = await self._execute_step(node, prompt)
                if not result.success:
                    logger.error(f"[{node.id}] 실패 — 워크플로 중단")
                    return self._build_result(workflow_name, False, start_time)
                i += 1

            elif isinstance(node, Parallel):
                results = await self._execute_parallel(node, prompt)
                if any(not r.success for r in results):
                    failed = [r.agent for r in results if not r.success]
                    logger.error(f"[{node.id}] 병렬 실패: {failed}")
                    return self._build_result(workflow_name, False, start_time)
                i += 1

            elif isinstance(node, Gate):
                action = await self._execute_gate(node)
                if action == GateAction.PROCEED:
                    i += 1
                elif action == GateAction.RETRY:
                    # 재시도할 step 찾기
                    retry_target = node.retry_step_id or (nodes[i-1].id if i > 0 else None)
                    if retry_target:
                        retry_idx = next(
                            (j for j, n in enumerate(nodes)
                             if hasattr(n, 'id') and n.id == retry_target),
                            max(0, i - 1)
                        )
                        i = retry_idx
                        logger.info(f"[{node.id}] 재시도 → {retry_target}")
                    else:
                        i += 1
                elif action == GateAction.ESCALATE:
                    return self._build_result(workflow_name, False, start_time, escalated=True)
                elif action == GateAction.ABORT:
                    return self._build_result(workflow_name, False, start_time, aborted=True)
                else:
                    i += 1

            elif isinstance(node, Branch):
                branch_nodes = self._evaluate_branch(node)
                # 분기 노드를 현재 위치에 삽입
                nodes = nodes[:i] + branch_nodes + nodes[i+1:]
                # i를 증가시키지 않음 — 삽입된 첫 노드부터 실행

            else:
                i += 1

        return self._build_result(workflow_name, True, start_time)

    async def _execute_step(self, step: Step, base_prompt: str) -> ClaudeResult:
        """단일 에이전트 실행"""
        # 핸드오프 프로토콜로 프롬프트 구성
        prompt = build_handoff_prompt(
            current_agent=step.agent,
            prompt=step.prompt_override or f"{step.label}\n\n{base_prompt}",
            previous_outputs=self._outputs,
        )

        logger.info(f"[{step.id}] {step.agent}: {step.label}")

        result = await self.runner.run_agent(
            prompt=prompt,
            agent=step.agent,
            max_turns=step.max_turns,
            max_budget_usd=step.max_budget_usd,
        )

        self._results[step.id] = result
        if result.success:
            self._outputs[step.agent] = result.output

        return result

    async def _execute_parallel(self, parallel: Parallel, base_prompt: str) -> list[ClaudeResult]:
        """병렬 에이전트 실행"""
        logger.info(f"[{parallel.id}] 병렬 실행: {[s.agent for s in parallel.steps]}")

        tasks = []
        for step in parallel.steps:
            prompt = build_handoff_prompt(
                current_agent=step.agent,
                prompt=step.prompt_override or f"{step.label}\n\n{base_prompt}",
                previous_outputs=self._outputs,
            )
            tasks.append({
                "prompt": prompt,
                "agent": step.agent,
                "max_turns": step.max_turns,
                "max_budget_usd": step.max_budget_usd,
            })

        results = await self.runner.run_agents_parallel(tasks, max_concurrent=3)

        for step, result in zip(parallel.steps, results):
            self._results[step.id] = result
            if result.success:
                self._outputs[step.agent] = result.output

        return results

    async def _execute_gate(self, gate: Gate) -> GateAction:
        """게이트 체크 실행"""
        gate_key = gate.id
        self._retry_counts.setdefault(gate_key, 0)

        if self._retry_counts[gate_key] >= gate.max_retries:
            logger.warning(f"[{gate.id}] 최대 재시도({gate.max_retries}) 도달 → 에스컬레이션")
            self._gate_results[gate.id] = "ESCALATED"
            return GateAction.ESCALATE

        passed = False

        if gate.check == "lint":
            passed = await self._gate_lint()
        elif gate.check == "test":
            passed = await self._gate_test()
        elif gate.check == "review":
            passed = self._gate_review_approved()
        elif gate.check == "budget":
            passed = self._gate_budget_ok()
        else:
            passed = True  # 알 수 없는 체크는 통과

        if passed:
            self._gate_results[gate.id] = "PASS"
            logger.info(f"[{gate.id}] 게이트 통과")
            return GateAction.PROCEED
        else:
            self._retry_counts[gate_key] += 1
            self._gate_results[gate.id] = f"FAIL (시도 {self._retry_counts[gate_key]}/{gate.max_retries})"
            logger.info(f"[{gate.id}] 게이트 실패 → {gate.on_fail.value}")
            return gate.on_fail

    def _evaluate_branch(self, branch: Branch) -> list:
        """분기 조건 평가"""
        condition = branch.condition.lower()

        # 이전 출력에서 조건 평가
        all_output = " ".join(self._outputs.values()).lower()

        if condition == "has_ui":
            result = any(kw in all_output for kw in ["ui", "화면", "페이지", "컴포넌트"])
        elif condition == "has_security_concern":
            result = any(kw in all_output for kw in ["보안", "인증", "권한", "security"])
        elif condition == "needs_migration":
            result = any(kw in all_output for kw in ["마이그레이션", "migration", "스키마"])
        else:
            result = False

        return branch.if_true if result else branch.if_false

    # ── 게이트 구현 ──

    async def _gate_lint(self) -> bool:
        """린터 통과 여부"""
        import subprocess
        for cmd in [
            "python3 linters/architecture_linter.py .",
            "python3 linters/structure_validator.py .",
        ]:
            proc = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                cwd=str(self.project_root), timeout=30,
            )
            if proc.returncode != 0:
                return False
        return True

    async def _gate_test(self) -> bool:
        """테스트 통과 여부"""
        import subprocess
        proc = subprocess.run(
            "python3 -m pytest -q 2>/dev/null",
            shell=True, capture_output=True, text=True,
            cwd=str(self.project_root), timeout=120,
        )
        return proc.returncode == 0

    def _gate_review_approved(self) -> bool:
        """리뷰어 승인 여부"""
        reviewer_output = self._outputs.get("reviewer", "")
        if not reviewer_output:
            return False
        lower = reviewer_output.lower()
        if any(kw in lower for kw in ["차단", "block", "수정 필요"]):
            return False
        return any(kw in lower for kw in ["승인", "approve", "lgtm", "통과"])

    def _gate_budget_ok(self) -> bool:
        """비용 한도 내인지"""
        total = sum(r.cost_usd for r in self._results.values())
        return total < 20.0

    def _build_result(
        self, name: str, success: bool, start_time: float,
        escalated: bool = False, aborted: bool = False,
    ) -> WorkflowResult:
        return WorkflowResult(
            success=success,
            workflow_name=name,
            agent_results=dict(self._results),
            gate_results=dict(self._gate_results),
            total_cost_usd=sum(r.cost_usd for r in self._results.values()),
            total_duration=time.time() - start_time,
            escalated=escalated,
            aborted=aborted,
        )


# ═══════════════════════════════════════════════════
#  워크플로 정의
# ═══════════════════════════════════════════════════

def workflow_feature(prompt: str) -> tuple[str, list[WorkflowNode]]:
    """
    풀사이클 기능 구현

    Phase 1: 기획 (pm + analyst 병렬) → designer
    Phase 2: 계획 (planner)
    Gate: 계획 게이트 (린트 + 구조 검증)
    Phase 3: 구현 (coder) → 검증 (tester + reviewer 병렬)
    Gate: 리뷰 게이트 (reviewer 승인 필요, 실패 시 coder로 루프백)
    Phase 4: 배포 검토 (ops) + 텔레메트리 검증 (analyst)
    """
    return "feature", [
        # Phase 1: 기획 — pm과 analyst는 독립적이므로 병렬
        Parallel(id="plan-parallel", label="기획", steps=[
            Step(id="pm", agent="pm", label="제품 사양 및 수용 기준 정의", max_turns=10),
            Step(id="analyst-metrics", agent="analyst", label="성공 지표 설계", max_turns=8),
        ]),
        Step(id="designer", agent="designer", label="UI/UX 설계", max_turns=10),

        # Phase 2: 계획
        Step(id="planner", agent="planner", label="실행 계획 수립 (AC 체크리스트 포함)", max_turns=10),

        # Phase 3: 구현
        Step(id="coder", agent="coder", label="코드 구현 (AC 체크리스트 하나씩 확인)", max_turns=20, max_budget_usd=5.0),

        # Gate: 린트 통과?
        Gate(id="lint-gate", check="lint", label="린트 게이트",
             on_fail=GateAction.RETRY, retry_step_id="coder", max_retries=2),

        # 검증 — tester와 reviewer 병렬
        Parallel(id="verify-parallel", label="검증", steps=[
            Step(id="tester", agent="tester", label="테스트 작성 및 실행", max_turns=10),
            Step(id="reviewer", agent="reviewer", label="코드 리뷰 + AC 검증", max_turns=10),
        ]),

        # Gate: 리뷰 승인?
        Gate(id="review-gate", check="review", label="리뷰 게이트",
             on_fail=GateAction.RETRY, retry_step_id="coder", max_retries=2),

        # Phase 4: 배포 준비 — ops와 analyst 텔레메트리 검증 병렬
        Parallel(id="deploy-parallel", label="배포 준비", steps=[
            Step(id="ops", agent="ops", label="배포 검토", max_turns=5),
            Step(id="analyst-verify", agent="analyst",
                 label="텔레메트리 구현 검증",
                 prompt_override="coder가 구현한 코드에서 analyst가 설계한 이벤트/로깅이 실제로 구현되었는지 확인하세요.",
                 max_turns=5),
        ]),
    ]


def workflow_ui_feature(prompt: str) -> tuple[str, list[WorkflowNode]]:
    """UI 중심 기능 — 디자이너가 설계와 검증 모두 수행"""
    return "ui-feature", [
        Parallel(id="plan-parallel", label="기획", steps=[
            Step(id="pm", agent="pm", label="제품 사양 정의", max_turns=8),
            Step(id="analyst-metrics", agent="analyst", label="성공 지표 설계", max_turns=6),
        ]),
        Step(id="designer-design", agent="designer", label="화면 설계 및 인터랙션 정의", max_turns=12),
        Step(id="planner", agent="planner", label="구현 계획", max_turns=8),
        Step(id="coder", agent="coder", label="UI 구현", max_turns=20, max_budget_usd=5.0),
        Gate(id="lint-gate", check="lint", on_fail=GateAction.RETRY, retry_step_id="coder"),
        # 디자이너 UX 리뷰와 코드 리뷰 병렬
        Parallel(id="review-parallel", label="리뷰", steps=[
            Step(id="designer-review", agent="designer", label="UX 리뷰 및 접근성 검증", max_turns=8),
            Step(id="reviewer", agent="reviewer", label="코드 리뷰", max_turns=8),
        ]),
        Gate(id="review-gate", check="review", on_fail=GateAction.RETRY, retry_step_id="coder"),
    ]


def workflow_bugfix(prompt: str) -> tuple[str, list[WorkflowNode]]:
    """버그 수정 — 빠르게, 하지만 검증은 철저히"""
    return "bugfix", [
        Step(id="coder", agent="coder", label="버그 재현 및 수정", max_turns=15, max_budget_usd=3.0),
        Gate(id="lint-gate", check="lint", on_fail=GateAction.RETRY, retry_step_id="coder"),
        Parallel(id="verify-parallel", label="검증", steps=[
            Step(id="tester", agent="tester", label="수정 검증 + 회귀 테스트", max_turns=10),
            Step(id="reviewer", agent="reviewer", label="코드 리뷰", max_turns=8),
        ]),
        Gate(id="review-gate", check="review", on_fail=GateAction.RETRY, retry_step_id="coder"),
    ]


def workflow_small_change(prompt: str) -> tuple[str, list[WorkflowNode]]:
    """
    경량 변경 — 설정, 문구, 스타일 등 작은 수정

    풀사이클을 태우지 않고, coder → 린트 게이트만 통과하면 완료.
    """
    return "small-change", [
        Step(id="coder", agent="coder", label="변경 구현", max_turns=8, max_budget_usd=1.0),
        Gate(id="lint-gate", check="lint", on_fail=GateAction.RETRY, retry_step_id="coder"),
    ]


def workflow_refactor(prompt: str) -> tuple[str, list[WorkflowNode]]:
    """리팩터링"""
    return "refactor", [
        Step(id="quality", agent="quality-scorer", label="현재 품질 평가", max_turns=8),
        Step(id="planner", agent="planner", label="리팩터링 계획", max_turns=10),
        Step(id="coder", agent="coder", label="리팩터링 실행", max_turns=20, max_budget_usd=5.0),
        Gate(id="lint-gate", check="lint", on_fail=GateAction.RETRY, retry_step_id="coder"),
        Parallel(id="verify-parallel", label="검증", steps=[
            Step(id="tester", agent="tester", label="회귀 테스트", max_turns=10),
            Step(id="reviewer", agent="reviewer", label="코드 리뷰", max_turns=8),
        ]),
        Gate(id="review-gate", check="review", on_fail=GateAction.RETRY, retry_step_id="coder"),
        Step(id="quality-after", agent="quality-scorer", label="리팩터링 후 품질 재평가", max_turns=5),
    ]


def workflow_spec(prompt: str) -> tuple[str, list[WorkflowNode]]:
    """제품 기획만 (구현 없이)"""
    return "spec", [
        Step(id="pm", agent="pm", label="제품 사양 작성", max_turns=12),
        Step(id="analyst", agent="analyst", label="성공 지표 설계", max_turns=8),
        Step(id="designer", agent="designer", label="UI/UX 설계", max_turns=10),
    ]


def workflow_incident(prompt: str) -> tuple[str, list[WorkflowNode]]:
    """
    장애 대응 — 완화 → 수정 → 검증 → 포스트모템

    이전: ops → coder → tester → ops (포스트모템 누락)
    이후: ops(분석+완화) → coder(핫픽스) → tester+reviewer 병렬 → ops(배포) → planner(포스트모템)
    """
    return "incident", [
        Step(id="ops-analyze", agent="ops", label="장애 분석 및 완화 판단", max_turns=10),
        Step(id="coder", agent="coder", label="핫픽스 구현", max_turns=15, max_budget_usd=3.0),
        Parallel(id="verify-parallel", label="핫픽스 검증", steps=[
            Step(id="tester", agent="tester", label="핫픽스 검증", max_turns=8),
            Step(id="reviewer", agent="reviewer", label="핫픽스 리뷰", max_turns=5),
        ]),
        Step(id="ops-deploy", agent="ops", label="배포 및 모니터링 포인트 정의", max_turns=5),
        Step(id="postmortem", agent="planner",
             label="포스트모템 작성",
             prompt_override=(
                 "이번 장애에 대한 포스트모템을 작성하세요.\n"
                 "포함 항목: 타임라인, 영향 범위, 근본 원인, 완화 과정, "
                 "재발 방지 액션 아이템.\n"
                 "docs/exec-plans/active/ 에 postmortem-<날짜>.md로 저장하세요."
             ),
             max_turns=8),
    ]


def workflow_analyze(prompt: str) -> tuple[str, list[WorkflowNode]]:
    """출시 후 효과 분석"""
    return "analyze", [
        Step(id="analyst", agent="analyst", label="지표 분석 및 결론", max_turns=10),
        Step(id="pm", agent="pm",
             label="분석 결과 기반 다음 행동 결정",
             prompt_override=(
                 "analyst의 분석 결과를 바탕으로 다음 행동을 결정하세요:\n"
                 "- 유지 (지표 개선 확인)\n"
                 "- 반복 (추가 개선 필요 → 새 제품 사양 작성)\n"
                 "- 롤백 (가드레일 지표 악화)\n"
                 "결정과 근거를 docs/product-specs/에 기록하세요."
             ),
             max_turns=8),
    ]


def workflow_docs(prompt: str) -> tuple[str, list[WorkflowNode]]:
    """문서 관리"""
    return "docs", [
        Step(id="doc-gardener", agent="doc-gardener", label="문서 스캔 및 업데이트", max_turns=10),
        Gate(id="struct-gate", check="lint", label="구조 검증"),
    ]


def workflow_review(prompt: str) -> tuple[str, list[WorkflowNode]]:
    """코드 리뷰만"""
    return "review", [
        Step(id="reviewer", agent="reviewer", label="코드 리뷰", max_turns=10),
        # 보안 관련 내용이 있으면 security-reviewer도 실행
        Branch(id="security-branch", condition="has_security_concern",
               if_true=[
                   Step(id="security", agent="security-reviewer", label="보안 리뷰", max_turns=8),
               ],
               if_false=[]),
    ]


# 워크플로 레지스트리
WORKFLOW_REGISTRY = {
    "feature": workflow_feature,
    "ui-feature": workflow_ui_feature,
    "bugfix": workflow_bugfix,
    "small-change": workflow_small_change,
    "refactor": workflow_refactor,
    "spec": workflow_spec,
    "incident": workflow_incident,
    "analyze": workflow_analyze,
    "docs": workflow_docs,
    "review": workflow_review,
}
