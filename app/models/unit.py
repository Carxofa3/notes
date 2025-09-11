from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

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
