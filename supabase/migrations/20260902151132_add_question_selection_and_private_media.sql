ALTER TABLE posts
    ADD COLUMN IF NOT EXISTS analysis_mode TEXT,
    ADD COLUMN IF NOT EXISTS analysis_template_version TEXT,
    ADD COLUMN IF NOT EXISTS selected_question_ids TEXT[],
    ADD COLUMN IF NOT EXISTS attachments JSONB;

ALTER TABLE posts DROP CONSTRAINT IF EXISTS posts_analysis_mode_check;
ALTER TABLE posts ADD CONSTRAINT posts_analysis_mode_check
    CHECK (analysis_mode IS NULL OR analysis_mode IN ('quick', 'focus', 'full'));

ALTER TABLE posts DROP CONSTRAINT IF EXISTS posts_attachments_array_check;
ALTER TABLE posts ADD CONSTRAINT posts_attachments_array_check
    CHECK (
        attachments IS NULL OR (
            jsonb_typeof(attachments) = 'array'
            AND jsonb_array_length(attachments) <= 6
        )
    );

INSERT INTO storage.buckets (
    id, name, public, file_size_limit, allowed_mime_types
)
VALUES (
    'tiploop-research-images', 'tiploop-research-images', FALSE, 10485760,
    ARRAY['image/jpeg', 'image/png', 'image/webp', 'image/gif']
)
ON CONFLICT (id) DO UPDATE SET
    public = EXCLUDED.public,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;

INSERT INTO storage.buckets (
    id, name, public, file_size_limit, allowed_mime_types
)
VALUES (
    'tiploop-research-videos', 'tiploop-research-videos', FALSE, 52428800,
    ARRAY['video/mp4', 'video/webm', 'video/quicktime']
)
ON CONFLICT (id) DO UPDATE SET
    public = EXCLUDED.public,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;

DROP POLICY IF EXISTS "research_media_insert_own" ON storage.objects;
CREATE POLICY "research_media_insert_own"
ON storage.objects FOR INSERT TO authenticated
WITH CHECK (
    bucket_id IN ('tiploop-research-images', 'tiploop-research-videos')
    AND (storage.foldername(name))[1] = (SELECT auth.uid()::text)
    AND (storage.foldername(name))[2] = 'drafts'
    AND cardinality(storage.foldername(name)) = 3
    AND (
        (bucket_id = 'tiploop-research-images' AND storage.extension(name) IN ('jpg', 'png', 'webp', 'gif'))
        OR
        (bucket_id = 'tiploop-research-videos' AND storage.extension(name) IN ('mp4', 'webm', 'mov'))
    )
);

DROP POLICY IF EXISTS "research_media_select_own" ON storage.objects;
CREATE POLICY "research_media_select_own"
ON storage.objects FOR SELECT TO authenticated
USING (
    bucket_id IN ('tiploop-research-images', 'tiploop-research-videos')
    AND (storage.foldername(name))[1] = (SELECT auth.uid()::text)
    AND owner_id = (SELECT auth.uid()::text)
);

DROP POLICY IF EXISTS "research_media_delete_own" ON storage.objects;
CREATE POLICY "research_media_delete_own"
ON storage.objects FOR DELETE TO authenticated
USING (
    bucket_id IN ('tiploop-research-images', 'tiploop-research-videos')
    AND (storage.foldername(name))[1] = (SELECT auth.uid()::text)
    AND owner_id = (SELECT auth.uid()::text)
);
