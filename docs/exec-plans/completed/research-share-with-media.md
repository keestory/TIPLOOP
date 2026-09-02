# 실행 계획 — 첨부 포함 연구 노트 공유

## 목표

작성자가 명시적으로 공유한 연구 노트를 링크 보유자가 로그인 없이 읽고, 노트에 첨부된 스크린샷과 영상을 함께 볼 수 있게 한다.

## 배경

현재 연구 노트와 첨부는 작성자에게만 보이며 `/posts/{id}/share`는 상세 화면으로 되돌아간다. 새 요구는 개인 공간을 공개 커뮤니티로 바꾸는 것이 아니라, 노트 단위로 취소 가능한 링크 공개를 제공하는 것이다.

## 접근법

- 노트마다 활성 공유 링크를 하나만 둔다.
- 링크는 기본 7일 뒤 만료되며 작성자가 그 전에 중지하거나 새 링크로 교체할 수 있다.
- 원문 토큰은 저장하지 않고 SHA-256 해시만 DB에 저장한다.
- 공개 내용은 링크 생성 시점의 스냅샷으로 고정해 이후 수정·추가 첨부를 자동 공개하지 않는다.
- 공개 페이지는 활성 토큰으로 노트를 조회하고 개인정보·편집 UI·Storage 경로를 노출하지 않는다.
- 첨부는 기존 private bucket에 유지한다.
- 공개 미디어 요청은 원문 링크에서 단방향 파생한 첨부별 grant를 쓰며, Supabase Edge Function이 활성 공유와 첨부 포함 여부를 매 요청 재검사한 뒤 private Storage 응답을 `no-store`로 스트리밍한다.
- 이미지와 영상의 Range 요청도 같은 검사를 거치므로 공유 중지 뒤 새 미디어 요청을 즉시 막는다. 이미 내려받은 파일은 기술적으로 회수할 수 없다.

## 태스크 분해

1. `post_shares` 스키마와 RLS·브라우저 권한 차단 추가
2. 공유 토큰 repo/service와 소유자 생성·중지 라우트 추가
3. 공개 노트·공유 관리 화면과 첨부 미디어 URL 연결
4. `shared-media` Edge Function 구현
5. 문서·회귀 테스트 갱신
6. Supabase migration·Edge Function·Vercel 배포 후 운영 검증

## 의사결정 로그

- 공개 버킷 전환은 기존 private-by-default 계약을 깨므로 사용하지 않는다.
- signed URL은 만료 뒤에도 Storage 캐시에 남을 수 있어 공개 공유에는 사용하지 않는다.
- 예전 외부 `image_url`·`video_url`은 출처와 공개 범위를 보장할 수 없어 공유 페이지에서 제외한다.
- 링크 공개는 검색 노출이 아니라 secret-link 접근으로 제한하고 `noindex`, `no-store`, `no-referrer`를 적용한다.
- 공유 생성·중지는 same-origin POST만 허용하고, URL은 설정된 운영 `SITE_URL`을 기준으로 만든다.

## 진행 상태

- [x] 현재 구조와 공식 Supabase Storage/Edge Function 계약 확인
- [x] 스키마·서비스·화면 구현
- [x] 자동 테스트
- [x] 원격 migration·함수 배포
- [x] Vercel 운영 배포·기본 거부 경로 검증

## 배포 검증

- Supabase `post_shares`, `post_share_media_grants`: RLS 활성, browser 역할 권한 없음
- `shared-media` v1: ACTIVE, custom grant 인증, 잘못된 grant 404, 다중 Range 416, 모두 `no-store`
- Vercel production: commit `5ecc93e`, `tiploop.vercel.app` alias READY, 배포 후 오류 로그 없음
- 운영 계정의 저장된 노트·첨부가 0개라 유효 이미지·영상 200/206와 공유 중지 후 404는 첫 실제 첨부 공유 때 사용자 스모크로 확인한다.
