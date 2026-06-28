# 계획 수립 가이드

## 계획은 일급 아티팩트

계획은 코드와 동등한 수준의 아티팩트입니다.
리포지터리에 버전 관리되며, 에이전트가 접근할 수 있습니다.

## 계획 유형

### 일시적 계획 (Ephemeral)
- 작은 변경, 단일 PR 범위
- 에이전트 컨텍스트 내에서 관리
- 리포지터리에 저장하지 않음

### 실행 계획 (Execution Plan)
- 복잡한 작업, 다중 PR 범위
- `docs/exec-plans/active/`에 저장
- 진행 상황 및 의사결정 로그 포함
- 완료 시 `docs/exec-plans/completed/`로 이동

## 실행 계획 작성

→ [템플릿](../templates/exec_plan_template.md) 사용

### 필수 섹션
1. **목표**: 무엇을 달성하려는가
2. **배경**: 왜 필요한가
3. **접근법**: 어떻게 구현할 것인가
4. **태스크 분해**: 구체적인 단계
5. **의사결정 로그**: 선택과 이유
6. **진행 상태**: 현재 진행 상황

## 진행 중인 계획

→ [exec-plans/active/](./exec-plans/active/) 참조

## 완료된 계획

→ [exec-plans/completed/](./exec-plans/completed/) 참조
