"""
에이전트 시스템

각 에이전트는 특화된 역할을 수행합니다:
- CodeAgent: 코드 생성 및 수정
- ReviewAgent: 코드 리뷰
- TestAgent: 테스트 생성 및 실행
- DocGardener: 문서 관리 (가비지 컬렉션)
- QualityScorer: 품질 평가
- LinterAgent: 아키텍처 린팅
- PlannerAgent: 실행 계획 수립
"""

from agents.base_agent import BaseAgent
from agents.code_agent import CodeAgent
from agents.review_agent import ReviewAgent
from agents.test_agent import TestAgent
from agents.doc_gardener import DocGardener
from agents.quality_scorer import QualityScorer
from agents.linter_agent import LinterAgent
from agents.planner_agent import PlannerAgent

AGENT_REGISTRY: dict[str, type[BaseAgent]] = {
    "coder": CodeAgent,
    "reviewer": ReviewAgent,
    "tester": TestAgent,
    "doc_gardener": DocGardener,
    "quality_scorer": QualityScorer,
    "linter": LinterAgent,
    "planner": PlannerAgent,
}

__all__ = [
    "BaseAgent",
    "CodeAgent",
    "ReviewAgent",
    "TestAgent",
    "DocGardener",
    "QualityScorer",
    "LinterAgent",
    "PlannerAgent",
    "AGENT_REGISTRY",
]
