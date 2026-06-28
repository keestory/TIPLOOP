"""비밀번호 해시·검증과 세션 토큰 생성.

표준 라이브러리만 사용한다(추가 의존성 0). Types, Config만 import 가능.
"""

from __future__ import annotations


import hashlib
import hmac
import secrets

from app.config.settings import PBKDF2_ITERATIONS


def hash_password(password: str) -> str:
    """PBKDF2-HMAC-SHA256으로 해시. 'salt$hash' 형식의 hex 문자열을 돌려준다."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """저장된 'salt$hash'와 비교. 타이밍 안전 비교를 쓴다."""
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        salt = bytes.fromhex(salt_hex)
    except (ValueError, AttributeError):
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return hmac.compare_digest(digest.hex(), digest_hex)


def generate_token() -> str:
    """세션 토큰(URL 안전 난수)."""
    return secrets.token_urlsafe(32)
