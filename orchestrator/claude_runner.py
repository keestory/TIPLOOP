"""
Claude Code CLI Runner

claude -p --agent <name> 명령을 subprocess로 실행하여
에이전트를 Claude Code 네이티브로 구동합니다.

핵심 실행 패턴:
  claude -p --agent coder --output-format json "프롬프트"
  claude -p --agent reviewer --output-format json "코드를 리뷰하세요"
  claude -w feature-branch --agent coder "격리 환경에서 구현"
"""

import asyncio
import json
import logging
import shlex
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger("harness.claude_runner")


@dataclass
class ClaudeResult:
    """Claude Code 실행 결과"""
    agent: str
    success: bool
    output: str = ""
    cost_usd: float = 0.0
    duration_seconds: float = 0.0
    session_id: str = ""
    is_error: bool = False
    num_turns: int = 0
    raw_json: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "agent": self.agent,
            "success": self.success,
            "output": self.output[:500],
            "cost_usd": self.cost_usd,
            "duration_seconds": self.duration_seconds,
            "session_id": self.session_id,
            "num_turns": self.num_turns,
        }


class ClaudeRunner:
    """
    Claude Code CLI Wrapper

    에이전트를 claude -p 모드로 실행하고 결과를 파싱합니다.
    """

    def __init__(self, project_root: Path, max_budget_usd: float = 5.0):
        self.project_root = project_root
        self.max_budget_usd = max_budget_usd

    def _build_command(
        self,
        prompt: str,
        agent: str = None,
        output_format: str = "json",
        model: str = None,
        max_turns: int = None,
        worktree: str = None,
        allowed_tools: list[str] = None,
        disallowed_tools: list[str] = None,
        append_system_prompt: str = None,
        permission_mode: str = None,
        max_budget_usd: float = None,
    ) -> list[str]:
        """claude CLI 명령 구성"""
        cmd = ["claude", "-p", "--output-format", output_format]

        if agent:
            cmd.extend(["--agent", agent])

        if model:
            cmd.extend(["--model", model])

        if max_turns:
            cmd.extend(["--max-turns", str(max_turns)])

        if worktree:
            cmd.extend(["--worktree", worktree])

        if allowed_tools:
            cmd.extend(["--allowed-tools", ",".join(allowed_tools)])

        if disallowed_tools:
            cmd.extend(["--disallowed-tools", ",".join(disallowed_tools)])

        if append_system_prompt:
            cmd.extend(["--append-system-prompt", append_system_prompt])

        if permission_mode:
            cmd.extend(["--permission-mode", permission_mode])

        budget = max_budget_usd or self.max_budget_usd
        cmd.extend(["--max-budget-usd", str(budget)])

        cmd.append(prompt)

        return cmd

    async def run_agent(
        self,
        prompt: str,
        agent: str,
        model: str = None,
        max_turns: int = None,
        worktree: str = None,
        append_system_prompt: str = None,
        permission_mode: str = None,
        max_budget_usd: float = None,
        timeout: int = 600,
    ) -> ClaudeResult:
        """
        Claude Code 에이전트 실행

        Args:
            prompt: 에이전트에 전달할 프롬프트
            agent: 에이전트 이름 (.claude/agents/<name>.md)
            model: 모델 오버라이드
            max_turns: 최대 턴 수
            worktree: git worktree 이름 (격리 실행)
            append_system_prompt: 추가 시스템 프롬프트
            permission_mode: 권한 모드
            max_budget_usd: 최대 예산
            timeout: 타임아웃 (초)
        """
        cmd = self._build_command(
            prompt=prompt,
            agent=agent,
            model=model,
            max_turns=max_turns,
            worktree=worktree,
            append_system_prompt=append_system_prompt,
            permission_mode=permission_mode,
            max_budget_usd=max_budget_usd,
        )

        logger.info(f"[{agent}] 실행: claude -p --agent {agent} ...")
        start_time = time.time()

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.project_root),
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )

            duration = time.time() - start_time
            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            # JSON 출력 파싱
            result = self._parse_output(stdout_str, agent, duration)

            if process.returncode != 0:
                result.success = False
                result.is_error = True
                if not result.output:
                    result.output = stderr_str or f"Exit code: {process.returncode}"
                logger.error(f"[{agent}] 실패 (exit {process.returncode}): {stderr_str[:200]}")
            else:
                logger.info(f"[{agent}] 완료 ({duration:.1f}s, ${result.cost_usd:.4f})")

            return result

        except asyncio.TimeoutError:
            duration = time.time() - start_time
            logger.error(f"[{agent}] 타임아웃 ({timeout}s)")
            return ClaudeResult(
                agent=agent,
                success=False,
                output=f"타임아웃: {timeout}초 초과",
                duration_seconds=duration,
                is_error=True,
            )

        except FileNotFoundError:
            return ClaudeResult(
                agent=agent,
                success=False,
                output="claude 명령을 찾을 수 없습니다. Claude Code가 설치되어 있는지 확인하세요.",
                is_error=True,
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"[{agent}] 예외: {e}")
            return ClaudeResult(
                agent=agent,
                success=False,
                output=str(e),
                duration_seconds=duration,
                is_error=True,
            )

    async def run_agents_parallel(
        self,
        tasks: list[dict],
        max_concurrent: int = 3,
    ) -> list[ClaudeResult]:
        """
        여러 에이전트를 병렬 실행

        Args:
            tasks: [{"prompt": str, "agent": str, ...}, ...]
            max_concurrent: 최대 동시 실행 수
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _run_with_limit(task: dict) -> ClaudeResult:
            async with semaphore:
                return await self.run_agent(**task)

        results = await asyncio.gather(
            *[_run_with_limit(t) for t in tasks],
            return_exceptions=True,
        )

        final = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                final.append(ClaudeResult(
                    agent=tasks[i].get("agent", "unknown"),
                    success=False,
                    output=str(r),
                    is_error=True,
                ))
            else:
                final.append(r)

        return final

    def run_agent_sync(self, prompt: str, agent: str, **kwargs) -> ClaudeResult:
        """동기 실행 (스크립트용)"""
        return asyncio.run(self.run_agent(prompt, agent, **kwargs))

    def _parse_output(self, stdout: str, agent: str, duration: float) -> ClaudeResult:
        """Claude Code JSON 출력 파싱"""
        result = ClaudeResult(
            agent=agent,
            success=True,
            duration_seconds=duration,
        )

        if not stdout.strip():
            result.output = "(빈 출력)"
            return result

        try:
            data = json.loads(stdout)
            result.raw_json = data

            # --output-format json 결과 구조
            # {"type": "result", "subtype": "success", "cost_usd": 0.01, "duration_ms": 1234,
            #  "duration_api_ms": 1000, "is_error": false, "num_turns": 3, "session_id": "...",
            #  "result": "에이전트 출력 텍스트"}
            if isinstance(data, dict):
                result.output = data.get("result", str(data))
                result.cost_usd = data.get("cost_usd", 0.0)
                result.session_id = data.get("session_id", "")
                result.is_error = data.get("is_error", False)
                result.num_turns = data.get("num_turns", 0)
                result.success = not result.is_error
            else:
                result.output = str(data)

        except json.JSONDecodeError:
            # JSON 파싱 실패 → 텍스트로 처리
            result.output = stdout
            result.raw_json = None

        return result

    async def check_available(self) -> bool:
        """claude CLI 사용 가능 여부 확인"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "claude", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            return proc.returncode == 0
        except FileNotFoundError:
            return False

    async def list_agents(self) -> list[str]:
        """설정된 에이전트 목록"""
        agents_dir = self.project_root / ".claude" / "agents"
        if not agents_dir.exists():
            return []
        return [f.stem for f in agents_dir.glob("*.md")]
