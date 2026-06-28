"""
메인 오케스트레이터 v2 — Claude Code 네이티브

v1 대비 변경점:
  - 순차 리스트 → 워크플로 엔진 (병렬, 게이트, 분기)
  - 텍스트 전달 → 핸드오프 프로토콜 (구조화된 에이전트 간 계약)
  - 경량 경로 추가 (small-change)
  - 장애 대응에 포스트모템 추가
  - 텔레메트리 구현 검증 추가

Usage:
    orch = Orchestrator(Path("."))
    result = await orch.run("결제 기능을 만들어줘")
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Optional

from orchestrator.claude_runner import ClaudeRunner
from orchestrator.workflow_engine import (
    WorkflowEngine, WorkflowResult, WORKFLOW_REGISTRY,
)
from orchestrator.review_loop import ReviewLoop, ReviewVerdict

logger = logging.getLogger("harness.orchestrator")


class Orchestrator:
    """
    Claude Code 네이티브 오케스트레이터 v2
    """

    def __init__(self, project_root: Path, max_budget_usd: float = 20.0):
        self.project_root = project_root
        self.runner = ClaudeRunner(project_root, max_budget_usd=max_budget_usd)
        self.engine = WorkflowEngine(project_root, self.runner)
        self.review_loop = ReviewLoop(project_root, self.runner)

    def detect_workflow(self, prompt: str) -> str:
        """프롬프트에서 워크플로 유형 감지"""
        lower = prompt.lower()

        # 긴급/운영 먼저 (속도가 중요)
        if any(kw in lower for kw in ["장애", "incident", "서버 다운", "긴급", "핫픽스", "hotfix", "롤백"]):
            return "incident"

        # 분석
        if any(kw in lower for kw in ["분석", "지표", "데이터", "효과", "a/b", "퍼널", "리텐션", "전환율"]):
            return "analyze"

        # 버그 수정
        if any(kw in lower for kw in ["버그", "수정", "fix", "bug", "에러", "error", "깨진"]):
            return "bugfix"

        # 문서 (리팩터링보다 먼저 체크 — "문서 정리"를 docs로 분류)
        if any(kw in lower for kw in ["문서", "doc", "readme", "가이드"]):
            return "docs"

        # 리팩터링
        if any(kw in lower for kw in ["리팩터", "refactor", "정리", "리팩토링"]):
            return "refactor"

        # 경량 변경
        if any(kw in lower for kw in ["문구", "텍스트", "오타", "typo", "설정 변경", "config"]):
            return "small-change"

        # 리뷰
        if any(kw in lower for kw in ["리뷰", "review", "검토"]):
            return "review"

        # 기획
        if any(kw in lower for kw in ["기획", "사양", "스펙", "spec", "요구사항", "prd"]):
            return "spec"

        # UI/프론트
        if any(kw in lower for kw in ["ui", "ux", "화면", "디자인", "프론트", "대시보드", "페이지"]):
            return "ui-feature"

        return "feature"

    async def run(
        self,
        prompt: str,
        workflow: str = None,
        review_level: int = None,
        files: list[str] = None,
    ) -> WorkflowResult:
        """
        전체 파이프라인 실행

        Args:
            prompt: 사용자 프롬프트
            workflow: 워크플로 유형 (None이면 자동 감지)
            review_level: 리뷰 레벨 (review 워크플로에서만)
            files: 관련 파일 목록
        """
        wf_name = workflow or self.detect_workflow(prompt)
        wf_factory = WORKFLOW_REGISTRY.get(wf_name)

        if wf_factory is None:
            logger.error(f"알 수 없는 워크플로: {wf_name}")
            wf_factory = WORKFLOW_REGISTRY["feature"]

        name, nodes = wf_factory(prompt)
        logger.info(f"오케스트레이터 시작 — 워크플로: {name}")

        result = await self.engine.execute(name, nodes, prompt)

        logger.info(
            f"오케스트레이터 완료 — {'성공' if result.success else '실패'} "
            f"({result.total_duration:.1f}s, ${result.total_cost_usd:.4f})"
        )
        return result

    async def run_single(self, prompt: str, agent: str, **kwargs):
        """단일 에이전트 직접 실행"""
        return await self.runner.run_agent(prompt=prompt, agent=agent, **kwargs)

    async def run_review(self, target: str, level: int = None, files: list[str] = None) -> ReviewVerdict:
        """리뷰만 실행"""
        return await self.review_loop.review(target, level, files)

    async def run_garbage_collection(self):
        """가비지 컬렉션"""
        return await self.runner.run_agents_parallel([
            {"prompt": "프로젝트 품질을 평가하고 docs/QUALITY_SCORE.md를 업데이트하세요.", "agent": "quality-scorer", "max_turns": 8, "max_budget_usd": 1.0},
            {"prompt": "docs/ 디렉토리를 스캔하여 오래되거나 부정확한 문서를 수정하세요.", "agent": "doc-gardener", "max_turns": 8, "max_budget_usd": 1.0},
        ], max_concurrent=2)

    def list_workflows(self) -> dict[str, str]:
        """사용 가능한 워크플로 목록"""
        descriptions = {
            "feature": "풀사이클 기능 구현 (PM→Analyst→Designer→Planner→Coder→Tester+Reviewer→Ops)",
            "ui-feature": "UI 중심 기능 (PM→Designer→Planner→Coder→Designer리뷰+Reviewer)",
            "bugfix": "버그 수정 (Coder→Tester+Reviewer)",
            "small-change": "경량 변경 (Coder→린트 게이트)",
            "refactor": "리팩터링 (품질평가→Planner→Coder→Tester+Reviewer→재평가)",
            "spec": "제품 기획만 (PM→Analyst→Designer)",
            "incident": "장애 대응 (Ops→Coder→검증→Ops→포스트모템)",
            "analyze": "출시 후 분석 (Analyst→PM 다음 행동 결정)",
            "docs": "문서 관리 (DocGardener→구조 검증)",
            "review": "코드 리뷰 (Reviewer + 보안 분기)",
        }
        return descriptions
