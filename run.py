#!/usr/bin/env python3
"""
Harness Engineering CLI — Claude Code 네이티브

Usage:
    python3 run.py "기능을 구현해줘"                      # 전체 파이프라인
    python3 run.py --agent coder "버그 수정"              # 단일 에이전트
    python3 run.py --review 3 "인증 모듈 리뷰"           # Level 3 리뷰
    python3 run.py --loop "로그인 버그 수정"              # coder→reviewer 반복 루프
    python3 run.py --gc                                    # 가비지 컬렉션
    python3 run.py --lint                                  # 린터 실행
    python3 run.py --quality                               # 품질 평가
    python3 run.py --agents                                # 에이전트 목록
"""

import argparse
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def run_linters():
    """로컬 린터 실행 (Claude Code 호출 없이)"""
    from linters.architecture_linter import run_all as arch_lint
    from linters.naming_linter import run_all as name_lint
    from linters.structure_validator import run_all as struct_lint

    print("=" * 60)
    print("Harness Engineering — 린터")
    print("=" * 60)

    all_violations = []

    for name, linter in [("아키텍처", arch_lint), ("네이밍", name_lint), ("구조", struct_lint)]:
        violations = linter(PROJECT_ROOT)
        all_violations.extend(violations)
        print(f"  [{name}] {len(violations)}건")

    errors = [v for v in all_violations if v.severity == "error"]
    warnings = [v for v in all_violations if v.severity == "warning"]
    print(f"\n  총: {len(errors)}건 오류, {len(warnings)}건 경고")

    if all_violations:
        print()
        for v in all_violations:
            print(v.format())

    return len(errors) == 0


async def run_orchestrator(prompt: str, workflow: str = None, with_loop: bool = False, files: list[str] = None):
    """전체 파이프라인 실행"""
    from orchestrator.main import Orchestrator

    orch = Orchestrator(PROJECT_ROOT)

    print("=" * 60)
    print("Harness Engineering — 오케스트레이터")
    print("=" * 60)
    print(f"프롬프트: {prompt}")
    print(f"모드: {'Ralph Wiggum Loop' if with_loop else '순차 파이프라인'}")
    print()

    result = await orch.run(prompt, workflow=workflow, files=files)
    print(result.to_markdown())


async def run_single_agent(prompt: str, agent: str):
    """단일 에이전트 실행"""
    from orchestrator.main import Orchestrator

    orch = Orchestrator(PROJECT_ROOT)

    print(f"에이전트: {agent}")
    print(f"프롬프트: {prompt}")
    print()

    result = await orch.run_single(prompt, agent, max_turns=15, max_budget_usd=3.0)
    print(f"결과: {'성공' if result.success else '실패'}")
    print(f"소요: {result.duration_seconds:.1f}s | 비용: ${result.cost_usd:.4f}")
    print(f"\n{result.output}")


async def run_review(target: str, level: int = None, files: list[str] = None):
    """리뷰 실행"""
    from orchestrator.review_loop import ReviewLoop

    loop = ReviewLoop(PROJECT_ROOT)

    print("=" * 60)
    print(f"Harness Engineering — Level {level or 'auto'} 리뷰")
    print("=" * 60)

    verdict = await loop.review(target, level, files)
    print(verdict.to_markdown())


async def run_review_loop(task: str, level: int = None, files: list[str] = None):
    """Ralph Wiggum Loop 실행"""
    from orchestrator.review_loop import ReviewLoop

    loop = ReviewLoop(PROJECT_ROOT)

    print("=" * 60)
    print("Harness Engineering — Ralph Wiggum Loop")
    print("=" * 60)
    print(f"태스크: {task}")
    print()

    verdict = await loop.review_loop(task, level, files)
    print(verdict.to_markdown())


async def run_gc():
    """가비지 컬렉션"""
    from orchestrator.main import Orchestrator

    orch = Orchestrator(PROJECT_ROOT)
    print("Harness Engineering — 가비지 컬렉션")
    print()

    results = await orch.run_garbage_collection()
    for r in results:
        print(f"  [{r.agent}] {'성공' if r.success else '실패'} ({r.duration_seconds:.1f}s)")


async def list_agents():
    """에이전트 목록"""
    from orchestrator.claude_runner import ClaudeRunner

    runner = ClaudeRunner(PROJECT_ROOT)
    agents = await runner.list_agents()

    print("Harness Engineering — 에이전트")
    print()
    for a in sorted(agents):
        agent_file = PROJECT_ROOT / ".claude" / "agents" / f"{a}.md"
        # frontmatter에서 description 추출
        desc = ""
        if agent_file.exists():
            content = agent_file.read_text()
            for line in content.split("\n"):
                if line.startswith("description:"):
                    desc = line.split(":", 1)[1].strip().strip('"')
                    break
        print(f"  {a:20s} {desc[:60]}")


async def run_quality():
    """품질 평가 (Claude Code 에이전트)"""
    from orchestrator.main import Orchestrator

    orch = Orchestrator(PROJECT_ROOT)
    result = await orch.run_single(
        "프로젝트 전체 품질을 평가하고 docs/QUALITY_SCORE.md를 업데이트하세요.",
        agent="quality-scorer",
        max_turns=10,
        max_budget_usd=1.0,
    )
    print(f"결과: {'성공' if result.success else '실패'}")
    print(result.output)


def main():
    parser = argparse.ArgumentParser(
        description="Harness Engineering — Claude Code 네이티브 오케스트레이터",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python3 run.py "로그인 버그를 수정해줘"                  # 전체 파이프라인 (자동 워크플로)
  python3 run.py --agent coder "새 API 추가"               # 단일 에이전트
  python3 run.py --review 3 "인증 모듈 변경 리뷰"         # Level 3 리뷰
  python3 run.py --loop "결제 로직 구현"                    # coder→reviewer 반복 루프
  python3 run.py --gc                                       # 가비지 컬렉션
  python3 run.py --lint                                     # 린터 (로컬)
  python3 run.py --quality                                  # 품질 평가 (에이전트)
  python3 run.py --agents                                   # 에이전트 목록
        """,
    )

    parser.add_argument("prompt", nargs="?", help="실행할 프롬프트")
    parser.add_argument("--agent", "-a", help="단일 에이전트 실행")
    parser.add_argument("--review", "-r", type=int, nargs="?", const=0, help="리뷰 실행 (레벨 지정, 0=자동)")
    parser.add_argument("--loop", "-l", action="store_true", help="Ralph Wiggum Loop (coder→reviewer 반복)")
    parser.add_argument("--workflow", "-w", choices=["feature", "ui-feature", "bugfix", "small-change", "refactor", "spec", "incident", "analyze", "docs", "review"], help="워크플로 지정")
    parser.add_argument("--workflows", action="store_true", help="사용 가능한 워크플로 목록")
    parser.add_argument("--gc", action="store_true", help="가비지 컬렉션")
    parser.add_argument("--lint", action="store_true", help="린터 실행 (로컬)")
    parser.add_argument("--quality", "-q", action="store_true", help="품질 평가")
    parser.add_argument("--agents", action="store_true", help="에이전트 목록")
    parser.add_argument("--files", "-f", nargs="*", help="관련 파일 지정")

    args = parser.parse_args()

    if args.workflows:
        from orchestrator.main import Orchestrator
        orch = Orchestrator(PROJECT_ROOT)
        print("Harness Engineering — 워크플로")
        print()
        for name, desc in orch.list_workflows().items():
            print(f"  {name:15s} {desc}")
        return

    if args.lint:
        success = run_linters()
        sys.exit(0 if success else 1)

    elif args.agents:
        asyncio.run(list_agents())

    elif args.gc:
        asyncio.run(run_gc())

    elif args.quality:
        asyncio.run(run_quality())

    elif args.review is not None and args.prompt:
        level = args.review if args.review > 0 else None
        asyncio.run(run_review(args.prompt, level, args.files))

    elif args.loop and args.prompt:
        asyncio.run(run_review_loop(args.prompt, files=args.files))

    elif args.agent and args.prompt:
        asyncio.run(run_single_agent(args.prompt, args.agent))

    elif args.prompt:
        asyncio.run(run_orchestrator(args.prompt, args.workflow, args.loop, args.files))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
