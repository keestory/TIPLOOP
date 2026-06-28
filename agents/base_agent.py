"""
베이스 에이전트

모든 에이전트의 공통 인터페이스와 기능을 정의합니다.
"""

import json
import logging
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


logger = logging.getLogger("harness.agent")


@dataclass
class AgentMessage:
    """에이전트 간 메시지"""
    role: str  # system, user, assistant
    content: str
    metadata: dict = field(default_factory=dict)


class BaseAgent(ABC):
    """
    베이스 에이전트 클래스

    모든 에이전트는 이 클래스를 상속받아 구현합니다.
    에이전트는 다음 도구에 접근할 수 있습니다:
    - 파일 읽기/쓰기
    - 셸 명령 실행
    - 프로젝트 문서 탐색
    """

    name: str = "base"
    description: str = "베이스 에이전트"

    def __init__(self, project_root: Path, client=None):
        self.project_root = project_root
        self.client = client
        self.conversation: list[AgentMessage] = []
        self._logger = logging.getLogger(f"harness.agent.{self.name}")

    @abstractmethod
    def get_system_prompt(self) -> str:
        """에이전트별 시스템 프롬프트"""
        ...

    @abstractmethod
    async def execute(self, task_description: str, context: dict = None) -> str:
        """태스크 실행"""
        ...

    # ── 도구: 파일 시스템 ──

    def read_file(self, path: str) -> str:
        """파일 읽기"""
        full_path = self.project_root / path
        if not full_path.exists():
            return f"[ERROR] 파일 없음: {path}"
        try:
            return full_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return f"[ERROR] 텍스트 파일이 아님: {path}"

    def write_file(self, path: str, content: str) -> str:
        """파일 쓰기"""
        full_path = self.project_root / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        return f"[OK] 파일 작성: {path}"

    def list_files(self, path: str = ".", pattern: str = "**/*") -> list[str]:
        """파일 목록"""
        full_path = self.project_root / path
        if not full_path.exists():
            return []
        return [
            str(p.relative_to(self.project_root))
            for p in full_path.glob(pattern)
            if p.is_file()
        ]

    def search_files(self, pattern: str, path: str = ".") -> list[dict]:
        """파일 내용 검색 (grep)"""
        full_path = self.project_root / path
        results = []
        try:
            proc = subprocess.run(
                ["grep", "-rn", "--include=*.py", "--include=*.md", "--include=*.ts", pattern, str(full_path)],
                capture_output=True, text=True, timeout=30,
            )
            for line in proc.stdout.strip().split("\n")[:50]:
                if ":" in line:
                    parts = line.split(":", 2)
                    if len(parts) >= 3:
                        results.append({
                            "file": parts[0],
                            "line": parts[1],
                            "content": parts[2].strip(),
                        })
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return results

    # ── 도구: 셸 명령 ──

    def run_command(self, command: str, timeout: int = 120) -> dict:
        """셸 명령 실행 (안전한 명령만)"""
        # 위험한 명령 차단
        dangerous = ["rm -rf", "git push --force", "drop table", "shutdown"]
        if any(d in command.lower() for d in dangerous):
            return {
                "success": False,
                "stdout": "",
                "stderr": f"[BLOCKED] 위험한 명령: {command}",
                "returncode": -1,
            }

        try:
            proc = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=str(self.project_root),
            )
            return {
                "success": proc.returncode == 0,
                "stdout": proc.stdout[:5000],
                "stderr": proc.stderr[:2000],
                "returncode": proc.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"[TIMEOUT] {timeout}초 초과",
                "returncode": -1,
            }

    # ── 도구: 프로젝트 탐색 ──

    def read_agents_md(self) -> str:
        """AGENTS.md 읽기 (맵)"""
        return self.read_file("AGENTS.md")

    def read_doc(self, doc_name: str) -> str:
        """docs/ 문서 읽기"""
        return self.read_file(f"docs/{doc_name}")

    def get_architecture(self) -> str:
        """ARCHITECTURE.md 읽기"""
        return self.read_file("ARCHITECTURE.md")

    # ── AI 호출 ──

    async def call_model(self, messages: list[dict], model: str = None, max_tokens: int = 4096) -> str:
        """모델 API 호출"""
        if self.client is None:
            return f"[DRY RUN] {self.name} 에이전트 응답 시뮬레이션"

        response = await self.client.messages.create(
            model=model or "claude-sonnet-4-6",
            max_tokens=max_tokens,
            messages=messages,
        )
        return response.content[0].text

    # ── 유틸리티 ──

    def log(self, msg: str, level: str = "info"):
        """구조화된 로깅"""
        getattr(self._logger, level)(json.dumps({
            "agent": self.name,
            "message": msg,
        }, ensure_ascii=False))
