# Supabase 셋업 가이드 (TIPLOOP)

TIPLOOP은 **인증=Supabase Auth(구글·Apple), 데이터=Supabase Postgres**로 동작합니다.
아래 값들을 환경 변수로 넣으면 됩니다. (`.env.example` 참고)

| 환경 변수 | 어디서 | 용도 |
|-----------|--------|------|
| `DATABASE_URL` | Supabase → Project Settings → Database → Connection string (URI) | Postgres 접속 |
| `SUPABASE_URL` | Project Settings → API → Project URL | 프론트 OAuth 시작 |
| `SUPABASE_PUBLISHABLE_KEY` | Project Settings → API Keys → Publishable key | 프론트 OAuth 시작 |
| `SUPABASE_ANON_KEY` | Legacy API Keys → `anon` key | 이전 배포 호환용(선택) |
| `SUPABASE_JWT_SECRET` | Project Settings → API → JWT Settings → JWT Secret | 백엔드 토큰 검증 |
| `IEUM_SECRET` | 직접 생성(긴 랜덤 문자열) | 자체 세션 쿠키 서명 |
| `SESSION_COOKIE_SECURE` | 배포 `1`, 로컬 HTTP만 `0` | HTTPS 전용 쿠키 |

현재 운영 프로젝트 ref는 `ftiynbgisypjjkakzcif`입니다. API URL과 DB pooler
사용자명(`postgres.<ref>`)의 ref가 다르면 앱이 시작되지 않습니다.

## 1. 프로젝트 만들기
1. https://supabase.com 에서 프로젝트 생성.
2. 위 표의 연결값을 복사해 환경 변수로 설정. 새 프로젝트는 `SUPABASE_PUBLISHABLE_KEY`를 권장합니다.
3. `supabase/schema.sql`을 먼저 적용합니다. 앱 테이블은 서버의 `DATABASE_URL`로만 접근하며, Data API 우회 노출을 막기 위해 RLS 기본 거부와 `anon`·`authenticated` 직접 권한 회수를 함께 적용합니다. RLS 적용·검증에 실패하면 앱은 시작되지 않습니다.
4. Vercel에는 **Transaction pooler(:6543)**, 로컬 장기 실행에는 **Session pooler(:5432)** 전체 URI를 사용합니다. 채팅·문서에 게시된 DB 비밀번호는 회전하고 예약문자는 percent-encode합니다.

## 2. 구글 로그인
1. Google Cloud Console → "OAuth 동의 화면" 설정 → "사용자 인증 정보"에서 **OAuth 클라이언트 ID(웹)** 생성.
2. 승인된 리디렉션 URI에 Supabase 콜백 추가:
   `https://<ref>.supabase.co/auth/v1/callback`
3. 발급된 Client ID/Secret을 Supabase → Authentication → Providers → **Google**에 입력, 활성화.

## 3. Apple 로그인

App Store 제출 전 Apple Developer의 App ID·Services ID와 Supabase Apple provider를
연결하고, 실제 iPhone에서 로그인과 계정 삭제 시 인증 해제까지 확인합니다. 설정과
검증이 끝나기 전에는 `APPLE_AUTH_ENABLED=0`을 유지합니다.

## 3-2. 연구 노트 비공개 첨부

`supabase/schema.sql` 또는 최신 migration은 `tiploop-research-images`와
`tiploop-research-videos`를 private bucket으로 만들고, 로그인 사용자 UUID로 시작하는
경로의 INSERT·SELECT·DELETE만 허용합니다. 앱은 signed URL을 10분 동안만 발급하며
DB에는 URL이 아닌 bucket과 path를 저장합니다.

이미지는 파일당 10MiB, 영상은 파일당 50MiB이고 노트 하나에는 합계 6개·영상 1개·전체
100MiB 제한을 둡니다. 기존 `attachments` 버킷을 Public으로 만들거나 공개 읽기 정책을
추가하지 마세요. 과거 `posts.image_url`과 `posts.video_url`은 소유자 상세에서 호환 표시만
하므로 공개 URL 자체는 별도로 정리해야 합니다.

작성자가 첨부 포함 링크를 만들면 `post_shares`에는 7일 만료 스냅샷과 원문 토큰 해시,
`post_share_media_grants`에는 첨부별 grant 해시만 저장합니다. `shared-media` Edge Function은
`verify_jwt=false`로 배포하지만 자체 256-bit secret grant를 검증하고 service key로 private
객체를 스트리밍합니다. 두 테이블에도 browser 역할 정책이나 직접 권한을 만들지 마세요.

## 4. 리디렉션 허용 URL
Supabase → Authentication → URL Configuration → **Redirect URLs**에 앱 주소의 콜백을 추가:
```
http://127.0.0.1:8000/auth/callback     (로컬)
https://tiploop.vercel.app/auth/callback (배포)
```

## 5. 로그인 흐름 (참고)
```
[로그인 페이지] 구글/Apple 클릭
   → supabase-js signInWithOAuth → 제공자 동의 → Supabase
   → /auth/callback (supabase-js가 세션 파싱)
   → POST /auth/session  (백엔드가 JWT 검증 → 교사 upsert → 세션 쿠키)
   → 신규/미완료면 /onboarding (직군·연차·업종)
   → 완료면 /
```

## 6. 배포 전 개인정보 게이트

배포 대상 환경 변수를 로드한 뒤 아래 명령이 통과해야 합니다.

```bash
python -m scripts.verify_supabase_privacy
```

이 검사는 API/DB 프로젝트 ref 일치, public 앱 테이블 15개의 RLS, 브라우저 역할
정책·직접 권한 부재, publishable key의 `posts` Data API 차단을 확인합니다. 또한 두 연구
버킷의 private·파일 제한과 Storage objects의 anon/public 정책 부재를 확인합니다.
