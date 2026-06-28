"""
리뷰 루프 — Claude Code 에이전트 기반

5단계 리뷰를 claude --agent 호출 체인으로 구현합니다.

Level 1: reviewer 에이전트 단일 패스
Level 2: 린터 실행 + reviewer 에이전트
Level 3: reviewer + security-reviewer 병렬 실행
Level 4: worktree 격리 + 린터 + 테스트 + reviewer + security-reviewer
Level 5: Level 4 + quality-scorer + doc-gardener 검증
"""

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from orchestrator.claude_runner import ClaudeRunner, ClaudeResult

logger = logging.getLogger("harness.review")


@dataclass
class ReviewVerdict:
    """리뷰 판정"""
    level: int
    approved: bool
    summary: str
    agent_results: list[ClaudeResult] = field(default_factory=list)
    lint_passed: bool = True
    test_passed: bool = True
    total_cost_usd: float = 0.0
    escalate_to: Optional[int] = None

    def to_markdown(self) -> str:
        lines = [
            f"## 리뷰 판정 (Level {self.level})",
            f"**결과**: {'승인' if self.approved else '수정 필요'}",
            f"**린트**: {'통과' if self.lint_passed else '위반'}",
            f"**테스트**: {'통과' if self.test_passed else '실패'}",
            f"**비용**: ${self.total_cost_usd:.4f}",
            f"**요약**: {self.summary}",
        ]
        for r in self.agent_results:
            status = "성공" if r.success else "실패"
            lines.append(f"\n### [{r.agent}] {status} ({r.duration_seconds:.1f}s)")
            lines.append(r.output[:1000] if r.output else "(출력 없음)")
        return "\n".join(lines)


def determine_review_level(
    files_changed: list[str] = None,
    lines_changed: int = 0,
    domains_affected: int = 1,
) -> int:
    """변경 내용에 따라 리뷰 레벨 자동 결정"""
    files = files_changed or []

    # Level 5: 인프라/보안
    infra_patterns = ["deploy", "docker", "ci", "security", "auth", "permission"]
    if any(any(p in f.lower() for p in infra_patterns) for f in files):
        return 5

    # Level 4: UI/API 변경
    ui_api_patterns = ["ui/", "api/", "route", "endpoint", "app.py", "server"]
    if any(any(p in f.lower() for p in ui_api_patterns) for f in files):
        return 4

    # Level 3: 다중 도메인 또는 대규모
    if domains_affected >= 2 or lines_changed > 500:
        return 3

    # Level 2: 코드 변경
    if any(f.endswith((".py", ".ts", ".js")) for f in files):
        return 2

    # Level 1: 문서/설정
    return 1


class ReviewLoop:
    """
    다중 레벨 리뷰 루프

    각 레벨은 이전 레벨을 포함합니다:
    Level 1 ⊂ Level 2 ⊂ Level 3 ⊂ Level 4 ⊂ Level 5
    """

    def __init__(self, project_root: Path, runner: ClaudeRunner = None):
        self.project_root = project_root
        self.runner = runner or ClaudeRunner(project_root)

    async def review(
        self,
        target: str,
        level: int = None,
        files_changed: list[str] = None,
        max_iterations: int = 3,
    ) -> ReviewVerdict:
        """
        리뷰 실행

        Args:
            target: 리뷰 대상 설명 또는 diff
            level: 리뷰 레벨 (None이면 자동 결정)
            files_changed: 변경 파일 목록
            max_iterations: 최대 반복 (coder→reviewer 루프)
        """
        if level is None:
            level = determine_review_level(files_changed)

        logger.info(f"리뷰 시작 — Level {level}")

        dispatch = {
            1: self._level_1,
            2: self._level_2,
            3: self._level_3,
            4: self._level_4,
            5: self._level_5,
        }

        handler = dispatch.get(level, self._level_2)
        return await handler(target, files_changed)

    # ═══════════════════════════════════════════
    #  Level 1: reviewer 단일 패스
    # ═══════════════════════════════════════════

    async def _level_1(self, target: str, files: list[str] = None) -> ReviewVerdict:
        """reviewer 에이전트가 코드를 읽고 피드백"""
        files_str = ", ".join(files) if files else "전체 프로젝트"

        result = await self.runner.run_agent(
            prompt=f"다음 코드/변경사항을 리뷰하세요:\n\n{target}\n\n관련 파일: {files_str}",
            agent="reviewer",
            max_turns=5,
            max_budget_usd=1.0,
        )

        approved = self._check_approval(result.output)
        return ReviewVerdict(
            level=1,
            approved=approved,
            summary=f"Level 1 — reviewer {'승인' if approved else '수정 필요'}",
            agent_results=[result],
            total_cost_usd=result.cost_usd,
        )

    # ═══════════════════════════════════════════
    #  Level 2: 린터 + reviewer
    # ═══════════════════════════════════════════

    async def _level_2(self, target: str, files: list[str] = None) -> ReviewVerdict:
        """린터 실행 결과를 reviewer에 전달"""
        results = []

        # Step 1: 린터 실행
        lint_passed, lint_output = await self._run_linters()

        # Step 2: 린트 결과를 포함하여 reviewer 실행
        lint_context = f"린트 결과: {'통과' if lint_passed else '위반 있음'}\n{lint_output}"
        files_str = ", ".join(files) if files else "전체 프로젝트"

        result = await self.runner.run_agent(
            prompt=(
                f"다음 코드를 리뷰하세요:\n\n{target}\n\n"
                f"관련 파일: {files_str}\n\n"
                f"## 정적 검증 결과\n{lint_context}"
            ),
            agent="reviewer",
            max_turns=8,
            max_budget_usd=1.5,
        )
        results.append(result)

        approved = lint_passed and self._check_approval(result.output)
        return ReviewVerdict(
            level=2,
            approved=approved,
            summary=f"Level 2 — 린트:{'통과' if lint_passed else '위반'}, reviewer:{'승인' if self._check_approval(result.output) else '수정 필요'}",
            agent_results=results,
            lint_passed=lint_passed,
            total_cost_usd=sum(r.cost_usd for r in results),
            escalate_to=3 if not approved else None,
        )

    # ═══════════════════════════════════════════
    #  Level 3: reviewer + security-reviewer 병렬
    # ═══════════════════════════════════════════

    async def _level_3(self, target: str, files: list[str] = None) -> ReviewVerdict:
        """reviewer + security-reviewer 병렬 실행 후 합의"""

        # Step 1: 린터
        lint_passed, lint_output = await self._run_linters()
        files_str = ", ".join(files) if files else "전체 프로젝트"
        review_prompt = (
            f"다음 코드를 리뷰하세요:\n\n{target}\n\n"
            f"관련 파일: {files_str}\n\n"
            f"## 정적 검증 결과\n{lint_output}"
        )

        # Step 2: reviewer + security-reviewer 병렬 실행
        results = await self.runner.run_agents_parallel([
            {
                "prompt": review_prompt,
                "agent": "reviewer",
                "max_turns": 8,
                "max_budget_usd": 1.5,
            },
            {
                "prompt": f"다음 코드를 보안 관점에서 리뷰하세요:\n\n{target}\n\n관련 파일: {files_str}",
                "agent": "security-reviewer",
                "max_turns": 5,
                "max_budget_usd": 2.0,
            },
        ], max_concurrent=2)

        # Step 3: 합의 — 둘 다 승인해야 통과
        reviewer_approved = self._check_approval(results[0].output) if results[0].success else False
        security_approved = self._check_approval(results[1].output) if results[1].success else False
        approved = lint_passed and reviewer_approved and security_approved

        return ReviewVerdict(
            level=3,
            approved=approved,
            summary=(
                f"Level 3 — 린트:{'O' if lint_passed else 'X'} "
                f"reviewer:{'O' if reviewer_approved else 'X'} "
                f"security:{'O' if security_approved else 'X'}"
            ),
            agent_results=results,
            lint_passed=lint_passed,
            total_cost_usd=sum(r.cost_usd for r in results),
            escalate_to=4 if not approved else None,
        )

    # ═══════════════════════════════════════════
    #  Level 4: worktree 격리 + 테스트 + 리뷰
    # ═══════════════════════════════════════════

    async def _level_4(self, target: str, files: list[str] = None) -> ReviewVerdict:
        """격리 환경에서 앱 구동, 테스트 실행 후 리뷰"""

        # Step 1: tester 에이전트로 테스트 실행
        test_result = await self.runner.run_agent(
            prompt=(
                f"다음 변경사항에 대해 테스트를 실행하고 검증하세요:\n\n{target}\n\n"
                "1. 기존 테스트 실행: python3 -m pytest -v\n"
                "2. 실패 시 원인 분석\n"
                "3. 커버리지 보고"
            ),
            agent="tester",
            max_turns=10,
            max_budget_usd=1.5,
        )

        test_passed = test_result.success and "fail" not in test_result.output.lower()

        # Step 2: Level 3 리뷰 실행
        level3 = await self._level_3(target, files)

        # 결과 병합
        all_results = [test_result] + level3.agent_results
        approved = test_passed and level3.approved

        return ReviewVerdict(
            level=4,
            approved=approved,
            summary=(
                f"Level 4 — 테스트:{'O' if test_passed else 'X'} "
                f"+ {level3.summary}"
            ),
            agent_results=all_results,
            lint_passed=level3.lint_passed,
            test_passed=test_passed,
            total_cost_usd=sum(r.cost_usd for r in all_results),
            escalate_to=5 if not approved else None,
        )

    # ═══════════════════════════════════════════
    #  Level 5: 전체 검증 + 품질 + 문서
    # ═══════════════════════════════════════════

    async def _level_5(self, target: str, files: list[str] = None) -> ReviewVerdict:
        """Level 4 + quality-scorer + doc-gardener"""

        # Step 1: Level 4 실행
        level4 = await self._level_4(target, files)

        # Step 2: quality-scorer + doc-gardener 병렬
        extra_results = await self.runner.run_agents_parallel([
            {
                "prompt": "프로젝트 전체 품질을 평가하고 docs/QUALITY_SCORE.md를 업데이트하세요.",
                "agent": "quality-scorer",
                "max_turns": 8,
                "max_budget_usd": 1.0,
            },
            {
                "prompt": "docs/ 디렉토리를 스캔하여 코드 변경에 맞지 않는 문서를 찾고 업데이트하세요.",
                "agent": "doc-gardener",
                "max_turns": 8,
                "max_budget_usd": 1.0,
            },
        ], max_concurrent=2)

        all_results = level4.agent_results + extra_results
        approved = level4.approved  # Level 4 승인이 핵심, 품질/문서는 보조

        return ReviewVerdict(
            level=5,
            approved=approved,
            summary=(
                f"Level 5 — {level4.summary} + "
                f"quality:{'O' if extra_results[0].success else 'X'} "
                f"docs:{'O' if extra_results[1].success else 'X'}"
            ),
            agent_results=all_results,
            lint_passed=level4.lint_passed,
            test_passed=level4.test_passed,
            total_cost_usd=sum(r.cost_usd for r in all_results),
        )

    # ═══════════════════════════════════════════
    #  Ralph Wiggum Loop (coder → reviewer 반복)
    # ═══════════════════════════════════════════

    async def review_loop(
        self,
        task: str,
        level: int = None,
        files: list[str] = None,
        max_iterations: int = 3,
    ) -> ReviewVerdict:
        """
        coder → reviewer 반복 루프

        1. coder가 작업 수행
        2. 레벨별 리뷰 실행
        3. 미승인 → 피드백을 coder에 전달 → 재작업
        4. 승인 또는 최대 반복 도달까지
        """
        if level is None:
            level = determine_review_level(files)

        accumulated_feedback = ""
        all_results: list[ClaudeResult] = []

        for iteration in range(1, max_iterations + 1):
            logger.info(f"=== Ralph Wiggum Loop: 반복 {iteration}/{max_iterations} (Level {level}) ===")

            # Step 1: coder 에이전트 실행
            coder_prompt = f"{task}"
            if accumulated_feedback:
                coder_prompt += f"\n\n## 이전 리뷰 피드백 (반드시 반영하세요)\n{accumulated_feedback}"

            coder_result = await self.runner.run_agent(
                prompt=coder_prompt,
                agent="coder",
                max_turns=15,
                max_budget_usd=3.0,
            )
            all_results.append(coder_result)

            if not coder_result.success:
                logger.error(f"coder 실패: {coder_result.output[:200]}")
                return ReviewVerdict(
                    level=level,
                    approved=False,
                    summary=f"coder 실패 (반복 {iteration})",
                    agent_results=all_results,
                    total_cost_usd=sum(r.cost_usd for r in all_results),
                )

            # Step 2: 레벨별 리뷰
            verdict = await self.review(
                target=f"coder 에이전트의 작업 결과:\n\n{coder_result.output[:3000]}",
                level=level,
                files_changed=files,
            )
            all_results.extend(verdict.agent_results)

            if verdict.approved:
                logger.info(f"승인 — 반복 {iteration}, Level {level}")
                return ReviewVerdict(
                    level=level,
                    approved=True,
                    summary=f"반복 {iteration}에서 Level {level} 승인",
                    agent_results=all_results,
                    lint_passed=verdict.lint_passed,
                    test_passed=verdict.test_passed,
                    total_cost_usd=sum(r.cost_usd for r in all_results),
                )

            # Step 3: 피드백 축적
            feedback_parts = [r.output[:500] for r in verdict.agent_results if r.output]
            accumulated_feedback = "\n\n---\n\n".join(feedback_parts)
            logger.info(f"수정 필요 — 반복 {iteration}, 피드백 {len(feedback_parts)}건")

            # 에스컬레이션 판단
            if verdict.escalate_to and verdict.escalate_to > level:
                level = verdict.escalate_to
                logger.info(f"에스컬레이션 → Level {level}")

        # 최대 반복 도달
        logger.warning(f"최대 반복({max_iterations}) 도달 — 사람 에스컬레이션")
        return ReviewVerdict(
            level=level,
            approved=False,
            summary=f"최대 반복 도달 — Level {level}에서 {max_iterations}회 시도",
            agent_results=all_results,
            total_cost_usd=sum(r.cost_usd for r in all_results),
        )

    # ═══════════════════════════════════════════
    #  유틸리티
    # ═══════════════════════════════════════════

    async def _run_linters(self) -> tuple[bool, str]:
        """모든 린터 실행 (로컬, Claude Code 호출 없이)"""
        import subprocess
        results = []
        all_passed = True

        linters = [
            ("아키텍처", "python3 linters/architecture_linter.py ."),
            ("네이밍", "python3 linters/naming_linter.py ."),
            ("구조", "python3 linters/structure_validator.py ."),
        ]

        for name, cmd in linters:
            proc = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                cwd=str(self.project_root), timeout=30,
            )
            passed = proc.returncode == 0
            if not passed:
                all_passed = False
            results.append(f"[{name}] {'통과' if passed else '위반'}: {proc.stdout[:300]}")

        return all_passed, "\n".join(results)

    def _check_approval(self, output: str) -> bool:
        """리뷰 출력에서 승인 여부 판단"""
        if not output:
            return False
        lower = output.lower()
        # 차단 키워드가 있으면 미승인
        if any(kw in lower for kw in ["차단", "block", "critical", "위험", "수정 필요"]):
            return False
        # 승인 키워드가 있으면 승인
        return any(kw in lower for kw in ["승인", "approve", "lgtm", "통과", "안전"])
