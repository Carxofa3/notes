from app.utils.database import get_db
from app.models.unit import Unit

def get_units_by_lesson(lesson_id):
    db = next(get_db())
    return db.query(Unit).filter(Unit.lesson_id == lesson_id).all()

def create_unit(title, lesson_id):
    db = next(get_db())
    unit = Unit(title=title, lesson_id=lesson_id)
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit

def update_unit(unit_id, data):
    db = next(get_db())
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if unit:
        for key, value in data.items():
            setattr(unit, key, value)
        db.commit()
        db.refresh(unit)
    return unit

def delete_unit(unit_id):
    db = next(get_db())
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if unit:
        db.delete(unit)
        db.commit()
    return unit