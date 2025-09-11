from app.models.base_model import BaseModel
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base(cls=BaseModel)

class Lesson(Base):
    __tablename__ = 'lessons'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
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
    order = Column(Integer, default=0)
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
    lesson_id = Column(Integer, ForeignKey('lessons.id'), nullable=False)
    unit_id = Column(Integer, ForeignKey('units.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lesson = relationship("Lesson", back_populates="notes")
    unit = relationship("Unit", back_populates="notes")

    def __repr__(self):
        return f"<Note(id={self.id}, title='{self.title}', lesson_id={self.lesson_id}, unit_id={self.unit_id})>"
