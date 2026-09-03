"""계정 삭제 비즈니스 흐름."""

from __future__ import annotations

from app.config.settings import (
    APPLE_CLIENT_ID,
    APPLE_CLIENT_SECRET,
    APPLE_TOKEN_ENCRYPTION_KEY,
    SUPABASE_ANON_KEY,
    SUPABASE_URL,
)
from app.providers import security
from app.repo import account_deletion, provider_credentials
from app.types.models import User


class AccountDeletionError(ValueError):
    """사용자에게 안내할 수 있는 계정 삭제 실패."""


def delete_current_account(
    user: User, access_token: str, provider_refresh_token: str = ""
) -> None:
    """재검증한 Supabase 사용자만 자신의 계정 전체를 삭제한다."""
    info = security.fetch_supabase_user(access_token, SUPABASE_URL, SUPABASE_ANON_KEY)
    if not info or str(info.get("id")) != user.auth_id:
        raise AccountDeletionError("로그인 정보를 다시 확인해 주세요.")

    provider = str((info.get("app_metadata") or {}).get("provider") or user.provider or "")
    if provider == "apple" and provider_refresh_token:
        try:
            provider_credentials.save_apple_refresh_token(
                user.id, provider_refresh_token, APPLE_TOKEN_ENCRYPTION_KEY
            )
        except ValueError as exc:
            raise AccountDeletionError(str(exc)) from exc

    try:
        # 별도 커밋으로 삭제 상태를 먼저 확정한다. Storage 정책은 이 상태부터 새
        # 업로드를 거부하므로 이미 발급된 JWT가 남아도 고아 파일이 생기지 않는다.
        account_deletion.start_account_deletion(user.id, user.auth_id)
    except account_deletion.AccountDeletionBlocked as exc:
        raise AccountDeletionError(str(exc)) from exc

    paths_by_bucket = account_deletion.owned_storage_paths(user.auth_id)
    for bucket, paths in paths_by_bucket.items():
        if not security.delete_storage_paths(
            access_token, SUPABASE_URL, SUPABASE_ANON_KEY, bucket, paths
        ):
            raise AccountDeletionError(
                "첨부 파일을 삭제하지 못했습니다. 잠시 후 다시 시도해 주세요."
            )

    if provider == "apple":
        try:
            apple_token, already_revoked = provider_credentials.apple_revocation_state(
                user.id, APPLE_TOKEN_ENCRYPTION_KEY
            )
        except ValueError as exc:
            raise AccountDeletionError(str(exc)) from exc
        if not already_revoked:
            if not apple_token:
                raise AccountDeletionError(
                    "안전을 위해 Apple로 다시 로그인한 뒤 계정 삭제를 시도해 주세요."
                )
            if not security.revoke_apple_token(
                apple_token, APPLE_CLIENT_ID, APPLE_CLIENT_SECRET
            ):
                raise AccountDeletionError(
                    "Apple 연결을 해제하지 못했습니다. 잠시 후 다시 시도해 주세요."
                )
            try:
                provider_credentials.mark_apple_token_revoked(user.id)
            except ValueError as exc:
                raise AccountDeletionError(str(exc)) from exc
    try:
        account_deletion.delete_account(user.id, user.auth_id)
    except account_deletion.AccountDeletionBlocked as exc:
        raise AccountDeletionError(str(exc)) from exc
