"""회원 계정과 연결된 TIPLOOP 데이터를 한 트랜잭션에서 삭제한다."""

from __future__ import annotations

from app.repo.database import get_connection


class AccountDeletionBlocked(RuntimeError):
    """Storage 잔존 객체 등으로 안전한 계정 삭제를 완료할 수 없음."""


def start_account_deletion(member_id: int, auth_id: str) -> None:
    """먼저 삭제 상태를 확정해 기존 JWT의 새 Storage 업로드를 차단한다."""
    with get_connection() as conn:
        row = conn.execute(
            """
            UPDATE members
               SET deletion_started_at = COALESCE(deletion_started_at, now())
             WHERE id = %s AND auth_id = %s
         RETURNING id
            """,
            (member_id, auth_id),
        ).fetchone()
        if row is None:
            raise AccountDeletionBlocked("계정 정보를 다시 확인해 주세요.")


def owned_storage_paths(auth_id: str) -> dict[str, list[str]]:
    """Supabase Auth 사용자가 소유한 Storage 객체를 버킷별로 돌려준다."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT bucket_id, name
              FROM storage.objects
             WHERE owner_id::text = %s
             ORDER BY bucket_id, name
            """,
            (auth_id,),
        ).fetchall()
    grouped: dict[str, list[str]] = {}
    for row in rows:
        grouped.setdefault(row["bucket_id"], []).append(row["name"])
    return grouped


def delete_account(member_id: int, auth_id: str) -> None:
    """앱 데이터와 Supabase Auth 사용자를 원자적으로 제거한다.

    삭제 상태가 먼저 저장되어 새 업로드가 막힌 뒤 Storage를 정리한다. 객체가
    하나라도 남으면 앱 데이터는 건드리지 않고 중단하며 같은 요청을 재시도할 수 있다.
    """
    with get_connection() as conn:
        with conn.transaction():
            auth_row = conn.execute(
                "SELECT id FROM auth.users WHERE id = %s::uuid FOR UPDATE",
                (auth_id,),
            ).fetchone()
            member_row = conn.execute(
                "SELECT id FROM members WHERE id = %s AND auth_id = %s FOR UPDATE",
                (member_id, auth_id),
            ).fetchone()
            if auth_row is None or member_row is None:
                raise AccountDeletionBlocked("계정 정보를 다시 확인해 주세요.")

            remaining = conn.execute(
                "SELECT count(*) AS count FROM storage.objects WHERE owner_id::text = %s",
                (auth_id,),
            ).fetchone()["count"]
            if remaining:
                raise AccountDeletionBlocked(
                    "첨부 파일 삭제를 완료하지 못했습니다. 잠시 후 다시 시도해 주세요."
                )

            post_rows = conn.execute(
                "SELECT id FROM posts WHERE author_id = %s", (member_id,)
            ).fetchall()
            post_ids = [row["id"] for row in post_rows]
            crew_rows = conn.execute(
                "SELECT id FROM crews WHERE created_by = %s", (member_id,)
            ).fetchall()
            crew_ids = [row["id"] for row in crew_rows]

            comment_rows = conn.execute(
                """
                WITH RECURSIVE doomed AS (
                    SELECT id FROM comments
                     WHERE author_id = %s OR post_id = ANY(%s::bigint[])
                    UNION
                    SELECT child.id
                      FROM comments child
                      JOIN doomed parent ON child.parent_id = parent.id
                )
                SELECT id FROM doomed
                """,
                (member_id, post_ids),
            ).fetchall()
            comment_ids = [row["id"] for row in comment_rows]

            conn.execute(
                "DELETE FROM comment_reactions WHERE user_id = %s OR comment_id = ANY(%s::bigint[])",
                (member_id, comment_ids),
            )
            conn.execute(
                "DELETE FROM post_reactions WHERE user_id = %s OR post_id = ANY(%s::bigint[])",
                (member_id, post_ids),
            )
            conn.execute(
                "DELETE FROM post_helpful WHERE user_id = %s OR post_id = ANY(%s::bigint[])",
                (member_id, post_ids),
            )
            conn.execute(
                "DELETE FROM media_comments WHERE author_id = %s OR post_id = ANY(%s::bigint[])",
                (member_id, post_ids),
            )
            conn.execute(
                "DELETE FROM reviews WHERE author_id = %s OR post_id = ANY(%s::bigint[])",
                (member_id, post_ids),
            )
            conn.execute(
                """
                DELETE FROM notifications
                 WHERE user_id = %s OR actor_id = %s
                    OR post_id = ANY(%s::bigint[])
                    OR crew_id = ANY(%s::bigint[])
                """,
                (member_id, member_id, post_ids, crew_ids),
            )
            conn.execute(
                "DELETE FROM crew_entries WHERE author_id = %s OR crew_id = ANY(%s::bigint[])",
                (member_id, crew_ids),
            )
            conn.execute(
                "DELETE FROM crew_members WHERE member_id = %s OR crew_id = ANY(%s::bigint[])",
                (member_id, crew_ids),
            )
            conn.execute("DELETE FROM crews WHERE id = ANY(%s::bigint[])", (crew_ids,))
            conn.execute(
                "DELETE FROM follows WHERE follower_id = %s OR followee_id = %s",
                (member_id, member_id),
            )
            conn.execute("DELETE FROM comments WHERE id = ANY(%s::bigint[])", (comment_ids,))
            conn.execute("DELETE FROM posts WHERE id = ANY(%s::bigint[])", (post_ids,))
            conn.execute("DELETE FROM members WHERE id = %s", (member_id,))
            deleted = conn.execute(
                "DELETE FROM auth.users WHERE id = %s::uuid RETURNING id", (auth_id,)
            ).fetchone()
            if deleted is None:
                raise AccountDeletionBlocked("인증 계정을 삭제하지 못했습니다.")
