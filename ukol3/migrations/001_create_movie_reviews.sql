CREATE TABLE IF NOT EXISTS public.movie_reviews (
  id BIGSERIAL PRIMARY KEY,
  movie_name VARCHAR(255) NOT NULL UNIQUE,
  rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 10),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO public.movie_reviews (movie_name, rating)
VALUES ('Inception', 9)
ON CONFLICT (movie_name)
DO UPDATE SET rating = EXCLUDED.rating, updated_at = NOW();
