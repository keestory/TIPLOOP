# CLAUDE.md — 프로젝트 맵

> 이 파일은 백과사전이 아닌 **목차**입니다.
> 상세 정보는 docs/ 링크를 따라가세요.

## 프로젝트: Harness Engineering 오케스트레이터

에이전트가 코드를 작성하고, 사람이 조정하는 시스템.

## 구조

```
.claude/agents/     → 에이전트 정의 (coder, reviewer, tester, planner 등)
orchestrator/       → 오케스트레이터 코어 (Claude Code CLI 기반)
linters/            → 아키텍처 경계 강제 도구
docs/               → 지식 베이스 (기록 시스템)
skills/             → 재사용 가능한 워크플로
templates/          → 실행 계획, 설계 문서 템플릿
```

## 사용 가이드 → [docs/USAGE_GUIDE.md](./docs/USAGE_GUIDE.md)

에이전트 호출법, 오케스트레이터 사용법, 다른 프로젝트 적용법, 비용 감각.

## 아키텍처 → [ARCHITECTURE.md](./ARCHITECTURE.md)

레이어: Types → Config → Providers → Repo → Service → Runtime → UI
의존성은 위→아래로만. 위반 시 `python3 linters/architecture_linter.py .`

## 에이전트

### 제품 (Product)
| 에이전트 | 역할 | 모델 |
|----------|------|------|
| pm | 제품 사양, 수용 기준, 우선순위 | opus |
| designer | UI/UX 설계, 디자인 시스템, 접근성 | opus |

### 엔지니어링 (Engineering)
| 에이전트 | 역할 | 모델 |
|----------|------|------|
| planner | 실행 계획 수립 | opus |
| coder | 코드 작성/수정 | sonnet |
| tester | 테스트 작성/실행 | sonnet |

### 검증 (Verification)
| 에이전트 | 역할 | 모델 |
|----------|------|------|
| reviewer | 읽기 전용 코드 리뷰 | opus |
| security-reviewer | 보안 전문 리뷰 | opus |

### 운영 (Operations)
| 에이전트 | 역할 | 모델 |
|----------|------|------|
| ops | 배포 검토, 장애 대응, 모니터링 | sonnet |
| analyst | 지표 설계, 데이터 분석, 효과 검증 | sonnet |
| doc-gardener | 문서 가비지 컬렉션 | sonnet |
| quality-scorer | 품질 등급 평가 | sonnet |

## 핵심 명령어

```bash
# 린터
python3 linters/architecture_linter.py .
python3 linters/naming_linter.py .
python3 linters/structure_validator.py .
python3 run.py --lint

# 오케스트레이터
python3 run.py "프롬프트"
python3 run.py --agent coder "프롬프트"
python3 run.py --review 2          # Level 2 리뷰
python3 run.py --gc                # 가비지 컬렉션
python3 run.py --quality           # 품질 평가
```

## 지식 베이스 → [docs/](./docs/)

| 경로 | 설명 |
|------|------|
| [docs/design-docs/](./docs/design-docs/) | 설계 문서, 핵심 신념 |
| [docs/exec-plans/](./docs/exec-plans/) | 실행 계획 (active/completed) |
| [docs/DESIGN.md](./docs/DESIGN.md) | 설계 원칙 |
| [docs/QUALITY_SCORE.md](./docs/QUALITY_SCORE.md) | 품질 등급 |
| [docs/SECURITY.md](./docs/SECURITY.md) | 보안 정책 |
| [docs/RELIABILITY.md](./docs/RELIABILITY.md) | 안정성 요구사항 |
| [docs/UX_GUIDELINES.md](./docs/UX_GUIDELINES.md) | UX 가이드라인 |
| [docs/DESIGN_SYSTEM.md](./docs/DESIGN_SYSTEM.md) | 디자인 시스템 (토큰, 컴포넌트) |
| [docs/product-specs/](./docs/product-specs/) | 제품 사양 (PM 작성) |
| [docs/METRICS.md](./docs/METRICS.md) | 지표 설계 가이드 (Analyst 참조) |
| [docs/KNOWN_ISSUES.md](./docs/KNOWN_ISSUES.md) | 발생한 에러와 해결법 (재발 방지) |
| [docs/USAGE_GUIDE.md](./docs/USAGE_GUIDE.md) | 사용 가이드 |
| [docs/VERCEL_DEPLOY.md](./docs/VERCEL_DEPLOY.md) | Vercel 배포 가이드 (서버리스) |
| [docs/MOBILE_APP.md](./docs/MOBILE_APP.md) | 모바일 앱 배포 (PWA·Capacitor·TWA) |

## 규칙

1. 코드 변경 후 반드시 린터 실행
2. 파일당 300줄 이하
3. 경계에서 데이터 파싱
4. 구조화된 로깅 사용
5. 시크릿은 환경 변수로만
