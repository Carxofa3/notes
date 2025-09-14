# app/services/unit_service.py
from app.database import db
from app.models.models import Unit, Lesson

def get_all_units_for_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    return lesson.units.order_by(Unit.display_order).all()

def get_unit_by_id(unit_id):
    return Unit.query.get_or_404(unit_id)

def create_unit(lesson_id, data):
    lesson = Lesson.query.get_or_404(lesson_id)
    new_unit = Unit(name=data['name'], lesson_id=lesson.id)
    # Logic for display_order will be needed
    db.session.add(new_unit)
    db.session.commit()
    return new_unit

def update_unit(unit_id, data):
    unit = get_unit_by_id(unit_id)
    unit.name = data.get('name', unit.name)
    # Logic for reordering will be more complex
    db.session.commit()
    return unit

def delete_unit(unit_id):
    unit = get_unit_by_id(unit_id)
    db.session.delete(unit)
    db.session.commit()

def reorder_units(ordered_ids):
    for index, unit_id in enumerate(ordered_ids):
        unit = Unit.query.get(unit_id)
        if unit:
            unit.display_order = index
    db.session.commit()
