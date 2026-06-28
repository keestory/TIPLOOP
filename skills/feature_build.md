# 스킬: 기능 구현 워크플로

> 기능을 기획하고, 구현하고, 테스트하는 전체 워크플로

## 트리거
- 기능 요청 접수 시
- 실행 계획 승인 후

## 워크플로

### 1단계: 계획 수립 (PlannerAgent)
- 요구사항 분석
- 실행 계획 작성 → `docs/exec-plans/active/` 저장
- 사람의 승인 대기

### 2단계: 아키텍처 검토 (PlannerAgent)
- 기존 아키텍처와의 정합성 확인
- 필요한 레이어/도메인 식별
- 의존성 영향 분석

### 3단계: 구현 (CodeAgent)
깊이 우선 분해 방식:
1. Types 레이어: 데이터 구조 정의
2. Config 레이어: 설정 항목 추가
3. Repo 레이어: 데이터 접근 구현
4. Service 레이어: 비즈니스 로직 구현
5. Runtime/UI 레이어: 실행 환경 연결

### 4단계: 테스트 (TestAgent)
- 각 레이어별 단위 테스트 작성
- 통합 테스트 작성
- 커버리지 확인

### 5단계: 린팅 (LinterAgent)
```bash
python linters/architecture_linter.py .
python linters/naming_linter.py .
python linters/structure_validator.py .
```

### 6단계: 리뷰 루프 (ReviewAgent)
- 코드 리뷰
- 피드백 반영
- 승인까지 반복

### 7단계: 문서 업데이트 (DocGardener)
- 관련 문서 업데이트
- AGENTS.md 반영 필요시 수정
- 실행 계획 완료 처리

### 8단계: PR 생성 및 병합
```bash
git checkout -b feat/<feature-slug>
git add .
git commit -m "feat: <기능 설명>"
gh pr create --title "feat: <기능 설명>" --body "<상세 내용>"
```

## 품질 게이트
- [ ] 모든 테스트 통과
- [ ] 아키텍처 린트 위반 0건
- [ ] 리뷰 승인
- [ ] 문서 업데이트 완료
