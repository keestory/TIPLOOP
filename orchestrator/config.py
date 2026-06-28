"""오케스트레이터 설정"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import json
import os


@dataclass
class AgentConfig:
    """개별 에이전트 설정"""
    name: str
    model: str = "claude-sonnet-4-6"
    max_tokens: int = 8192
    temperature: float = 0.0
    max_retries: int = 3
    timeout_seconds: int = 1800  # 30분
    autonomy_level: str = "medium"  # low, medium, high


@dataclass
class ReviewLoopConfig:
    """리뷰 루프 (Ralph Wiggum Loop) 설정"""
    max_iterations: int = 5
    auto_approve_threshold: float = 0.95  # 신뢰도 임계값
    require_human_review: bool = False


@dataclass
class OrchestratorConfig:
    """오케스트레이터 전체 설정"""
    project_root: Path = field(default_factory=lambda: Path.cwd())
    api_key: Optional[str] = None
    default_model: str = "claude-sonnet-4-6"
    planning_model: str = "claude-opus-4-6"
    max_concurrent_agents: int = 5
    review_loop: ReviewLoopConfig = field(default_factory=ReviewLoopConfig)
    log_dir: Path = field(default_factory=lambda: Path.cwd() / ".harness" / "logs")
    checkpoint_dir: Path = field(default_factory=lambda: Path.cwd() / ".harness" / "checkpoints")

    # 에이전트별 설정
    agents: dict[str, AgentConfig] = field(default_factory=lambda: {
        "planner": AgentConfig(name="planner", model="claude-opus-4-6", autonomy_level="low"),
        "coder": AgentConfig(name="coder", model="claude-sonnet-4-6", autonomy_level="medium"),
        "reviewer": AgentConfig(name="reviewer", model="claude-sonnet-4-6", autonomy_level="high"),
        "tester": AgentConfig(name="tester", model="claude-sonnet-4-6", autonomy_level="high"),
        "doc_gardener": AgentConfig(name="doc_gardener", model="claude-haiku-4-5-20251001", autonomy_level="high"),
        "quality_scorer": AgentConfig(name="quality_scorer", model="claude-haiku-4-5-20251001", autonomy_level="high"),
        "linter": AgentConfig(name="linter", model="claude-haiku-4-5-20251001", autonomy_level="high"),
    })

    def __post_init__(self):
        if self.api_key is None:
            self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_file(cls, path: Path) -> "OrchestratorConfig":
        """설정 파일에서 로드"""
        with open(path) as f:
            data = json.load(f)
        return cls(**data)

    def get_agent_config(self, agent_name: str) -> AgentConfig:
        """에이전트 설정 조회"""
        return self.agents.get(agent_name, AgentConfig(name=agent_name))
