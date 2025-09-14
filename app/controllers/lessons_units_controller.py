from flask import Blueprint, request, jsonify
from app.models.models import Lesson, Unit
from app.database import db
from app.utils.responses import success_response, error_response
from datetime import datetime

lessons_units_blueprint = Blueprint('lessons_units', __name__)

# Lessons endpoints
@lessons_units_blueprint.route('/lessons', methods=['GET'])
def get_lessons():
    """Get all lessons ordered by display_order"""
    try:
        lessons = Lesson.query.order_by(Lesson.display_order).all()
        
        lessons_data = []
        for lesson in lessons:
            lessons_data.append({
                'id': lesson.id,
                'title': lesson.title,
                'description': lesson.description,
                'display_order': lesson.display_order,
                'created_at': lesson.created_at.isoformat() if lesson.created_at else None,
                'updated_at': lesson.updated_at.isoformat() if lesson.updated_at else None,
                'units_count': len(lesson.units)
            })
        
        return success_response(data={'lessons': lessons_data})
        
    except Exception as e:
        return error_response(f"Failed to retrieve lessons: {str(e)}")

@lessons_units_blueprint.route('/lessons/<int:lesson_id>', methods=['PUT'])
def update_lesson(lesson_id):
    """Update lesson title and description"""
    try:
        lesson = Lesson.query.get(lesson_id)
        if not lesson:
            return error_response("Lesson not found")
        
        data = request.get_json()
        
        if 'title' in data:
            lesson.title = data['title']
        if 'description' in data:
            lesson.description = data['description']
        
        lesson.updated_at = datetime.utcnow()
        db.session.commit()
        
        return success_response(data={
            'id': lesson.id,
            'title': lesson.title,
            'description': lesson.description,
            'display_order': lesson.display_order
        }, message="Lesson updated successfully")
        
    except Exception as e:
        return error_response(f"Failed to update lesson: {str(e)}")

@lessons_units_blueprint.route('/lessons/reorder', methods=['POST'])
def reorder_lessons():
    """Reorder lessons based on new positions"""
    try:
        data = request.get_json()
        lesson_orders = data.get('lesson_orders', [])
        
        # lesson_orders should be array of {id: int, display_order: int}
        for lesson_order in lesson_orders:
            lesson_id = lesson_order.get('id')
            new_order = lesson_order.get('display_order')
            
            lesson = Lesson.query.get(lesson_id)
            if lesson:
                lesson.display_order = new_order
                lesson.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return success_response(message="Lessons reordered successfully")
        
    except Exception as e:
        db.session.rollback()
        return error_response(f"Failed to reorder lessons: {str(e)}")

# Units endpoints
@lessons_units_blueprint.route('/lessons/<int:lesson_id>/units', methods=['GET'])
def get_units(lesson_id):
    """Get all units for a lesson ordered by display_order"""
    try:
        units = Unit.query.filter_by(lesson_id=lesson_id).order_by(Unit.display_order).all()
        
        units_data = []
        for unit in units:
            units_data.append({
                'id': unit.id,
                'title': unit.title,
                'lesson_id': unit.lesson_id,
                'display_order': unit.display_order,
                'created_at': unit.created_at.isoformat() if unit.created_at else None,
                'updated_at': unit.updated_at.isoformat() if unit.updated_at else None,
                'notes_count': len(unit.notes)
            })
        
        return success_response(data={'units': units_data})
        
    except Exception as e:
        return error_response(f"Failed to retrieve units: {str(e)}")

@lessons_units_blueprint.route('/units/<int:unit_id>', methods=['PUT'])
def update_unit(unit_id):
    """Update unit title"""
    try:
        unit = Unit.query.get(unit_id)
        if not unit:
            return error_response("Unit not found")
        
        data = request.get_json()
        
        if 'title' in data:
            unit.title = data['title']
        
        unit.updated_at = datetime.utcnow()
        db.session.commit()
        
        return success_response(data={
            'id': unit.id,
            'title': unit.title,
            'lesson_id': unit.lesson_id,
            'display_order': unit.display_order
        }, message="Unit updated successfully")
        
    except Exception as e:
        return error_response(f"Failed to update unit: {str(e)}")

@lessons_units_blueprint.route('/lessons/<int:lesson_id>/units/reorder', methods=['POST'])
def reorder_units(lesson_id):
    """Reorder units within a lesson"""
    try:
        data = request.get_json()
        unit_orders = data.get('unit_orders', [])
        
        # unit_orders should be array of {id: int, display_order: int}
        for unit_order in unit_orders:
            unit_id = unit_order.get('id')
            new_order = unit_order.get('display_order')
            
            unit = Unit.query.filter_by(id=unit_id, lesson_id=lesson_id).first()
            if unit:
                unit.display_order = new_order
                unit.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return success_response(message="Units reordered successfully")
        
    except Exception as e:
        db.session.rollback()
        return error_response(f"Failed to reorder units: {str(e)}")

@lessons_units_blueprint.route('/lessons', methods=['POST'])
def create_lesson():
    """Create a new lesson"""
    try:
        data = request.get_json()
        title = data.get('title')
        description = data.get('description', '')
        
        if not title:
            return error_response("Lesson title is required")
        
        # Get next display order
        max_order = db.session.query(db.func.max(Lesson.display_order)).scalar() or 0
        
        lesson = Lesson(
            title=title,
            description=description,
            display_order=max_order + 1
        )
        
        db.session.add(lesson)
        db.session.commit()
        
        return success_response(data={
            'id': lesson.id,
            'title': lesson.title,
            'description': lesson.description,
            'display_order': lesson.display_order
        }, message="Lesson created successfully")
        
    except Exception as e:
        return error_response(f"Failed to create lesson: {str(e)}")

@lessons_units_blueprint.route('/lessons/<int:lesson_id>/units', methods=['POST'])
def create_unit(lesson_id):
    """Create a new unit in a lesson"""
    try:
        lesson = Lesson.query.get(lesson_id)
        if not lesson:
            return error_response("Lesson not found")
        
        data = request.get_json()
        title = data.get('title')
        
        if not title:
            return error_response("Unit title is required")
        
        # Get next display order for this lesson
        max_order = db.session.query(db.func.max(Unit.display_order)).filter_by(lesson_id=lesson_id).scalar() or 0
        
        unit = Unit(
            title=title,
            lesson_id=lesson_id,
            display_order=max_order + 1
        )
        
        db.session.add(unit)
        db.session.commit()
        
        return success_response(data={
            'id': unit.id,
            'title': unit.title,
            'lesson_id': unit.lesson_id,
            'display_order': unit.display_order
        }, message="Unit created successfully")
        
    except Exception as e:
        return error_response(f"Failed to create unit: {str(e)}")

@lessons_units_blueprint.route('/lessons/<int:lesson_id>', methods=['DELETE'])
def delete_lesson(lesson_id):
    """Delete a lesson and all its units and notes"""
    try:
        lesson = Lesson.query.get(lesson_id)
        if not lesson:
            return error_response("Lesson not found")
        
        db.session.delete(lesson)
        db.session.commit()
        
        return success_response(message="Lesson deleted successfully")
        
    except Exception as e:
        return error_response(f"Failed to delete lesson: {str(e)}")

@lessons_units_blueprint.route('/units/<int:unit_id>', methods=['DELETE'])
def delete_unit(unit_id):
    """Delete a unit and all its notes"""
    try:
        unit = Unit.query.get(unit_id)
        if not unit:
            return error_response("Unit not found")
        
        db.session.delete(unit)
        db.session.commit()
        
        return success_response(message="Unit deleted successfully")
        
    except Exception as e:
        return error_response(f"Failed to delete unit: {str(e)}")
