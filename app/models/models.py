# app/models/models.py
from app.database import db
import json

class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    display_order = db.Column(db.Integer)
    units = db.relationship('Unit', backref='lesson', lazy=True, cascade="all, delete-orphan")

class Unit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lesson.id'), nullable=False)
    display_order = db.Column(db.Integer)
    notes = db.relationship('Note', backref='unit', lazy=True, cascade="all, delete-orphan")

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    unit_id = db.Column(db.Integer, db.ForeignKey('unit.id'), nullable=False)
    ai_formatted_content = db.Column(db.Text)
    embeddings = db.relationship('Embedding', backref='note', lazy=True, cascade="all, delete-orphan")
    images = db.relationship('Image', backref='note', lazy=True, cascade="all, delete-orphan")

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    note_id = db.Column(db.Integer, db.ForeignKey('note.id'), nullable=False)

class Embedding(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey('note.id'), nullable=False)
    phrase = db.Column(db.Text, nullable=False)
    vector = db.Column(db.PickleType, nullable=False) # Using PickleType for simplicity

class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    _value = db.Column('value', db.Text)

    @property
    def value(self):
        return json.loads(self._value) if self._value else None

    @value.setter
    def value(self, val):
        self._value = json.dumps(val)
