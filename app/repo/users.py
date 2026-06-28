"""사용자 저장소."""

import sqlite3

from app.repo.database import get_connection
from app.types.models import User


def _to_user(row: sqlite3.Row) -> User:
    return User(
        id=row["id"],
        email=row["email"],
        name=row["name"],
        school_level=row["school_level"],
        region=row["region"],
        subject=row["subject"],
        created_at=row["created_at"],
    )


def create_user(
    email: str, password_hash: str, name: str, school_level: str, region: str, subject: str
) -> User:
    """사용자를 만들고 생성된 행을 돌려준다. 이메일 중복 시 sqlite3.IntegrityError."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO users (email, password_hash, name, school_level, region, subject) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (email, password_hash, name, school_level, region, subject),
        )
        conn.commit()
        return get_user(cur.lastrowid)
    finally:
        conn.close()


def get_user(user_id: int) -> User | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _to_user(row) if row else None
    finally:
        conn.close()


def get_credentials_by_email(email: str) -> tuple[User, str] | None:
    """이메일로 (사용자, password_hash)를 찾는다. 로그인에서만 사용."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not row:
            return None
        return _to_user(row), row["password_hash"]
    finally:
        conn.close()
