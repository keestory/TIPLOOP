-- 계정 삭제를 시작한 사용자의 기존 JWT가 새 Storage 객체를 만들지 못하게 한다.
ALTER TABLE public.members
    ADD COLUMN IF NOT EXISTS deletion_started_at TIMESTAMPTZ;

CREATE OR REPLACE FUNCTION public.tiploop_account_accepts_storage()
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, auth
AS $$
DECLARE
    account_is_active BOOLEAN;
BEGIN
    SELECT deletion_started_at IS NULL
      INTO account_is_active
      FROM public.members
     WHERE auth_id = auth.uid()::text
       FOR SHARE;
    RETURN COALESCE(account_is_active, FALSE);
END;
$$;

REVOKE ALL ON FUNCTION public.tiploop_account_accepts_storage() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.tiploop_account_accepts_storage() TO authenticated;

DROP POLICY IF EXISTS "research_media_insert_own" ON storage.objects;
CREATE POLICY "research_media_insert_own"
ON storage.objects FOR INSERT TO authenticated
WITH CHECK (
    bucket_id IN ('tiploop-research-images', 'tiploop-research-videos')
    AND public.tiploop_account_accepts_storage()
    AND (storage.foldername(name))[1] = (SELECT auth.uid()::text)
    AND (storage.foldername(name))[2] = 'drafts'
    AND cardinality(storage.foldername(name)) = 3
    AND (
        (bucket_id = 'tiploop-research-images' AND storage.extension(name) IN ('jpg', 'png', 'webp', 'gif'))
        OR
        (bucket_id = 'tiploop-research-videos' AND storage.extension(name) IN ('mp4', 'webm', 'mov'))
    )
);
