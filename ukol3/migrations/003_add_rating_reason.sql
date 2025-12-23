-- Add textual rating reason from user.
BEGIN;

ALTER TABLE public.movie_reviews
    ADD COLUMN IF NOT EXISTS rating_reason TEXT NOT NULL DEFAULT '';

-- Ensure existing rows have a value (for cases where column existed without default).
UPDATE public.movie_reviews
SET rating_reason = COALESCE(rating_reason, '');

COMMIT;
