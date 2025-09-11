-- Migration to add enhanced features to the notes application
-- Run this after the initial schema has been created

-- Add new columns to the notes table
ALTER TABLE notes ADD COLUMN formatted_content TEXT;
ALTER TABLE notes ADD COLUMN auto_title TEXT;
ALTER TABLE notes ADD COLUMN detected_headings TEXT; -- JSON stored as TEXT
ALTER TABLE notes ADD COLUMN content_schema TEXT; -- JSON stored as TEXT
ALTER TABLE notes ADD COLUMN formatting_options TEXT; -- JSON stored as TEXT
ALTER TABLE notes ADD COLUMN color_theme TEXT;
ALTER TABLE notes ADD COLUMN attached_images TEXT; -- JSON stored as TEXT
ALTER TABLE notes ADD COLUMN word_count INTEGER DEFAULT 0;
ALTER TABLE notes ADD COLUMN reading_time INTEGER DEFAULT 0;

-- Create the settings table
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL DEFAULT 'default',
    
    -- Theme and UI customization
    primary_color TEXT DEFAULT '#4299e1',
    color_palette TEXT, -- JSON stored as TEXT
    dark_mode BOOLEAN DEFAULT FALSE,
    custom_css TEXT,
    
    -- Editor preferences  
    editor_font_family TEXT DEFAULT 'Inter, system-ui, sans-serif',
    editor_font_size INTEGER DEFAULT 16,
    editor_line_height TEXT DEFAULT '1.6',
    auto_save_interval INTEGER DEFAULT 30,
    spell_check BOOLEAN DEFAULT TRUE,
    
    -- Content preferences
    auto_detect_titles BOOLEAN DEFAULT TRUE,
    auto_generate_schema BOOLEAN DEFAULT TRUE,
    default_note_color TEXT DEFAULT '#f7fafc',
    
    -- Advanced settings
    export_format TEXT DEFAULT 'markdown',
    image_quality TEXT DEFAULT 'medium',
    max_image_size INTEGER DEFAULT 5,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on user_id for settings
CREATE INDEX IF NOT EXISTS idx_settings_user_id ON settings(user_id);

-- Insert default settings record
INSERT OR IGNORE INTO settings (user_id) VALUES ('default');

-- Create uploads directory structure (this would need to be done via the application)
-- The application will create the webui/static/uploads directory when needed
