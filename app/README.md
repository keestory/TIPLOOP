# 이음(Ieum) — 선생님 오픈 커뮤니티

유치원·초·중·고 선생님들이 **닫힌 단톡방을 넘어** 정보·세미나·고민을 나누는 열린 커뮤니티.
이 저장소의 하네스 워크플로(PM → Designer → Planner → Coder → Tester → Reviewer)를 따라 만든 첫 앱입니다.

- 제품 사양: [`docs/product-specs/ieum-community.md`](../docs/product-specs/ieum-community.md)
- 설계·디자인 시스템: [`docs/design-docs/ieum-design.md`](../docs/design-docs/ieum-design.md)
- 실행 계획: [`docs/exec-plans/active/ieum-mvp.md`](../docs/exec-plans/active/ieum-mvp.md)

## 기능 (MVP)

- 교사 가입/로그인 (이메일·학교급·지역·담당)
- 글쓰기 — `정보공유` · `세미나` · `고민나눔` 세 카테고리 통합
- 세미나 글: 일시·장소·온라인 링크
- 피드 필터: 카테고리 · 학교급 · 지역
- 누구나 읽기 가능(오픈 원칙), 로그인 시 댓글 작성
- 교사 프로필 + 작성 글 모아보기

## 실행

```bash
pip install -r app/requirements.txt
uvicorn app.main:app --reload
# http://127.0.0.1:8000
```

DB는 SQLite(`ieum.db`), 첫 기동 시 자동 생성됩니다. 위치는 `IEUM_DB_PATH`,
세션 시크릿은 `IEUM_SECRET` 환경 변수로 바꿀 수 있습니다.

## 테스트 / 린트

```bash
python3 -m pytest tests/
python3 linters/architecture_linter.py .   # 레이어 의존성
```

## 구조 (레이어드 도메인 아키텍처)

의존성은 위→아래로만 흐릅니다 (`architecture_linter.py`로 강제).

```
app/
  types/      User · Post · Comment (순수 데이터)
  config/     설정 + 학교급/지역/카테고리 상수
  providers/  비밀번호 해시 · 세션 토큰 (stdlib만)
  repo/       SQLite 데이터 접근
  service/    auth · community 비즈니스 로직
  ui/         FastAPI 라우트 + 의존성
  main.py     엔트리포인트 (create_app)
templates/    Jinja2 (종이·먹·황토 디자인 시스템)
static/       styles.css
```
