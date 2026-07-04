#!/usr/bin/env bash
# 이음 로컬 실행 — venv 준비 + .env 로드 + DB 점검 + 서버.
# 한 번만: cp .env.example .env  후 .env의 DATABASE_URL 비밀번호만 채우면 됨.
#
#   bash scripts/dev.sh
set -e
cd "$(dirname "$0")/.."

if [ ! -d .venv ]; then
  echo "· .venv 생성"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "· 의존성 확인/설치"
pip install -q -r app/requirements.txt

if [ ! -f .env ]; then
  echo "❌ .env 파일이 없습니다. 먼저 만들어 주세요:"
  echo "     cp .env.example .env   그리고 DATABASE_URL 비밀번호를 채우세요."
  exit 1
fi

echo "· DB 점검"
python3 scripts/check_db.py || {
  echo "→ DB 점검 실패. 위 메시지대로 .env를 고친 뒤 다시 실행하세요."
  exit 1
}

echo "· 서버 시작 → http://127.0.0.1:8000"
exec uvicorn app.main:app --reload
