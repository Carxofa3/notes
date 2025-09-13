-- Unified migration for the entire application
-- This script creates the complete schema from scratch

-- 1. Base Schema from schema.sql
CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    display_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    lesson_id INTEGER NOT NULL,
    order_num INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    display_order INTEGER DEFAULT 0,
    FOREIGN KEY (lesson_id) REFERENCES lessons (id)
);

CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    lesson_id INTEGER NOT NULL,
    unit_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Columns from enhanced features migration
    formatted_content TEXT,
    auto_title TEXT,
    detected_headings TEXT, -- JSON stored as TEXT
    content_schema TEXT, -- JSON stored as TEXT
    formatting_options TEXT, -- JSON stored as TEXT
    color_theme TEXT,
    attached_images TEXT, -- JSON stored as TEXT
    word_count INTEGER DEFAULT 0,
    reading_time INTEGER DEFAULT 0,

    -- Columns from AI features migration
    ai_formatted_content TEXT,
    embedding_vector TEXT, -- JSON array of floats
    embedding_model TEXT DEFAULT 'text-embedding-ada-002',
    last_embedded_at TIMESTAMP,

    FOREIGN KEY (lesson_id) REFERENCES lessons (id),
    FOREIGN KEY (unit_id) REFERENCES units (id)
);

-- 2. Settings table (merged from both migrations)
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL DEFAULT 'default',

    -- Theme and UI customization (from enhanced)
    primary_color TEXT DEFAULT '#4299e1',
    color_palette TEXT, -- JSON stored as TEXT
    dark_mode BOOLEAN DEFAULT FALSE,
    custom_css TEXT,

    -- Editor preferences (from enhanced)
    editor_font_family TEXT DEFAULT 'Inter, system-ui, sans-serif',
    editor_font_size INTEGER DEFAULT 16,
    editor_line_height TEXT DEFAULT '1.6',
    auto_save_interval INTEGER DEFAULT 30,
    spell_check BOOLEAN DEFAULT TRUE,

    -- Content preferences (from enhanced)
    auto_detect_titles BOOLEAN DEFAULT TRUE,
    auto_generate_schema BOOLEAN DEFAULT TRUE,
    default_note_color TEXT DEFAULT '#f7fafc',

    -- Advanced settings (from enhanced)
    export_format TEXT DEFAULT 'markdown',
    image_quality TEXT DEFAULT 'medium',
    max_image_size INTEGER DEFAULT 5,

    -- AI settings (from AI migration)
    ai_base_url TEXT DEFAULT 'https://api.openai.com/v1',
    ai_api_key TEXT,
    ai_model TEXT DEFAULT 'gpt-3.5-turbo',
    ai_embedding_model TEXT DEFAULT 'text-embedding-ada-002',
    ai_enabled BOOLEAN DEFAULT FALSE,
    ai_auto_format BOOLEAN DEFAULT FALSE,
    search_enabled BOOLEAN DEFAULT TRUE,
    max_search_results INTEGER DEFAULT 10,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. AI-specific tables
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

CREATE TABLE IF NOT EXISTS search_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_text TEXT NOT NULL,
    query_hash TEXT UNIQUE NOT NULL,
    results TEXT NOT NULL, -- JSON array of results
    embedding_vector TEXT, -- Embedding of the query
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

-- 4. Indexes for performance
CREATE INDEX IF NOT EXISTS idx_settings_user_id ON settings(user_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_note_id ON embeddings(note_id);
CREATE INDEX IF NOT EXISTS idx_search_cache_hash ON search_cache(query_hash);
CREATE INDEX IF NOT EXISTS idx_search_cache_expires ON search_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_lessons_order ON lessons(display_order);
CREATE INDEX IF NOT EXISTS idx_units_order ON units(display_order);
CREATE INDEX IF NOT EXISTS idx_notes_embedding_model ON notes(embedding_model);

-- 5. Initial data
INSERT OR IGNORE INTO settings (user_id) VALUES ('default');

-- Note: The logic to update display_order for existing data is not included here
-- as this script is intended for creating a fresh database.
-- A separate data migration script would be needed for existing installations.
