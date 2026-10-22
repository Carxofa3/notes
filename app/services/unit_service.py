# app/services/unit_service.py
from app.database import db
from app.models.models import Unit, Lesson

def get_all_units_for_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    return Unit.query.filter_by(lesson_id=lesson.id).order_by(Unit.display_order).all()

def get_unit_by_id(unit_id):
    return Unit.query.get_or_404(unit_id)

def create_unit(lesson_id, data):
    lesson = Lesson.query.get_or_404(lesson_id)
    name = data.get('name', '').strip() or 'New Folder'
    icon = data.get('icon') or '📁'
    color = data.get('color') or '#10b981'
    
    # Calculate display order
    last_unit = Unit.query.filter_by(lesson_id=lesson.id).order_by(Unit.display_order.desc()).first()
    next_order = (last_unit.display_order + 1) if last_unit and last_unit.display_order is not None else 0

    new_unit = Unit(
        name=name,
        lesson_id=lesson.id,
        display_order=next_order,
        icon=icon,
        color=color
    )
    db.session.add(new_unit)
    db.session.commit()
    return new_unit

def update_unit(unit_id, data):
    unit = get_unit_by_id(unit_id)
    if 'name' in data and data['name']:
        unit.name = data['name'].strip()
    if 'icon' in data:
        unit.icon = data['icon']
    if 'color' in data:
        unit.color = data['color']
    if 'lesson_id' in data and data['lesson_id']:
        try:
            unit.lesson_id = int(data['lesson_id'])
        except (ValueError, TypeError):
            pass
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
