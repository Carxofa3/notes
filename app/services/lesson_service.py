# app/services/lesson_service.py
from app.database import db
from app.models.models import Lesson

def get_all_lessons():
    return Lesson.query.order_by(Lesson.display_order).all()

def get_lesson_by_id(lesson_id):
    return Lesson.query.get_or_404(lesson_id)

def create_lesson(data):
    new_lesson = Lesson(name=data['name'])
    # Logic for display_order will be needed
    db.session.add(new_lesson)
    db.session.commit()
    return new_lesson

def update_lesson(lesson_id, data):
    lesson = get_lesson_by_id(lesson_id)
    lesson.name = data.get('name', lesson.name)
    # Logic for reordering will be more complex
    db.session.commit()
    return lesson

def delete_lesson(lesson_id):
    lesson = get_lesson_by_id(lesson_id)
    db.session.delete(lesson)
    db.session.commit()

def reorder_lessons(ordered_ids):
    for index, lesson_id in enumerate(ordered_ids):
        lesson = Lesson.query.get(lesson_id)
        if lesson:
            lesson.display_order = index
    db.session.commit()
