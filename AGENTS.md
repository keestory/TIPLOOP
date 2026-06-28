# AGENTS.md — 에이전트를 위한 맵

> 이 파일은 백과사전이 아닌 **목차**입니다.
> 에이전트는 여기서 시작하여 필요한 깊이의 문서로 이동합니다.

## 리포지터리 구조

```
orchestrator/    → 오케스트레이터 코어 (태스크 분해, 에이전트 실행, 리뷰 루프)
agents/          → 에이전트 정의 (코드, 리뷰, 테스트, 문서관리, 품질평가)
linters/         → 아키텍처 경계 강제 및 구조 검증
skills/          → 재사용 가능한 워크플로 스킬
templates/       → 실행 계획, 설계 문서 템플릿
docs/            → 지식 베이스 (기록 시스템)
```

## 핵심 원칙

1. **리포지터리가 기록 시스템** — 에이전트가 접근할 수 없는 것은 존재하지 않음
2. **점진적 공개** — 작은 진입점에서 시작, 필요시 깊이 탐색
3. **기계적 강제** — 아키텍처 경계는 린터와 테스트로 강제
4. **가비지 컬렉션** — 기술 부채는 매일 조금씩 해결

## 아키텍처 → [ARCHITECTURE.md](./ARCHITECTURE.md)

도메인 레이어링, 의존성 방향, 허용 경계에 대한 상세 정보.

## 지식 베이스 → [docs/](./docs/)

| 경로 | 설명 |
|------|------|
| `docs/design-docs/` | 설계 문서 및 핵심 신념 |
| `docs/exec-plans/active/` | 진행 중인 실행 계획 |
| `docs/exec-plans/completed/` | 완료된 실행 계획 |
| `docs/product-specs/` | 제품 사양 |
| `docs/references/` | 외부 참조 (llms.txt 등) |
| `docs/generated/` | 자동 생성 문서 (스키마 등) |
| `docs/DESIGN.md` | 설계 원칙 |
| `docs/FRONTEND.md` | 프론트엔드 가이드 |
| `docs/PLANS.md` | 계획 수립 가이드 |
| `docs/PRODUCT_SENSE.md` | 제품 감각 및 UX 원칙 |
| `docs/QUALITY_SCORE.md` | 도메인별 품질 등급 |
| `docs/RELIABILITY.md` | 안정성 요구사항 |
| `docs/SECURITY.md` | 보안 정책 |

## 에이전트 유형

| 에이전트 | 역할 | 자율성 수준 |
|----------|------|------------|
| `CodeAgent` | 코드 생성 및 수정 | 중 (리뷰 필요) |
| `ReviewAgent` | PR 코드 리뷰 | 높 (자동 승인 가능) |
| `TestAgent` | 테스트 생성 및 실행 | 높 |
| `DocGardener` | 문서 최신화 및 정리 | 높 (자동 병합 가능) |
| `QualityScorer` | 도메인별 품질 평가 | 높 |
| `LinterAgent` | 아키텍처 위반 감지 | 높 |
| `PlannerAgent` | 실행 계획 수립 | 낮 (사람 승인 필요) |

## 워크플로

1. **기능 구현**: PlannerAgent → CodeAgent → TestAgent → ReviewAgent → 병합
2. **버그 수정**: CodeAgent(재현) → CodeAgent(수정) → TestAgent(검증) → ReviewAgent
3. **문서 정비**: DocGardener(스캔) → DocGardener(수정) → 자동 병합
4. **품질 관리**: QualityScorer(평가) → LinterAgent(검증) → CodeAgent(리팩터링)

## 린터 규칙 → [linters/](./linters/)

아키텍처 경계, 네이밍 컨벤션, 파일 구조 규칙이 정의되어 있음.
위반 시 에이전트 친화적 오류 메시지 제공.

## 스킬 → [skills/](./skills/)

| 스킬 | 설명 |
|------|------|
| `review_pr` | PR 리뷰 전체 워크플로 |
| `bug_fix` | 버그 재현 → 수정 → 검증 |
| `feature_build` | 기능 기획 → 구현 → 테스트 |
| `doc_gardening` | 문서 최신화 스캔 및 수정 |
