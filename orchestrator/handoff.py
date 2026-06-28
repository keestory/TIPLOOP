"""
에이전트 간 핸드오프 프로토콜

문제: 이전 에이전트의 출력을 2000자 텍스트로 잘라서 다음 에이전트에 넘기면
      구조가 사라지고, 핵심 정보가 유실되고, 에이전트가 맥락을 잃는다.

해결: 각 에이전트가 구조화된 핸드오프 문서를 생성하고,
      다음 에이전트는 자기에게 필요한 섹션만 읽는다.
"""

from dataclasses import dataclass, field
from typing import Optional


# ── 핸드오프 아티팩트 정의 ──
# 각 에이전트가 생산하는 것과 소비하는 것을 명시

AGENT_CONTRACTS = {
    "pm": {
        "produces": [
            "docs/product-specs/<feature>.md",  # 제품 사양
        ],
        "output_sections": {
            "summary": "기능 한 줄 요약",
            "user_stories": "사용자 스토리 목록",
            "acceptance_criteria": "Given-When-Then 형식의 수용 기준",
            "edge_cases": "엣지 케이스와 기대 동작",
            "out_of_scope": "이번에 하지 않는 것",
            "nonfunctional": "성능/보안/접근성 요구사항",
        },
        "consumes": [],  # 첫 번째 에이전트
    },

    "analyst": {
        "produces": [
            "지표 설계 (제품 사양에 추가)",
        ],
        "output_sections": {
            "primary_metric": "핵심 지표 — 이름, 정의, 목표값",
            "guardrail_metrics": "가드레일 지표 — 이것이 X% 이상 하락하면 롤백",
            "events_required": "구현에 필요한 이벤트/로깅 목록 (coder가 반드시 구현)",
            "measurement_plan": "판단 시점, 분석 방법",
        },
        "consumes": ["pm.acceptance_criteria", "pm.summary"],
    },

    "designer": {
        "produces": [
            "화면 설계 문서",
        ],
        "output_sections": {
            "user_flow": "사용자 플로우 (단계별)",
            "screen_structure": "화면별 핵심 요소와 계층",
            "states": "상태별 화면 (기본/로딩/빈/에러)",
            "interactions": "인터랙션 정의",
            "accessibility": "접근성 요구사항",
        },
        "consumes": ["pm.user_stories", "pm.acceptance_criteria", "pm.nonfunctional"],
    },

    "planner": {
        "produces": [
            "docs/exec-plans/active/<plan>.md",  # 실행 계획
        ],
        "output_sections": {
            "tasks": "구현 태스크 목록 (순서, 의존성, 담당 에이전트)",
            "ac_checklist": "수용 기준 체크리스트 (coder가 하나씩 확인)",
            "events_checklist": "이벤트 구현 체크리스트 (analyst가 정의한 것)",
            "risks": "리스크와 대응 방안",
            "decisions": "아키텍처 결정과 이유",
        },
        "consumes": [
            "pm.acceptance_criteria",
            "pm.edge_cases",
            "analyst.events_required",
            "designer.user_flow",
            "designer.screen_structure",
        ],
    },

    "coder": {
        "produces": [
            "코드 변경",
            "테스트 코드",
        ],
        "output_sections": {
            "files_changed": "변경된 파일 목록과 이유",
            "ac_status": "수용 기준별 구현 상태 (DONE/PARTIAL/SKIPPED)",
            "events_status": "이벤트 구현 상태 (DONE/TODO)",
            "test_coverage": "작성한 테스트 요약",
            "notes": "리뷰어가 알아야 할 판단/트레이드오프",
        },
        "consumes": [
            "planner.tasks",
            "planner.ac_checklist",
            "planner.events_checklist",
            "designer.screen_structure",
            "designer.states",
        ],
    },

    "tester": {
        "produces": [
            "테스트 코드",
            "테스트 실행 결과",
        ],
        "output_sections": {
            "test_results": "통과/실패 수",
            "coverage": "커버리지 %",
            "ac_verification": "수용 기준별 테스트 존재 여부",
            "failures": "실패 테스트 목록과 원인",
        },
        "consumes": [
            "coder.files_changed",
            "coder.ac_status",
            "planner.ac_checklist",
        ],
    },

    "reviewer": {
        "produces": [
            "리뷰 판정",
        ],
        "output_sections": {
            "verdict": "승인/수정 필요/차단",
            "blockers": "차단 이슈 (반드시 수정)",
            "warnings": "경고 (권고)",
            "ac_verification": "수용 기준별 PASS/FAIL (TC)",
            "lint_results": "린터 결과",
        },
        "consumes": [
            "coder.files_changed",
            "coder.ac_status",
            "coder.notes",
            "tester.test_results",
            "tester.ac_verification",
            "planner.ac_checklist",
        ],
    },

    "security-reviewer": {
        "produces": ["보안 리뷰 판정"],
        "output_sections": {
            "verdict": "안전/주의/위험",
            "vulnerabilities": "발견된 취약점",
            "recommendations": "보안 권고",
        },
        "consumes": ["coder.files_changed"],
    },

    "ops": {
        "produces": ["배포 검토 판정"],
        "output_sections": {
            "deploy_verdict": "배포 가능/보류",
            "impact_scope": "영향 범위",
            "rollback_plan": "롤백 방법",
            "monitoring_points": "배포 후 모니터링 포인트",
        },
        "consumes": [
            "coder.files_changed",
            "tester.test_results",
            "reviewer.verdict",
        ],
    },

    "analyst_verify": {
        "produces": ["텔레메트리 검증 결과"],
        "output_sections": {
            "events_verified": "이벤트 구현 확인 (PASS/FAIL)",
            "gaps": "누락된 이벤트",
        },
        "consumes": [
            "analyst.events_required",
            "coder.events_status",
            "coder.files_changed",
        ],
    },
}


def build_handoff_prompt(
    current_agent: str,
    prompt: str,
    previous_outputs: dict[str, str],
) -> str:
    """
    에이전트에 전달할 프롬프트를 구성.

    이전 에이전트의 전체 출력을 붙이는 대신,
    현재 에이전트가 필요로 하는 섹션만 추출하여 전달.
    """
    contract = AGENT_CONTRACTS.get(current_agent, {})
    consumes = contract.get("consumes", [])
    produces = contract.get("output_sections", {})

    parts = [f"## 태스크\n{prompt}"]

    # 이전 에이전트 산출물 중 필요한 것만 포함
    if consumes and previous_outputs:
        parts.append("\n## 이전 단계 산출물 (당신이 필요한 부분)")
        for dep in consumes:
            agent_name = dep.split(".")[0]
            section = dep.split(".", 1)[1] if "." in dep else None
            output = previous_outputs.get(agent_name, "")
            if output:
                label = f"[{agent_name}] {section}" if section else f"[{agent_name}]"
                # 출력에서 해당 섹션 추출 시도
                parts.append(f"\n### {label}")
                parts.append(output[:1500])

    # 출력 형식 가이드
    if produces:
        parts.append("\n## 당신의 출력에 반드시 포함할 섹션")
        for key, desc in produces.items():
            parts.append(f"- **{key}**: {desc}")

    return "\n".join(parts)


def build_gate_check_prompt(
    agent_name: str,
    agent_output: str,
    expected_sections: list[str],
) -> str:
    """
    게이트 체크: 에이전트 출력이 필수 섹션을 포함하는지 확인하는 프롬프트
    """
    return (
        f"다음은 [{agent_name}] 에이전트의 출력입니다.\n\n"
        f"{agent_output[:3000]}\n\n"
        f"다음 섹션이 포함되어 있는지 확인하세요:\n"
        + "\n".join(f"- {s}" for s in expected_sections)
        + "\n\n누락된 섹션이 있으면 'GATE_FAIL: 누락 목록'으로 응답하세요.\n"
        "모두 포함되어 있으면 'GATE_PASS'로 응답하세요."
    )
