"""소셜 로그인 제공자 토큰의 암호화 저장과 해제 상태 관리."""

from __future__ import annotations

from app.repo.database import get_connection


def save_apple_refresh_token(member_id: int, token: str, encryption_key: str) -> None:
    """Apple refresh token을 평문으로 남기지 않고 AES-256으로 암호화한다."""
    if not token or len(encryption_key) < 32:
        raise ValueError("Apple 연결 정보를 안전하게 저장할 수 없습니다.")
    with get_connection() as conn:
        updated = conn.execute(
            """
            UPDATE members
               SET provider_refresh_token_ciphertext = extensions.pgp_sym_encrypt(
                       %s,
                       %s,
                       'cipher-algo=aes256,compress-algo=0'
                   ),
                   provider_token_revoked_at = NULL
             WHERE id = %s AND provider = 'apple'
         RETURNING id
            """,
            (token, encryption_key, member_id),
        ).fetchone()
        if updated is None:
            raise ValueError("Apple 계정 정보를 확인하지 못했습니다.")


def apple_revocation_state(member_id: int, encryption_key: str) -> tuple[str | None, bool]:
    """복호화한 refresh token과 이미 연결 해제했는지를 반환한다."""
    if len(encryption_key) < 32:
        raise ValueError("Apple 연결 정보를 안전하게 읽을 수 없습니다.")
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT CASE
                     WHEN provider_refresh_token_ciphertext IS NULL THEN NULL
                     ELSE extensions.pgp_sym_decrypt(
                         provider_refresh_token_ciphertext,
                         %s
                     )
                   END AS refresh_token,
                   provider_token_revoked_at IS NOT NULL AS revoked
              FROM members
             WHERE id = %s AND provider = 'apple'
            """,
            (encryption_key, member_id),
        ).fetchone()
    if row is None:
        raise ValueError("Apple 계정 정보를 확인하지 못했습니다.")
    return row["refresh_token"], bool(row["revoked"])


def mark_apple_token_revoked(member_id: int) -> None:
    """Apple 연결 해제 성공을 기록해 삭제 재시도 시 중복 호출을 피한다."""
    with get_connection() as conn:
        updated = conn.execute(
            """
            UPDATE members
               SET provider_token_revoked_at = COALESCE(provider_token_revoked_at, now())
             WHERE id = %s AND provider = 'apple'
         RETURNING id
            """,
            (member_id,),
        ).fetchone()
        if updated is None:
            raise ValueError("Apple 계정 정보를 확인하지 못했습니다.")
