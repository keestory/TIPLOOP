# 스킬: PR 리뷰 워크플로

> 에이전트가 PR을 자동으로 리뷰하는 전체 워크플로

## 트리거
- 새 PR이 열릴 때
- 리뷰 요청 시

## 워크플로

### 1단계: 컨텍스트 수집
```bash
gh pr view <PR_NUMBER> --json title,body,files,additions,deletions
gh pr diff <PR_NUMBER>
```

### 2단계: 관련 문서 로드
- AGENTS.md (프로젝트 맵)
- ARCHITECTURE.md (아키텍처 규칙)
- docs/DESIGN.md (설계 원칙)
- docs/SECURITY.md (보안 정책)

### 3단계: 린터 실행
```bash
python linters/architecture_linter.py .
python linters/naming_linter.py .
python linters/structure_validator.py .
```

### 4단계: ReviewAgent 실행
- diff와 린터 결과를 컨텍스트로 전달
- 정확성, 아키텍처, 보안, 품질 기준으로 리뷰

### 5단계: 피드백 제출
```bash
gh pr review <PR_NUMBER> --comment --body "<리뷰 내용>"
# 또는
gh pr review <PR_NUMBER> --approve
# 또는
gh pr review <PR_NUMBER> --request-changes --body "<수정 요청>"
```

### 6단계: 피드백 루프 (필요시)
- 작성자의 응답 확인
- 업데이트된 코드 재리뷰
- 모든 이슈 해결 시 승인

## 자율성 수준
- 경미한 이슈: 자동 코멘트
- 아키텍처 위반: 변경 요청
- 보안 이슈: 즉시 차단 + 사람 알림
