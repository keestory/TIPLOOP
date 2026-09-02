# Vercel 배포 가이드 (TIPLOOP)

FastAPI 앱을 Vercel **Python 서버리스 함수**로 배포한다. 빌드 스텝 없이
`api/index.py` 가 ASGI 앱을 그대로 노출하고, 모든 경로가 이 함수로 라우팅된다.

## 추가된 파일

| 파일 | 역할 |
|------|------|
| `api/index.py` | Vercel 진입점 — `app.main:app`(ASGI)을 노출 |
| `api/requirements.txt` | 함수 런타임 의존성 (루트 오케스트레이터 requirements 대신 사용) |
| `vercel.json` | 모든 경로를 함수로 rewrite + `templates/`·`static/` 번들 |
| `.vercelignore` | 오케스트레이터/테스트/문서 등 배포 제외 |

## 1. 환경 변수 (Vercel → Settings → Environment Variables)

운영 Supabase 값은 **Production에만** 넣습니다. Preview에서 DB 흐름을 시험하려면
별도 Supabase Branch/테스트 프로젝트의 URL·키·DB를 Preview에 같은 세트로 넣으세요.
운영 `DATABASE_URL`·`IEUM_SECRET`·`CRON_SECRET`을 Preview와 공유하지 않습니다.

| 이름 | 값 | 비고 |
|------|-----|------|
| `DATABASE_URL` | Supabase **Transaction pooler**(IPv4) 문자열 | 서버리스는 이걸 권장 (아래 참고) |
| `SUPABASE_URL` | `https://<프로젝트>.supabase.co` | 브라우저 노출 공개값 |
| `SUPABASE_PUBLISHABLE_KEY` | publishable 키 | 브라우저 노출 공개값 |
| `SUPABASE_ANON_KEY` | legacy anon 키 | 이전 배포 호환용(선택) |
| `IEUM_SECRET` | 긴 랜덤 문자열 | 세션 쿠키 서명용 (비밀) |
| `SESSION_COOKIE_SECURE` | `1` | HTTPS 전용 세션 쿠키 강제 |
| `SUPABASE_JWT_SECRET` | (비워도 됨) | 토큰 검증은 Supabase에 위임 |
| `CRON_SECRET` | 긴 랜덤 문자열 | 크론 엔드포인트 보호 — Vercel이 자동으로 Bearer 헤더에 실어 호출 |
| `SITE_URL` | `https://tiploop.vercel.app` | OG·공유 카드 절대 URL |
| `SKIP_DB_INIT` | `1` | `schema.sql` 적용·RLS 검증이 끝난 배포에서만 사용 |

> **크론**: `vercel.json`의 `crons`가 일요일 09:00 UTC(한국 18:00)에
> `/cron/weekly-nudge`를 호출해 이번 주 미참여 크루원에게 마감 넛지 알림을 보낸다.
> `CRON_SECRET`이 없으면 엔드포인트는 401로 잠긴다.

### DATABASE_URL — 서버리스용 풀러
Supabase 대시보드 → **Connect** → **Transaction pooler**(포트 `6543`, IPv4)의
문자열을 쓰세요. 서버리스는 짧은 커넥션이 많이 열리므로 트랜잭션 풀러가 적합합니다.
비밀번호(`:` 다음)만 실제 DB 비번으로 교체.

```
postgresql://postgres.<ref>:<DB비번>@aws-1-<region>.pooler.supabase.com:6543/postgres
```

> 코드에서 `prepare_threshold=None` 로 prepared statement를 꺼 두었기 때문에
> pgbouncer 트랜잭션 풀러에서도 `prepared statement already exists` 오류가 안 납니다.

> ⚠️ `service_role` 키는 절대 넣지 마세요. 이 앱은 쓰지 않습니다.
> DB 비밀번호가 들어간 `DATABASE_URL` 은 **Vercel 환경변수에만** 두고 저장소에 커밋하지 마세요.
> `IEUM_SECRET`은 32자 미만이거나 기본값이면 앱이 시작되지 않습니다.

## 2. 스키마 준비 (한 번)

앱은 부팅 시 스키마를 멱등 생성(`init_db`)하고 RLS 상태까지 검증합니다. 실패하면
개인정보 경계를 보장할 수 없으므로 앱 시작을 중단합니다. 서버리스 콜드스타트에서
확실히 하려면 Supabase → SQL Editor 에 `supabase/schema.sql` 을 한 번 실행해
두면 안전합니다. 이후에만 `SKIP_DB_INIT=1`을 쓸 수 있으며, 이 경우에도 RLS 검증은
생략되지 않습니다. (팔로우·알림·topics 컬럼까지 모두 포함)

## 3. 배포하기

### 방법 A — GitHub 연결 (권장)
1. Vercel 프로젝트(`tiploop`)를 GitHub `keestory/TIPLOOP` 저장소에 연결
   (Settings → Git).
2. Production Branch를 정합니다(보통 `main`).
3. 환경 변수 저장 후, 해당 브랜치에 push 하면 자동 배포됩니다.
   - 다른 브랜치(예: `claude/harness-engineering-agent-...`)에 push 하면
     **Preview 배포**가 생성됩니다 — 실제 URL로 미리 확인 가능.

### 방법 B — Vercel CLI
```bash
npm i -g vercel
vercel login
vercel link --yes --scope keestory91-6294s-projects --project tiploop
# project id: prj_O43yIXI4hFoLMFqhB1PuZKWCOuNK
# 환경변수 넣기 (또는 대시보드에서)
vercel env add DATABASE_URL
vercel env add SUPABASE_URL
vercel env add SUPABASE_PUBLISHABLE_KEY
vercel env add IEUM_SECRET
vercel env add CRON_SECRET
vercel env add SESSION_COOKIE_SECURE
vercel env add SITE_URL
vercel env add SKIP_DB_INIT
vercel --prod          # 프로덕션 배포
```

## 4. 배포 후 점검
- `/login` → 구글/카카오 버튼이 보이는지
- 로그인 → 온보딩 → 홈 흐름
- 배포 환경에서 `python -m scripts.verify_supabase_privacy` 통과
- `IEUM_SECRET` 32자 이상, `SESSION_COOKIE_SECURE=1` 확인
- **Supabase Auth → URL Configuration** 의 Redirect URL에 배포 도메인
  (`https://<배포도메인>/auth/callback`)을 추가해야 소셜 로그인 콜백이 동작합니다.
- 새 이미지/영상 업로드와 선택적인 7일 공유 링크를 점검합니다. 공유 중지 뒤 텍스트와
  새 Range 미디어 요청이 모두 404인지 확인합니다.
- 이전 Public `attachments` 버킷이 있다면 공개 URL을 출시 전에 별도로 정리합니다
  (`docs/SUPABASE_SETUP.md` 참고).

## 참고: 정적 파일
`vercel.json` 의 `includeFiles` 로 `templates/`·`static/` 가 함수 번들에 포함되고,
`/static/*` 는 FastAPI의 StaticFiles가 서빙합니다(작은 CSS/JS라 충분).
