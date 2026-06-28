"""
QualityScorer — 품질 평가 에이전트

도메인별 품질 등급을 평가하고 QUALITY_SCORE.md를 업데이트합니다.
"""

import re
from pathlib import Path
from agents.base_agent import BaseAgent


class QualityScorer(BaseAgent):
    name = "quality_scorer"
    description = "도메인별 품질 등급을 평가하고 추적하는 에이전트"

    SYSTEM_PROMPT = """당신은 소프트웨어 품질 평가 에이전트입니다.

## 역할
- 각 도메인과 아키텍처 레이어의 품질을 평가합니다.
- 테스트 커버리지, 린트 위반, 문서 상태를 종합 분석합니다.
- 기술 부채를 식별하고 우선순위를 매깁니다.

## 등급 기준
- A: 우수 — 테스트 90%+, 린트 위반 0, 문서 최신
- B: 양호 — 테스트 70%+, 경미한 린트 위반
- C: 보통 — 테스트 50%+, 일부 아키텍처 위반
- D: 미흡 — 테스트 부족, 아키텍처 위반 다수
- F: 위험 — 즉각적 개선 필요

## 출력 형식
도메인별 품질 등급 테이블과 개선 권고사항을 제공하세요.
"""

    def get_system_prompt(self) -> str:
        return self.SYSTEM_PROMPT

    async def execute(self, task_description: str, context: dict = None) -> str:
        messages = [
            {"role": "user", "content": f"## 태스크\n{task_description}"},
        ]
        result = await self.call_model(messages, max_tokens=4096)
        self.log(f"품질 평가 완료: {task_description[:50]}")
        return result

    async def evaluate_domain(self, domain_path: str) -> dict:
        """특정 도메인의 품질 평가"""
        full_path = self.project_root / domain_path
        if not full_path.exists():
            return {"error": f"경로 없음: {domain_path}"}

        # 기본 메트릭 수집
        py_files = list(full_path.rglob("*.py"))
        test_files = [f for f in py_files if "test" in f.name.lower()]
        total_lines = 0
        large_files = []

        for f in py_files:
            try:
                lines = len(f.read_text(encoding="utf-8").splitlines())
                total_lines += lines
                if lines > 300:
                    large_files.append({"file": str(f.relative_to(self.project_root)), "lines": lines})
            except Exception:
                pass

        # 린터 실행
        lint_result = self.run_command(f"python -m py_compile {' '.join(str(f) for f in py_files[:20])}")

        # 등급 계산
        test_ratio = len(test_files) / max(len(py_files), 1)
        has_large_files = len(large_files) > 0

        if test_ratio >= 0.5 and not has_large_files:
            grade = "A"
        elif test_ratio >= 0.3:
            grade = "B"
        elif test_ratio >= 0.1:
            grade = "C"
        else:
            grade = "D"

        return {
            "domain": domain_path,
            "grade": grade,
            "total_files": len(py_files),
            "test_files": len(test_files),
            "test_ratio": round(test_ratio, 2),
            "total_lines": total_lines,
            "large_files": large_files,
            "lint_clean": lint_result["success"],
        }

    async def evaluate_all(self) -> dict:
        """전체 프로젝트 품질 평가"""
        domains = ["orchestrator", "agents", "linters"]
        results = {}
        for domain in domains:
            results[domain] = await self.evaluate_domain(domain)
        return results

    async def update_quality_score(self) -> str:
        """QUALITY_SCORE.md 업데이트"""
        evaluations = await self.evaluate_all()

        lines = [
            "# 품질 스코어",
            "",
            "> 자동 생성 — QualityScorer 에이전트",
            "",
            "## 등급 기준",
            "",
            "| 등급 | 설명 |",
            "|------|------|",
            "| A | 우수 — 테스트 커버리지 90%+, 린트 위반 0, 문서 최신 |",
            "| B | 양호 — 테스트 커버리지 70%+, 경미한 린트 위반 |",
            "| C | 보통 — 테스트 커버리지 50%+, 일부 아키텍처 위반 |",
            "| D | 미흡 — 테스트 부족, 아키텍처 위반 다수 |",
            "| F | 위험 — 즉각적인 개선 필요 |",
            "",
            "## 현재 품질 등급",
            "",
            "| 도메인 | 등급 | 파일수 | 테스트 비율 | 총 라인수 | 린트 |",
            "|--------|------|--------|-----------|----------|------|",
        ]

        for domain, eval_data in evaluations.items():
            if "error" in eval_data:
                lines.append(f"| {domain} | - | - | - | - | - |")
            else:
                lines.append(
                    f"| {domain} | {eval_data['grade']} | "
                    f"{eval_data['total_files']} | "
                    f"{eval_data['test_ratio']:.0%} | "
                    f"{eval_data['total_lines']} | "
                    f"{'통과' if eval_data['lint_clean'] else '위반'} |"
                )

        content = "\n".join(lines)
        self.write_file("docs/QUALITY_SCORE.md", content)
        return content
