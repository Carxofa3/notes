from app.models.base_model import BaseModel
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base(cls=BaseModel)

class Lesson(Base):
    __tablename__ = 'lessons'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    units = relationship("Unit", back_populates="lesson", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="lesson", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Lesson(id={self.id}, title='{self.title}')>"

class Unit(Base):
    __tablename__ = 'units'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    lesson_id = Column(Integer, ForeignKey('lessons.id'), nullable=False)
    order = Column(Integer, default=0)  # Keep for backward compatibility
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lesson = relationship("Lesson", back_populates="units")
    notes = relationship("Note", back_populates="unit", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Unit(id={self.id}, title='{self.title}', lesson_id={self.lesson_id})>"

class Note(Base):
    __tablename__ = 'notes'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    formatted_content = Column(Text, nullable=True)  # Rich text HTML content
    lesson_id = Column(Integer, ForeignKey('lessons.id'), nullable=False)
    unit_id = Column(Integer, ForeignKey('units.id'), nullable=True)
    
    # Auto-detection features
    auto_title = Column(String, nullable=True)  # Auto-detected title
    detected_headings = Column(JSON, nullable=True)  # Auto-detected headings/subtitles
    content_schema = Column(JSON, nullable=True)  # Live schema of content structure
    
    # Formatting and display options
    formatting_options = Column(JSON, nullable=True)  # Custom formatting settings
    color_theme = Column(String, nullable=True)  # Custom color for this note
    
    # Image attachments
    attached_images = Column(JSON, nullable=True)  # List of attached image paths/URLs
    
    # Metadata
    word_count = Column(Integer, default=0)
    reading_time = Column(Integer, default=0)  # Estimated reading time in minutes
    
    # AI-related fields
    ai_formatted_content = Column(Text, nullable=True)  # AI-improved content
    embedding_vector = Column(JSON, nullable=True)  # Note-level embedding
    embedding_model = Column(String, default='text-embedding-ada-002')
    last_embedded_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lesson = relationship("Lesson", back_populates="notes")
    unit = relationship("Unit", back_populates="notes")
    embeddings = relationship("Embedding", back_populates="note", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Note(id={self.id}, title='{self.title}', lesson_id={self.lesson_id}, unit_id={self.unit_id})>"

class Settings(Base):
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False, default='default')  # For multi-user support later
    
    # Theme and UI customization
    primary_color = Column(String, default='#4299e1')  # Main theme color
    color_palette = Column(JSON, nullable=True)  # Generated complementary colors
    dark_mode = Column(Boolean, default=False)
    custom_css = Column(Text, nullable=True)  # Custom CSS overrides
    
    # Editor preferences
    editor_font_family = Column(String, default='Inter, system-ui, sans-serif')
    editor_font_size = Column(Integer, default=16)
    editor_line_height = Column(String, default='1.6')
    auto_save_interval = Column(Integer, default=30)  # seconds
    spell_check = Column(Boolean, default=True)
    
    # Content preferences
    auto_detect_titles = Column(Boolean, default=True)
    auto_generate_schema = Column(Boolean, default=True)
    default_note_color = Column(String, default='#f7fafc')
    
    # Advanced settings
    export_format = Column(String, default='markdown')  # markdown, html, pdf
    image_quality = Column(String, default='medium')  # low, medium, high
    max_image_size = Column(Integer, default=5)  # MB
    
    # AI settings
    ai_base_url = Column(String, default='https://api.openai.com/v1')
    ai_api_key = Column(String, nullable=True)
    ai_model = Column(String, default='gpt-3.5-turbo')
    ai_embedding_model = Column(String, default='text-embedding-ada-002')
    ai_enabled = Column(Boolean, default=False)
    ai_auto_format = Column(Boolean, default=False)
    search_enabled = Column(Boolean, default=True)
    max_search_results = Column(Integer, default=10)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Settings(id={self.id}, user_id='{self.user_id}', primary_color='{self.primary_color}')>"

class Embedding(Base):
    __tablename__ = 'embeddings'

    id = Column(Integer, primary_key=True)
    note_id = Column(Integer, ForeignKey('notes.id'), nullable=False)
    phrase_text = Column(Text, nullable=False)
    phrase_start = Column(Integer, nullable=False)
    phrase_end = Column(Integer, nullable=False)
    embedding_vector = Column(JSON, nullable=False)
    embedding_model = Column(String, default='text-embedding-ada-002')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    note = relationship("Note", back_populates="embeddings")

    def __repr__(self):
        return f"<Embedding(id={self.id}, note_id={self.note_id}, phrase='{self.phrase_text[:50]}')>"

class SearchCache(Base):
    __tablename__ = 'search_cache'

    id = Column(Integer, primary_key=True)
    query_text = Column(String, nullable=False)
    query_hash = Column(String, unique=True, nullable=False)
    results = Column(JSON, nullable=False)
    embedding_vector = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    def __repr__(self):
        return f"<SearchCache(id={self.id}, query='{self.query_text[:30]}')>"
