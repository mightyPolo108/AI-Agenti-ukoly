-- Align movie_reviews with application expectations.
BEGIN;

-- Add timestamp for tracking updates.
ALTER TABLE public.movie_reviews
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

UPDATE public.movie_reviews
SET updated_at = NOW()
WHERE updated_at IS NULL;

-- Enforce 1-10 rating range.
ALTER TABLE public.movie_reviews
    DROP CONSTRAINT IF EXISTS movie_reviews_rating_check;

ALTER TABLE public.movie_reviews
    ADD CONSTRAINT movie_reviews_rating_check CHECK (rating >= 1 AND rating <= 10);

-- Upsert relies on uniqueness by movie name (not by rating).
ALTER TABLE public.movie_reviews
    DROP CONSTRAINT IF EXISTS movie_reviews_movie_name_rating_key;

ALTER TABLE public.movie_reviews
    ADD CONSTRAINT movie_reviews_movie_name_key UNIQUE (movie_name);

COMMIT;
