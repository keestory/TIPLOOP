# 실행 계획: TIPLOOP 개인 서비스 연구 노트 전환

> 상태: completed — 원격 DB 게이트 별도 실행 필요
> 작성일: 2026-09-01
> 완료일: 2026-09-01
> 담당: PlannerAgent · CodeAgent · TestAgent · ReviewAgent · UI/UXAgent · StrategyAgent

## 목표

기존 공개 커뮤니티의 주요 화면을 개인 서비스 연구 노트로 전환한다. 기존 `posts` 데이터 구조를 재사용하면서 본인 소유권 격리, 구조화 작성, 검색, 수정, 적용 큐까지 한 흐름으로 완성한다.

## 완료 범위

- `category=reference`를 개인 서비스 분석 노트로 재정의
- 홈·보관함·작성·상세·편집·계정 화면 전환
- 12개 분석 관점, 채운 항목 진행도, `실제로 적용할 것` 큐
- 작성 중 기기 내 자동 초안과 textarea 자동 높이
- `author_id`와 `category`를 SQL 조건에 둔 읽기·수정 경계
- 타 사용자 계정·기록 404, 레거시 댓글 반응·팔로우 410
- 이전 자유 형식 본문과 이미지·영상 URL의 읽기·수정 보존
- 13개 앱 테이블 RLS와 browser 역할 정책 부재의 fail-closed 부팅 검증
- 32자 이상 세션 비밀키 fail-closed 검증과 HTTPS 전용 세션 쿠키
- publishable key Data API canary 배포 스크립트

## 검증

- [x] no-DB 단위·정적 테스트 통과
- [x] 로그인 게이트·소유권 SQL·레거시 변조 회귀 테스트 추가
- [x] strict 프론트엔드 감사 0건
- [x] 구조 검증 통과
- [x] 아키텍처·네이밍 린터 신규 위반 0건
- [x] 모바일 390×844 핵심 흐름 브라우저 QA
- [ ] 전용 Postgres에서 DB 의존 전체 테스트 실행
- [ ] 실제 Supabase에서 RLS + anon Data API canary 실행

## 남은 출시 게이트

1. 이름이 `tiploop_test` 또는 `_test`로 끝나는 전용 DB에 `tiploop_test_guard` 마커를 사람이 먼저 만들고, `TIPLOOP_TEST_DB_CONFIRM`에 DB 이름을 다시 입력한 뒤 전체 테스트를 실행한다. 원격이면 `ALLOW_REMOTE_TEST_DB=1`과 정확한 `TEST_DATABASE_PROJECT_REF`도 필요하다.
2. 배포 대상 환경에서 `python -m scripts.verify_supabase_privacy`를 실행한다.
3. 기존 Public `attachments` 버킷 객체를 내보내 보관한 뒤 비공개 전환 또는 삭제하고 URL 처리 결과를 점검한다.

전용 테스트 DB의 안전 마커는 테스트 실행 전에 사람이 다음 SQL로 한 번만 만듭니다.

```sql
CREATE TABLE public.tiploop_test_guard (
  marker TEXT PRIMARY KEY CHECK (marker = 'TIPLOOP_TEST_ONLY')
);
INSERT INTO public.tiploop_test_guard (marker)
VALUES ('TIPLOOP_TEST_ONLY') ON CONFLICT DO NOTHING;
```

## 의사결정 로그

| 날짜 | 결정 | 이유 |
|------|------|------|
| 2026-09-01 | 기존 `reference` 데이터 구조 재사용 | 새 제품 루프를 빠르게 검증하면서 기존 기록을 보존 |
| 2026-09-01 | 개인 소유권과 RLS를 첫 범위에 포함 | 서비스 연구 내용의 노출 위험 방지 |
| 2026-09-01 | 비교·태그·AI는 후순위 | 실제 기록 패턴 확인 전 스키마 과설계 방지 |
| 2026-09-01 | 서버 초안 대신 로컬 초안을 우선 | 장문 유실 P0를 DB 스키마 변경 없이 즉시 완화 |
| 2026-09-01 | 병합·배포는 수행하지 않음 | 사용자 요청 범위와 원격 계정 권한 경계를 유지 |
