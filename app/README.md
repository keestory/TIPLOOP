# 티핑(Tipping) — 커머스·IT 실무자 커뮤니티

일하며 얻은 **팁·노하우**와 다른 서비스를 뜯어본 **레퍼런스**를 기록하고, 혼자만의 메모가
아니라 커뮤니티로 나누는 서비스. 이 저장소의 하네스 워크플로(PM → Designer → Planner →
Coder → Tester)를 따라 만들었습니다.

- 제품 사양: [`docs/product-specs/tipping-community.md`](../docs/product-specs/tipping-community.md)
- 설계·디자인 시스템: [`docs/design-docs/ieum-design.md`](../docs/design-docs/ieum-design.md)
- **Supabase 셋업: [`docs/SUPABASE_SETUP.md`](../docs/SUPABASE_SETUP.md)**

## 기능

- **구글·카카오 소셜 로그인** (Supabase Auth) — 이메일/비밀번호 없음
- 온보딩 — 소셜이 주지 않는 **직군·연차·업종**만 추가로 받음
- 글쓰기 — `팁` · `레퍼런스` · `질문` · `회고` 네 카테고리 (레퍼런스는 참고 링크 첨부)
- 피드 정렬(최신·공감·화제) + 필터(카테고리·직군·업종)
- 공감(♥)·댓글·답글 스레드, 누구나 읽기 가능(오픈 원칙)
- 회원 프로필 + 받은 공감(카르마)

## 실행 (로컬)

데이터·인증 모두 **Supabase**. [`docs/SUPABASE_SETUP.md`](../docs/SUPABASE_SETUP.md)대로
키를 받은 뒤, `.env`를 만들고 한 명령으로 실행:

```bash
git clone https://github.com/keestory/ft.git FT && cd FT
git checkout claude/harness-engineering-agent-acwvo2
cp .env.example .env      # .env 열어서 DATABASE_URL 비밀번호 + JWT Secret 채우기
bash scripts/dev.sh       # venv + 의존성 + DB 점검 + 서버
# http://127.0.0.1:8000
```

`scripts/dev.sh`가 가상환경 준비 → 의존성 설치 → `scripts/check_db.py`로 DB를 점검하고
(무엇이 틀렸는지 한국어로 안내) → uvicorn을 띄웁니다. 데모 데이터는 `python3 scripts/seed_demo.py`.

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
  types/      User(=회원) · Post · Comment (순수 데이터)
  config/     설정(브랜드/Supabase/DB 키) + 직군/연차/업종/카테고리 상수
  providers/  Supabase JWT 검증 · 세션 쿠키 서명 (stdlib만)
  repo/       Supabase Postgres 데이터 접근 (psycopg)
  service/    auth(소셜 로그인·온보딩) · community · reaction
  ui/         FastAPI 라우트 + 의존성 (소셜 로그인/콜백/온보딩 포함)
  main.py     엔트리포인트 (create_app)
templates/    Jinja2 (모노 + 형광 디자인 시스템, supabase-js로 OAuth)
static/       styles.css
```
