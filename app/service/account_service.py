"""계정 삭제 비즈니스 흐름."""

from __future__ import annotations

from app.config.settings import SUPABASE_ANON_KEY, SUPABASE_URL
from app.providers import security
from app.repo import account_deletion
from app.types.models import User


class AccountDeletionError(ValueError):
    """사용자에게 안내할 수 있는 계정 삭제 실패."""


def delete_current_account(user: User, access_token: str) -> None:
    """재검증한 Supabase 사용자만 자신의 계정 전체를 삭제한다."""
    info = security.fetch_supabase_user(access_token, SUPABASE_URL, SUPABASE_ANON_KEY)
    if not info or str(info.get("id")) != user.auth_id:
        raise AccountDeletionError("로그인 정보를 다시 확인해 주세요.")

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
    try:
        account_deletion.delete_account(user.id, user.auth_id)
    except account_deletion.AccountDeletionBlocked as exc:
        raise AccountDeletionError(str(exc)) from exc
