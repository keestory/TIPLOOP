# TIPLOOP — 개인 서비스 노트

다른 서비스의 **기능·기획·UX·콘텐츠·마케팅·비즈니스 모델·운영 모델**을 구조적으로
서비스를 뜯어보고, 내 일과 프로젝트에 적용할 포인트까지 남기는 개인 서비스 노트입니다.

- 제품 사양: [`docs/product-specs/tiploop-service-research.md`](../docs/product-specs/tiploop-service-research.md)
- 설계·디자인 시스템: [`docs/design-docs/ieum-design.md`](../docs/design-docs/ieum-design.md)
- **Supabase 셋업: [`docs/SUPABASE_SETUP.md`](../docs/SUPABASE_SETUP.md)**

## 기능

- **Google 소셜 로그인** (Supabase Auth) — 이메일/비밀번호 없음
- 온보딩 — 소셜이 주지 않는 **직군·연차·업종**만 추가로 받음
- 서비스 링크로 빠르게 시작하는 개인 홈 워크벤치
- 5분 추천·직접 선택·전체 중 깊이를 고르는 12개 분석 질문
- 본인 노트만 제목·본문 검색, 상세 조회, 수정
- 사용자별 private Storage에 이미지·짧은 영상을 남기는 개인 공간
- 공개 미디어 URL·댓글·공감·공유를 숨긴 개인 공간
- Data API 우회 접근을 막는 기본 거부 RLS

## 실행 (로컬)

데이터·인증 모두 **Supabase**. [`docs/SUPABASE_SETUP.md`](../docs/SUPABASE_SETUP.md)대로
키를 받은 뒤, `.env`를 만들고 한 명령으로 실행:

```bash
git clone https://github.com/keestory/TIPLOOP.git TIPLOOP && cd TIPLOOP
git checkout main
cp .env.example .env      # .env에 Session pooler URI와 공개 API 값을 채우기
bash scripts/dev.sh       # venv + 의존성 + DB 점검 + 서버
# http://127.0.0.1:8000
```

`scripts/dev.sh`가 가상환경 준비 → 의존성 설치 → `scripts/check_db.py`로 DB를 점검하고
(무엇이 틀렸는지 한국어로 안내) → uvicorn을 띄웁니다. 데모 데이터는 `python3 scripts/seed_demo.py`.

## 테스트 / 린트

DB 테스트는 별도의 Postgres가 필요합니다. 운영 `DATABASE_URL`은 테스트에 사용하지 않고,
명시적인 `TEST_DATABASE_URL`만 허용합니다:

```bash
TEST_DATABASE_URL=postgresql://localhost/tiploop_test python3 -m pytest tests/
python3 linters/architecture_linter.py .   # 레이어 의존성
```

## 구조 (레이어드 도메인 아키텍처)

의존성은 위→아래로만 흐릅니다 (`architecture_linter.py`로 강제).

```
app/
  types/      User(=회원) · Post · Comment (순수 데이터)
  config/     설정(브랜드/Supabase/DB 키) + 직군/연차/업종/카테고리 상수
  providers/  Supabase JWT 검증 · 세션 쿠키 서명 (stdlib만)
  repo/       Supabase Postgres 데이터 접근 (psycopg)
  service/    auth(소셜 로그인·온보딩) · research · community(레거시 호환)
  ui/         FastAPI 라우트 + 의존성 (소셜 로그인/콜백/온보딩 포함)
  main.py     엔트리포인트 (create_app)
templates/    Jinja2 (모노 + 형광 디자인 시스템, supabase-js로 OAuth)
static/       styles.css
```
