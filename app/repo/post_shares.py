"""연구 노트의 취소 가능한 secret-link 공유 저장소."""

from __future__ import annotations

from psycopg.types.json import Jsonb

from app.repo.database import get_connection


def replace_active(
    post_id: int,
    author_id: int,
    token_hash: str,
    include_media: bool,
    snapshot: dict,
    media_token_hashes: tuple[str, ...],
) -> bool:
    """소유자의 기존 활성 링크를 끄고 새 링크를 원자적으로 만든다."""
    with get_connection() as conn:
        with conn.transaction():
            owned = conn.execute(
                """
                SELECT id FROM posts
                 WHERE id = %s AND author_id = %s AND category = 'reference'
                 FOR UPDATE
                """,
                (post_id, author_id),
            ).fetchone()
            if owned is None:
                return False
            conn.execute(
                """
                UPDATE post_shares s
                   SET revoked_at = now()
                  FROM posts p
                 WHERE p.id = s.post_id
                   AND s.post_id = %s
                   AND p.author_id = %s
                   AND p.category = 'reference'
                   AND s.revoked_at IS NULL
                """,
                (post_id, author_id),
            )
            row = conn.execute(
                """
                INSERT INTO post_shares (
                    post_id, token_hash, include_media, snapshot, expires_at
                )
                VALUES (%s, %s, %s, %s, now() + interval '7 days')
                RETURNING id
                """,
                (post_id, token_hash, include_media, Jsonb(snapshot)),
            ).fetchone()
            if row is not None and media_token_hashes:
                conn.executemany(
                    """
                    INSERT INTO post_share_media_grants (
                        share_id, attachment_index, token_hash
                    ) VALUES (%s, %s, %s)
                    """,
                    [
                        (row["id"], index, media_hash)
                        for index, media_hash in enumerate(media_token_hashes)
                    ],
                )
    return row is not None


def active_for_owner(post_id: int, author_id: int) -> dict | None:
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT s.include_media,
                   to_char(s.created_at, 'YYYY-MM-DD HH24:MI') AS created_at,
                   to_char(s.expires_at, 'YYYY-MM-DD HH24:MI') AS expires_at
              FROM post_shares s
              JOIN posts p ON p.id = s.post_id
             WHERE s.post_id = %s
               AND p.author_id = %s
               AND p.category = 'reference'
               AND s.revoked_at IS NULL
               AND s.expires_at > now()
            """,
            (post_id, author_id),
        ).fetchone()


def active_for_hash(token_hash: str) -> dict | None:
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT id, post_id, include_media, snapshot
             FROM post_shares
             WHERE token_hash = %s
               AND revoked_at IS NULL
               AND expires_at > now()
            """,
            (token_hash,),
        ).fetchone()


def revoke_active(post_id: int, author_id: int) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            """
            UPDATE post_shares s
               SET revoked_at = now()
              FROM posts p
             WHERE p.id = s.post_id
               AND s.post_id = %s
               AND p.author_id = %s
               AND p.category = 'reference'
               AND s.revoked_at IS NULL
            RETURNING s.id
            """,
            (post_id, author_id),
        ).fetchone()
    return row is not None
