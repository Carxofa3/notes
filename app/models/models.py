# app/models/models.py
from app.database import db
import json
from datetime import datetime, timezone

def utc_now():
    return datetime.now(timezone.utc)

class Lesson(db.Model):
    __tablename__ = 'lesson'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    display_order = db.Column(db.Integer)
    units = db.relationship('Unit', backref='lesson', lazy=True, cascade="all, delete-orphan")

class Unit(db.Model):
    __tablename__ = 'unit'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lesson.id'), nullable=False)
    display_order = db.Column(db.Integer)
    notes = db.relationship('Note', backref='unit', lazy=True, cascade="all, delete-orphan")

class Note(db.Model):
    __tablename__ = 'note'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    unit_id = db.Column(db.Integer, db.ForeignKey('unit.id'), nullable=False)
    ai_formatted_content = db.Column(db.Text)
    crdt_state = db.Column(db.LargeBinary, nullable=True)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)
    embeddings = db.relationship('Embedding', backref='note', lazy=True, cascade="all, delete-orphan")
    images = db.relationship('Image', backref='note', lazy=True, cascade="all, delete-orphan")
    fact_checks = db.relationship('FactCheckResult', backref='note', lazy=True, cascade="all, delete-orphan")

class Image(db.Model):
    __tablename__ = 'image'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    note_id = db.Column(db.Integer, db.ForeignKey('note.id'), nullable=False)

class Embedding(db.Model):
    __tablename__ = 'embedding'
    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey('note.id'), nullable=False)
    phrase = db.Column(db.Text, nullable=False)
    vector = db.Column(db.PickleType, nullable=False) # Using PickleType for simplicity

class Setting(db.Model):
    __tablename__ = 'setting'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    _value = db.Column('value', db.Text)

    @property
    def value(self):
        return json.loads(self._value) if self._value else None

    @value.setter
    def value(self, val):
        self._value = json.dumps(val)

class CourseDocument(db.Model):
    __tablename__ = 'course_document'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(255), nullable=True)
    course_name = db.Column(db.String(100), nullable=True)
    total_pages = db.Column(db.Integer, default=0)
    uploaded_at = db.Column(db.DateTime, default=utc_now)
    chunks = db.relationship('SlideChunk', backref='document', lazy=True, cascade="all, delete-orphan")

class SlideChunk(db.Model):
    __tablename__ = 'slide_chunk'
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('course_document.id'), nullable=False)
    page_number = db.Column(db.Integer, nullable=False)
    slide_title = db.Column(db.String(255), nullable=True)
    content = db.Column(db.Text, nullable=False)
    vector = db.Column(db.PickleType, nullable=True)

class FactCheckResult(db.Model):
    __tablename__ = 'fact_check_result'
    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey('note.id'), nullable=True)
    claim = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), nullable=False) # 'verified', 'contradiction', 'plausible', 'unverified'
    confidence = db.Column(db.Float, default=0.0)
    source_tier = db.Column(db.String(50)) # 'course_slides', 'wikipedia', 'semantic_scholar', 'jev_decide'
    citation = db.Column(db.String(255), nullable=True)
    evidence_text = db.Column(db.Text, nullable=True)
    suggested_correction = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

class TailscalePeer(db.Model):
    __tablename__ = 'tailscale_peer'
    id = db.Column(db.Integer, primary_key=True)
    device_name = db.Column(db.String(100), nullable=False)
    tailscale_ip = db.Column(db.String(64), nullable=True)
    magic_dns = db.Column(db.String(255), nullable=True)
    port = db.Column(db.Integer, default=58855)
    fingerprint = db.Column(db.String(128), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    last_seen = db.Column(db.DateTime, default=utc_now)
