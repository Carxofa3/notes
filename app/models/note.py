from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

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
