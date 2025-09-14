from app.database import db
from app.models import Lesson

def get_all_lessons():
    return db.session.query(Lesson).all()

def create_lesson(title, description):
    lesson = Lesson(title=title, description=description)
    db.session.add(lesson)
    db.session.commit()
    return lesson

def update_lesson(lesson_id, data):
    lesson = db.session.query(Lesson).filter(Lesson.id == lesson_id).first()
    if lesson:
        for key, value in data.items():
            setattr(lesson, key, value)
        db.session.commit()
    return lesson

def delete_lesson(lesson_id):
    lesson = db.session.query(Lesson).filter(Lesson.id == lesson_id).first()
    if lesson:
        db.session.delete(lesson)
        db.session.commit()
    return lesson