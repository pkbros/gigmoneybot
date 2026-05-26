-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Table: users
CREATE TABLE IF NOT EXISTS users (
  telegram_id  BIGINT PRIMARY KEY,
  username     TEXT,
  display_name TEXT,
  college      TEXT, -- Added college column
  created_at   TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Table: listings
CREATE TABLE IF NOT EXISTS listings (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  telegram_id  BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
  skill_text   TEXT NOT NULL,
  fee_text     TEXT NOT NULL, -- Changed from fee_inr INTEGER to fee_text TEXT
  embedding    vector(768),
  college      TEXT,
  created_at   TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Table: search_logs
CREATE TABLE IF NOT EXISTS search_logs (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  telegram_id  BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
  username     TEXT,
  query        TEXT NOT NULL,
  college      TEXT,
  created_at   TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- RPC Function for semantic search with college filtering
CREATE OR REPLACE FUNCTION match_listings (
  query_embedding vector(768),
  match_threshold float,
  match_count int,
  filter_college TEXT
)
RETURNS TABLE (
  username TEXT,
  display_name TEXT,
  skill_text TEXT,
  description TEXT, -- Added description to return
  fee_text TEXT,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    u.username,
    u.display_name,
    l.skill_text,
    l.description, -- Added description to select
    l.fee_text,
    1 - (l.embedding <=> query_embedding) AS similarity
  FROM listings l
  JOIN users u ON l.telegram_id = u.telegram_id
  WHERE l.college = filter_college
    AND 1 - (l.embedding <=> query_embedding) > match_threshold
  ORDER BY l.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
