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
import urllib.parse
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


def delete_storage_paths(
    access_token: str,
    supabase_url: str,
    publishable_key: str,
    bucket: str,
    paths: list[str],
) -> bool:
    """현재 사용자의 JWT로 본인 소유 Storage 객체를 삭제한다.

    브라우저가 먼저 파일을 지우지만, 서버에서도 같은 사용자 토큰으로 한 번 더
    실행해 네트워크 중단 뒤 남은 객체를 정리한다. 관리자 키는 사용하지 않는다.
    """
    if not paths:
        return True
    url = f"{supabase_url.rstrip('/')}/storage/v1/object/{bucket}"
    # Supabase Storage remove API는 요청당 최대 1,000개다.
    for start in range(0, len(paths), 1000):
        body = json.dumps({"prefixes": paths[start:start + 1000]}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            method="DELETE",
            headers={
                "Authorization": "Bearer " + access_token,
                "apikey": publishable_key,
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                if not 200 <= resp.status < 300:
                    return False
        except (urllib.error.URLError, TimeoutError, OSError):
            return False
    return True


def revoke_apple_token(token: str, client_id: str, client_secret: str) -> bool:
    """Apple OAuth refresh token을 공식 revoke endpoint에서 폐기한다."""
    if not token or not client_id or not client_secret:
        return False
    body = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "token": token,
            "token_type_hint": "refresh_token",
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://appleid.apple.com/auth/revoke",
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


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
