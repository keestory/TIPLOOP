"""인증 1차 처리 — Supabase JWT 검증과 자체 세션 쿠키 서명.

표준 라이브러리만 사용한다(추가 의존성 0). Types, Config만 import 가능.
Supabase 액세스 토큰은 HS256(프로젝트 JWT 시크릿)으로 서명되므로 hmac로 검증한다.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time


def _b64url_decode(segment: str) -> bytes:
    pad = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + pad)


def verify_supabase_jwt(token: str, secret: str) -> dict | None:
    """HS256 서명·만료를 검증하고 claims(dict)를 돌려준다. 실패 시 None."""
    if not token or not secret:
        return None
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
    except ValueError:
        return None
    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    try:
        if not hmac.compare_digest(expected, _b64url_decode(sig_b64)):
            return None
        claims = json.loads(_b64url_decode(payload_b64))
    except (ValueError, json.JSONDecodeError):
        return None
    exp = claims.get("exp")
    if isinstance(exp, (int, float)) and time.time() > exp:
        return None
    return claims


def sign_session(teacher_id: int, secret: str, ttl_seconds: int) -> str:
    """teacher_id를 담은 서명 세션 토큰. 'id.exp.sig' 형식."""
    exp = int(time.time()) + ttl_seconds
    msg = f"{teacher_id}.{exp}"
    sig = hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return f"{msg}.{sig}"


def read_session(cookie: str | None, secret: str) -> int | None:
    """세션 토큰을 검증하고 teacher_id를 돌려준다. 무효/만료면 None."""
    if not cookie:
        return None
    try:
        teacher_id, exp, sig = cookie.split(".")
    except (ValueError, AttributeError):
        return None
    msg = f"{teacher_id}.{exp}"
    expected = hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    try:
        if int(exp) < time.time():
            return None
        return int(teacher_id)
    except ValueError:
        return None
