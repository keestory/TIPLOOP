# Supabase 셋업 가이드 (이음)

이음은 **인증=Supabase Auth(구글·카카오), 데이터=Supabase Postgres**로 동작합니다.
아래 값들을 환경 변수로 넣으면 됩니다. (`.env.example` 참고)

| 환경 변수 | 어디서 | 용도 |
|-----------|--------|------|
| `DATABASE_URL` | Supabase → Project Settings → Database → Connection string (URI) | Postgres 접속 |
| `SUPABASE_URL` | Project Settings → API → Project URL | 프론트 OAuth 시작 |
| `SUPABASE_ANON_KEY` | Project Settings → API → `anon` public key | 프론트 OAuth 시작 |
| `SUPABASE_JWT_SECRET` | Project Settings → API → JWT Settings → JWT Secret | 백엔드 토큰 검증 |
| `IEUM_SECRET` | 직접 생성(긴 랜덤 문자열) | 자체 세션 쿠키 서명 |

## 1. 프로젝트 만들기
1. https://supabase.com 에서 프로젝트 생성.
2. 위 표의 4개 값을 복사해 환경 변수로 설정.
3. 스키마는 앱 첫 기동 시 `init_db()`가 자동 생성합니다(teachers/posts/comments/reactions).

## 2. 구글 로그인
1. Google Cloud Console → "OAuth 동의 화면" 설정 → "사용자 인증 정보"에서 **OAuth 클라이언트 ID(웹)** 생성.
2. 승인된 리디렉션 URI에 Supabase 콜백 추가:
   `https://<ref>.supabase.co/auth/v1/callback`
3. 발급된 Client ID/Secret을 Supabase → Authentication → Providers → **Google**에 입력, 활성화.

## 3. 카카오 로그인
1. https://developers.kakao.com 에서 애플리케이션 생성.
2. 카카오 로그인 활성화 → Redirect URI에 `https://<ref>.supabase.co/auth/v1/callback` 추가.
3. **동의항목**에서 카카오계정(이메일) — 이름/이메일 을 사용 설정.
4. REST API 키/Client Secret을 Supabase → Authentication → Providers → **Kakao**에 입력, 활성화.

> 전화번호는 현재 받지 않습니다(추후 필요 시 문자 인증 또는 카카오 동의항목으로 추가 가능).

## 4. 리디렉션 허용 URL
Supabase → Authentication → URL Configuration → **Redirect URLs**에 앱 주소의 콜백을 추가:
```
http://127.0.0.1:8000/auth/callback     (로컬)
https://<배포도메인>/auth/callback        (배포)
```

## 5. 로그인 흐름 (참고)
```
[로그인 페이지] 구글/카카오 클릭
   → supabase-js signInWithOAuth → 제공자 동의 → Supabase
   → /auth/callback (supabase-js가 세션 파싱)
   → POST /auth/session  (백엔드가 JWT 검증 → 교사 upsert → 세션 쿠키)
   → 신규/미완료면 /onboarding (학교급·지역·담당)
   → 완료면 /
```
