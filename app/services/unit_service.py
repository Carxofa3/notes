from app.database import db
from app.models import Unit

def get_units_by_lesson(lesson_id):
    return db.session.query(Unit).filter(Unit.lesson_id == lesson_id).all()

def create_unit(title, lesson_id):
    unit = Unit(title=title, lesson_id=lesson_id)
    db.session.add(unit)
    db.session.commit()
    return unit

def update_unit(unit_id, data):
    unit = db.session.query(Unit).filter(Unit.id == unit_id).first()
    if unit:
        for key, value in data.items():
            setattr(unit, key, value)
        db.session.commit()
    return unit

def delete_unit(unit_id):
    unit = db.session.query(Unit).filter(Unit.id == unit_id).first()
    if unit:
        db.session.delete(unit)
        db.session.commit()
    return unit