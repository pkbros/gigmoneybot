-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm; -- Added for fuzzy keyword search

-- ... (tables remain the same)

-- Create a GIST index for fast Trigram similarity searches on skill headings
CREATE INDEX IF NOT EXISTS trgm_idx_listings_skill ON listings USING gist (skill_text gist_trgm_ops);

-- RPC for Lightning Trigram Search (Fuzzy but Fast)
-- Upgraded to search both heading and description
CREATE OR REPLACE FUNCTION keyword_search_trigram(
  query_text TEXT,
  filter_college TEXT,
  match_threshold FLOAT DEFAULT 0.2,
  match_count INT DEFAULT 5
)
RETURNS TABLE (
  id UUID,
  username TEXT,
  display_name TEXT,
  skill_text TEXT,
  description TEXT,
  fee_text TEXT,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    l.id,
    u.username,
    u.display_name,
    l.skill_text,
    l.description,
    l.fee_text,
    GREATEST(
      similarity(l.skill_text, query_text),
      similarity(COALESCE(l.description, ''), query_text)
    )::float AS similarity
  FROM listings l
  JOIN users u ON l.telegram_id = u.telegram_id
  WHERE l.college = filter_college
    AND (
      LOWER(l.skill_text) % LOWER(query_text) -- Case-insensitive Trigram
      OR l.skill_text ILIKE '%' || query_text || '%' -- Substring Heading
      OR l.description ILIKE '%' || query_text || '%' -- Substring Description
    )
  ORDER BY similarity DESC
  LIMIT match_count;
END;
$$;

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
  id UUID, -- Added ID to return
  username TEXT,
  display_name TEXT,
  skill_text TEXT,
  description TEXT,
  fee_text TEXT,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    l.id, -- Added ID to select
    u.username,
    u.display_name,
    l.skill_text,
    l.description,
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
