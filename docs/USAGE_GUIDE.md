# 사용 가이드

## 빠른 시작

```bash
cd /Users/user/Desktop/harness-engineering
```

## 1. 에이전트 직접 호출 (가장 실용적)

에이전트 하나를 골라서 대화형으로 사용합니다.

```bash
# 기획
claude --agent pm                    # PM과 대화하면서 사양 정리
claude --agent designer              # UI/UX 설계
claude --agent analyst               # 지표 설계, 데이터 분석

# 구현
claude --agent planner               # 실행 계획 수립
claude --agent coder                 # 코드 작성/수정
claude --agent tester                # 테스트 작성/실행

# 검증
claude --agent reviewer              # 코드 리뷰
claude --agent security-reviewer     # 보안 리뷰
claude --agent ops                   # 배포 검토, 장애 대응

# 운영
claude --agent doc-gardener          # 문서 관리
claude --agent quality-scorer        # 품질 평가
```

### 프롬프트 예시

```bash
# PM — 제품 사양 작성
claude --agent pm "사용자 온보딩 기능의 제품 사양을 작성해줘. 수용 기준도 포함해서."

# Designer — 화면 설계
claude --agent designer "온보딩 플로우를 설계해줘. 3단계 이내로."

# Coder — 구현
claude --agent coder "온보딩 API 엔드포인트를 구현해줘. docs/product-specs/ 참고."

# Reviewer — 리뷰
claude --agent reviewer "orchestrator/ 디렉토리 코드를 리뷰해줘"

# Ops — 배포 검토
claude --agent ops "이번 변경사항의 배포 영향을 분석해줘"

# Analyst — 효과 분석
claude --agent analyst "온보딩 기능의 성공 지표를 설계해줘"
```

### 격리 환경에서 실행 (git worktree)

병렬로 여러 기능을 작업할 때:

```bash
claude -w feature-auth --agent coder "인증 모듈 구현"
claude -w feature-onboarding --agent coder "온보딩 구현"
# 각각 별도 브랜치에서 독립적으로 작업
```

### 비대화형 실행 (스크립트/자동화용)

```bash
# JSON 출력으로 파이프라인에 연결
claude -p --agent reviewer --output-format json "src/ 리뷰해줘"

# 비용 제한
claude -p --agent coder --max-budget-usd 2.0 "버그 수정해줘"
```

## 2. 오케스트레이터 (전체 파이프라인)

여러 에이전트가 순서대로, 또는 병렬로 실행됩니다.

```bash
# 자동 감지 — 프롬프트 키워드로 워크플로 선택
python3 run.py "결제 기능을 만들어줘"        # → feature 파이프라인
python3 run.py "로그인 버그 수정"            # → bugfix
python3 run.py "버튼 문구 변경"             # → small-change
python3 run.py "서버 장애 대응"             # → incident
python3 run.py "출시 효과 분석"             # → analyze
python3 run.py "제품 사양 작성"             # → spec

# 워크플로 직접 지정
python3 run.py --workflow feature "결제 기능"
python3 run.py --workflow ui-feature "대시보드 페이지"
python3 run.py --workflow small-change "에러 메시지 문구 수정"

# 단일 에이전트만
python3 run.py --agent coder "utils 모듈 리팩터링"
python3 run.py --agent pm "검색 기능 사양 작성"
```

### 워크플로 목록

```bash
python3 run.py --workflows
```

| 워크플로 | 파이프라인 | 언제 |
|----------|----------|------|
| feature | (pm+analyst) → designer → planner → coder → [lint] → (tester+reviewer) → [review] → (ops+analyst) | 새 기능 전체 |
| ui-feature | (pm+analyst) → designer → planner → coder → [lint] → (designer+reviewer) → [review] | UI 기능 |
| bugfix | coder → [lint] → (tester+reviewer) → [review] | 버그 수정 |
| small-change | coder → [lint] | 문구/설정 변경 |
| refactor | quality-scorer → planner → coder → [lint] → (tester+reviewer) → [review] → quality-scorer | 리팩터링 |
| spec | pm → analyst → designer | 기획만 |
| incident | ops → coder → (tester+reviewer) → ops → planner(포스트모템) | 장애 대응 |
| analyze | analyst → pm | 출시 후 분석 |
| docs | doc-gardener → [lint] | 문서 관리 |
| review | reviewer → ?보안분기 → security-reviewer | 리뷰만 |

## 3. 유지보수 명령어

```bash
# 린터 (로컬, Claude 호출 없이)
python3 run.py --lint

# 품질 평가 (에이전트)
python3 run.py --quality

# 가비지 컬렉션 (quality-scorer + doc-gardener 병렬)
python3 run.py --gc

# 에이전트 목록
python3 run.py --agents

# 리뷰 (레벨 지정)
python3 run.py --review 3 "인증 모듈 변경 리뷰"
```

## 4. 다른 프로젝트에 적용하기

이 에이전트 시스템을 다른 프로젝트에서 사용하려면:

```bash
# 에이전트 정의 복사
cp -r /Users/user/Desktop/harness-engineering/.claude /path/to/your/project/

# 최소 필요 파일
# .claude/agents/*.md    — 에이전트 정의
# .claude/settings.json  — 권한 설정
# CLAUDE.md              — 프로젝트 맵 (프로젝트에 맞게 수정)

# 선택적 — 프로젝트에 맞게 커스터마이즈
# docs/                  — 지식 베이스
# linters/               — 아키텍처 린터
# orchestrator/          — 오케스트레이터 (python3 run.py)
```

### 커스터마이즈 포인트

| 파일 | 수정 대상 |
|------|----------|
| `.claude/agents/coder.md` | 프로젝트 기술 스택, 코딩 규칙 |
| `.claude/agents/reviewer.md` | 리뷰 기준, 아키텍처 규칙 |
| `.claude/agents/pm.md` | 제품 도메인, 사용자 페르소나 |
| `.claude/agents/designer.md` | 디자인 원칙, 피해야 할 패턴 |
| `CLAUDE.md` | 프로젝트 구조, 핵심 명령어 |
| `docs/DESIGN.md` | 프로젝트 설계 원칙 |
| `docs/SECURITY.md` | 보안 정책 |

## 5. 비용 감각

| 사용 방식 | 예상 비용 |
|----------|----------|
| 에이전트 1개 대화 (5-10턴) | $0.1 ~ $0.5 |
| small-change 워크플로 | $0.3 ~ $1 |
| bugfix 워크플로 | $1 ~ $3 |
| feature 워크플로 (풀사이클) | $5 ~ $15 |
| 가비지 컬렉션 | $0.5 ~ $2 |

`--max-budget-usd` 플래그로 에이전트별 비용 제한 가능.

## 6. 추천 작업 방식

### 새 기능을 만들 때

```bash
# 1. PM과 사양 정리
claude --agent pm "기능 설명..."

# 2. 설계
claude --agent designer "PM 사양 기반으로 설계..."

# 3. 계획
claude --agent planner "사양과 설계 기반으로 실행 계획..."

# 4. 구현
claude --agent coder "계획대로 구현..."

# 5. 리뷰
claude --agent reviewer "구현 결과 리뷰..."
```

에이전트를 **한 단계씩 대화하면서** 진행하는 게 가장 실용적입니다.
결과를 확인하고, 피드백을 주고, 다음 단계로 넘기세요.

### 자동화하고 싶을 때

위 과정이 익숙해지면 오케스트레이터로 한 번에:

```bash
python3 run.py "결제 기능을 만들어줘"
```

### 매일 하면 좋은 것

```bash
python3 run.py --lint    # 아침에 린트 한 번
python3 run.py --gc      # 주 1회 가비지 컬렉션
```
