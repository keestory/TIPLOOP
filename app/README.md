# 이음(Ieum) — 선생님 오픈 커뮤니티

유치원·초·중·고 선생님들이 **닫힌 단톡방을 넘어** 정보·세미나·고민을 나누는 열린 커뮤니티.
이 저장소의 하네스 워크플로(PM → Designer → Planner → Coder → Tester → Reviewer)를 따라 만든 첫 앱입니다.

- 제품 사양: [`docs/product-specs/ieum-community.md`](../docs/product-specs/ieum-community.md)
- 설계·디자인 시스템: [`docs/design-docs/ieum-design.md`](../docs/design-docs/ieum-design.md)
- **Supabase 셋업: [`docs/SUPABASE_SETUP.md`](../docs/SUPABASE_SETUP.md)**

## 기능

- **구글·카카오 소셜 로그인** (Supabase Auth) — 이메일/비밀번호 없음
- 온보딩 — 소셜이 주지 않는 **학교급·지역·담당**만 추가로 받음(전화번호는 카카오가 주면 자동, 구글이면 입력)
- 글쓰기 — `정보공유` · `세미나` · `고민나눔` 세 카테고리 통합 (세미나는 일시·장소·링크)
- 피드 정렬(최신·공감·화제) + 필터(카테고리·학교급·지역)
- 공감(♥)·댓글·답글 스레드, 누구나 읽기 가능(오픈 원칙)
- 교사 프로필 + 받은 공감(카르마)

## 실행 (로컬)

데이터·인증 모두 **Supabase**를 씁니다. 먼저 [`docs/SUPABASE_SETUP.md`](../docs/SUPABASE_SETUP.md)대로
프로젝트를 만들고 키를 받으세요. Python 3.9+.

```bash
git clone https://github.com/keestory/ft.git FT && cd FT
git checkout claude/harness-engineering-agent-acwvo2
python3 -m venv .venv && source .venv/bin/activate
pip install -r app/requirements.txt

# 환경 변수 (.env.example 참고)
export DATABASE_URL="postgresql://postgres:[PW]@db.<ref>.supabase.co:5432/postgres"
export SUPABASE_URL="https://<ref>.supabase.co"
export SUPABASE_ANON_KEY="..."
export SUPABASE_JWT_SECRET="..."
export IEUM_SECRET="$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))')"

# (선택) 데모 글/세미나/댓글/공감 채우기
python3 scripts/seed_demo.py

uvicorn app.main:app --reload   # http://127.0.0.1:8000
```

> Supabase의 Redirect URLs에 `http://127.0.0.1:8000/auth/callback`을 꼭 추가하세요.

## 테스트 / 린트

테스트는 Postgres가 필요합니다(로컬 PG 또는 Supabase). `DATABASE_URL`을 주고 실행:

```bash
DATABASE_URL=postgresql://... python3 -m pytest tests/
python3 linters/architecture_linter.py .   # 레이어 의존성
```

## 구조 (레이어드 도메인 아키텍처)

의존성은 위→아래로만 흐릅니다 (`architecture_linter.py`로 강제).

```
app/
  types/      User(=교사) · Post · Comment (순수 데이터)
  config/     설정(Supabase/DB 키) + 학교급/지역/카테고리 상수
  providers/  Supabase JWT 검증 · 세션 쿠키 서명 (stdlib만)
  repo/       Supabase Postgres 데이터 접근 (psycopg)
  service/    auth(소셜 로그인·온보딩) · community · reaction
  ui/         FastAPI 라우트 + 의존성 (소셜 로그인/콜백/온보딩 포함)
  main.py     엔트리포인트 (create_app)
templates/    Jinja2 (모노 + 형광 디자인 시스템, supabase-js로 OAuth)
static/       styles.css
```
