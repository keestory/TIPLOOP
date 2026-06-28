# 스킬: 버그 수정 워크플로

> 버그를 재현하고, 수정하고, 검증하는 전체 워크플로

## 트리거
- 버그 리포트 접수 시
- "버그", "수정", "fix", "bug" 키워드 감지

## 워크플로

### 1단계: 버그 분석 (CodeAgent)
- 버그 설명 분석
- 관련 코드 파일 탐색
- 로그/메트릭 확인 (가능한 경우)

### 2단계: 재현 (CodeAgent)
- 실패하는 테스트 작성
- 테스트 실행으로 버그 확인
```bash
python -m pytest tests/test_<module>.py -v
```

### 3단계: 수정 (CodeAgent)
- 근본 원인 식별
- 최소한의 변경으로 수정
- 아키텍처 규칙 준수

### 4단계: 검증 (TestAgent)
- 새 테스트 통과 확인
- 기존 테스트 회귀 없음 확인
```bash
python -m pytest --tb=short
```

### 5단계: 리뷰 (ReviewAgent)
- Ralph Wiggum Loop 실행
- 수정의 정확성 및 부작용 검토

### 6단계: PR 생성
```bash
git checkout -b fix/<issue-slug>
git add .
git commit -m "fix: <버그 설명>"
gh pr create --title "fix: <버그 설명>" --body "<상세 내용>"
```

## 에스컬레이션 기준
- 2번 이상 수정 시도 실패 시
- 다중 도메인에 걸친 버그
- 데이터 손실 위험이 있는 경우
