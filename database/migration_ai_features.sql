-- Migration for AI features and semantic search
-- Run this after the enhanced features migration

-- Add order columns to existing tables
ALTER TABLE lessons ADD COLUMN display_order INTEGER DEFAULT 0;
ALTER TABLE units ADD COLUMN display_order INTEGER DEFAULT 0;

-- Add AI-related columns to notes
ALTER TABLE notes ADD COLUMN ai_formatted_content TEXT;
ALTER TABLE notes ADD COLUMN embedding_vector TEXT; -- JSON array of floats
ALTER TABLE notes ADD COLUMN embedding_model TEXT DEFAULT 'text-embedding-ada-002';
ALTER TABLE notes ADD COLUMN last_embedded_at TIMESTAMP;

-- Create embeddings table for phrase-level embeddings
CREATE TABLE IF NOT EXISTS embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id INTEGER NOT NULL,
    phrase_text TEXT NOT NULL,
    phrase_start INTEGER NOT NULL, -- Start position in note content
    phrase_end INTEGER NOT NULL,   -- End position in note content
    embedding_vector TEXT NOT NULL, -- JSON array of floats
    embedding_model TEXT DEFAULT 'text-embedding-ada-002',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (note_id) REFERENCES notes (id) ON DELETE CASCADE
);

-- Create search cache table for performance
CREATE TABLE IF NOT EXISTS search_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_text TEXT NOT NULL,
    query_hash TEXT UNIQUE NOT NULL,
    results TEXT NOT NULL, -- JSON array of results
    embedding_vector TEXT, -- Embedding of the query
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

-- Add AI settings to settings table
ALTER TABLE settings ADD COLUMN ai_base_url TEXT DEFAULT 'https://api.openai.com/v1';
ALTER TABLE settings ADD COLUMN ai_api_key TEXT;
ALTER TABLE settings ADD COLUMN ai_model TEXT DEFAULT 'gpt-3.5-turbo';
ALTER TABLE settings ADD COLUMN ai_embedding_model TEXT DEFAULT 'text-embedding-ada-002';
ALTER TABLE settings ADD COLUMN ai_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE settings ADD COLUMN ai_auto_format BOOLEAN DEFAULT FALSE;
ALTER TABLE settings ADD COLUMN search_enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE settings ADD COLUMN max_search_results INTEGER DEFAULT 10;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_embeddings_note_id ON embeddings(note_id);
CREATE INDEX IF NOT EXISTS idx_search_cache_hash ON search_cache(query_hash);
CREATE INDEX IF NOT EXISTS idx_search_cache_expires ON search_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_lessons_order ON lessons(display_order);
CREATE INDEX IF NOT EXISTS idx_units_order ON units(display_order);
CREATE INDEX IF NOT EXISTS idx_notes_embedding_model ON notes(embedding_model);

-- Update display_order for existing lessons and units
UPDATE lessons SET display_order = id WHERE display_order = 0;
UPDATE units SET display_order = id WHERE display_order = 0;
