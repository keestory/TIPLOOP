"""세션 저장소 — 토큰 ↔ 사용자."""

from app.repo.database import get_connection


def create_session(token: str, user_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, user_id))
        conn.commit()
    finally:
        conn.close()


def get_user_id(token: str) -> int | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT user_id FROM sessions WHERE token = ?", (token,)).fetchone()
        return row["user_id"] if row else None
    finally:
        conn.close()


def delete_session(token: str) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
    finally:
        conn.close()
