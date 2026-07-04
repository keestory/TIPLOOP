"""DB 연결 진단 — 무엇이 틀렸는지 사람이 읽을 수 있게 알려준다.

    python3 scripts/check_db.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config.settings import DATABASE_URL

_PLACEHOLDERS = ("여기", "실제DB비번", "YOUR-PASSWORD", "새비번", "비번", "PASSWORD")


def main() -> int:
    if not DATABASE_URL:
        print("❌ DATABASE_URL이 비어 있어요. .env를 만들었는지 확인하세요 (.env.example 참고).")
        return 1

    masked = re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", DATABASE_URL)
    print("DATABASE_URL:", masked)

    for ph in _PLACEHOLDERS:
        if ph in DATABASE_URL:
            print(f"❌ 비밀번호 자리에 '{ph}' 가 남아 있어요 → 실제 DB 비밀번호로 바꾸세요.")
            return 1

    from app.repo.database import init_db

    try:
        init_db()
    except Exception as exc:  # noqa: BLE001 - 진단 목적
        msg = str(exc)
        first = msg.splitlines()[0] if msg else msg
        if "password authentication failed" in msg:
            print("❌ 비밀번호가 틀렸어요.")
            print("   → Supabase → Settings → Database → Reset database password (영문+숫자 권장)")
            print("   → 새 비번을 .env의 DATABASE_URL에 넣으세요.")
        elif "Tenant or user not found" in msg:
            print("❌ 사용자명 형식 문제 — user는 'postgres.aqpmvlcgtopfufdtafoi' 여야 해요(Session pooler).")
        elif "could not translate host name" in msg or "Name or service not known" in msg:
            print("❌ 호스트명 오타 — pooler 주소를 다시 확인하세요.")
        elif "timeout" in msg.lower() or "unreachable" in msg.lower():
            print("❌ 네트워크 도달 실패 — Session pooler(IPv4) 문자열이 맞는지 확인하세요.")
        else:
            print("❌ 연결 실패:", first)
        return 1

    print("✅ DB 연결 + 스키마 생성 완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
