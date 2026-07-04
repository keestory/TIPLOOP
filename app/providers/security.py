"""인증 1차 처리 — Supabase 사용자 조회와 자체 세션 쿠키 서명.

액세스 토큰 검증은 Supabase에 위임한다(/auth/v1/user). 서명 방식(HS256/ES256)에
무관하게 동작하고, 반환된 사용자 정보를 그대로 쓴다. 세션은 자체 서명 쿠키로 유지.
Types, Config만 import 가능.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.error
import urllib.request


def fetch_supabase_user(access_token: str, supabase_url: str, anon_key: str) -> dict | None:
    """액세스 토큰으로 Supabase에 사용자 정보를 조회한다. 무효면 None.

    반환 예: {"id": "...uuid...", "email": "...", "user_metadata": {...}, "app_metadata": {...}}
    """
    if not access_token or not supabase_url or not anon_key:
        return None
    url = supabase_url.rstrip("/") + "/auth/v1/user"
    req = urllib.request.Request(
        url, headers={"Authorization": "Bearer " + access_token, "apikey": anon_key}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status != 200:
                return None
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, ValueError, TimeoutError, OSError):
        return None
    return data if isinstance(data, dict) and data.get("id") else None


def sign_session(member_id: int, secret: str, ttl_seconds: int) -> str:
    """member_id를 담은 서명 세션 토큰. 'id.exp.sig' 형식."""
    exp = int(time.time()) + ttl_seconds
    msg = f"{member_id}.{exp}"
    sig = hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return f"{msg}.{sig}"


def read_session(cookie: str | None, secret: str) -> int | None:
    """세션 토큰을 검증하고 member_id를 돌려준다. 무효/만료면 None."""
    if not cookie:
        return None
    try:
        member_id, exp, sig = cookie.split(".")
    except (ValueError, AttributeError):
        return None
    msg = f"{member_id}.{exp}"
    expected = hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    try:
        if int(exp) < time.time():
            return None
        return int(member_id)
    except ValueError:
        return None
