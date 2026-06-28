# 실행 계획 — 이음 MVP

> Planner 에이전트 워크플로 · 레이어드 도메인 아키텍처(ARCHITECTURE.md) 준수

## 스택 (추천대로 선택)

- **백엔드**: FastAPI (이 저장소가 Python 기반 → 일관성)
- **DB**: SQLite (stdlib `sqlite3`, 의존성 0) — MVP에 충분
- **뷰**: Jinja2 서버 렌더링 (글 중심 제품 → SPA 불필요, 빠르고 가벼움)
- **인증**: stdlib `hashlib` PBKDF2 + 서버 세션(쿠키 토큰)
- 런타임 의존성 최소화: `fastapi`, `uvicorn`, `jinja2`, `python-multipart`

## 디렉토리 — 레이어 매핑

의존성은 위→아래로만 (`architecture_linter.py`로 강제):

```
app/
  main.py              # 엔트리포인트(레이어 외) → create_app() 호출
  types/models.py      # User, Post, Comment 데이터구조 (순수)
  config/settings.py   # DB 경로, 학교급/지역/카테고리 상수, 세션 설정
  providers/security.py# 비밀번호 해시·검증, 세션 토큰 생성
  repo/database.py     # 커넥션 + 스키마 init
  repo/users.py        # 사용자 CRUD
  repo/sessions.py     # 세션 CRUD
  repo/posts.py        # 글 CRUD + 필터 조회
  repo/comments.py     # 댓글 CRUD
  service/auth_service.py      # 가입·로그인·로그아웃·현재 사용자
  service/community_service.py # 글 작성·목록·상세·댓글·프로필
  ui/deps.py           # current_user 의존성
  ui/app_factory.py    # FastAPI 조립, static/templates 마운트
  ui/routes_auth.py    # /register /login /logout
  ui/routes_community.py# / /posts /posts/new /profile
templates/             # base, index, post_detail, post_new, login, register, profile
static/styles.css      # 디자인 시스템 구현
tests/                 # service 단위 + 라우트 스모크
```

각 파일 300줄 이하 유지.

## 데이터 모델

- **users**: id, email(unique), password_hash, name, school_level, region, subject, created_at
- **sessions**: token(pk), user_id, created_at
- **posts**: id, author_id, category(info|seminar|support), title, body, created_at,
  event_at, location, online_url (세미나 전용, nullable)
- **comments**: id, post_id, author_id, body, created_at

## 단계

1. types → config → providers (기반)
2. repo: database + 4개 저장소
3. service: auth + community
4. ui: deps + app_factory + 라우트
5. templates + static
6. tests + 린터 통과 확인
7. 실행 검증(uvicorn 기동, 핵심 플로우 수동 확인)

## 검증 게이트

- `python3 linters/architecture_linter.py .` → 위반 없음
- `python3 -m pytest tests/` → 통과
- 앱 기동 후: 가입 → 글쓰기(세미나 포함) → 필터 → 댓글 → 프로필 동작
