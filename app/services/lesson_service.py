from app.utils.database import get_db
from app.models.lesson import Lesson

def get_all_lessons():
    db = next(get_db())
    return db.query(Lesson).all()

def create_lesson(title, description):
    db = next(get_db())
    lesson = Lesson(title=title, description=description)
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson

def update_lesson(lesson_id, data):
    db = next(get_db())
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if lesson:
        for key, value in data.items():
            setattr(lesson, key, value)
        db.commit()
        db.refresh(lesson)
    return lesson

def delete_lesson(lesson_id):
    db = next(get_db())
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if lesson:
        db.delete(lesson)
        db.commit()
    return lesson