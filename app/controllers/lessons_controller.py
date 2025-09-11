from flask import Blueprint
from app.services import lesson_service
from app.utils.responses import success_response, error_response
from app.utils.validators import validate_json

lessons_blueprint = Blueprint('lessons', __name__)

@lessons_blueprint.route('/lessons', methods=['GET'])
def get_lessons():
    lessons = lesson_service.get_all_lessons()
    return success_response([lesson.__dict__ for lesson in lessons])

@lessons_blueprint.route('/lessons', methods=['POST'])
@validate_json(['title'])
def create_lesson(data):
    lesson = lesson_service.create_lesson(data['title'], data.get('description'))
    return success_response(lesson.__dict__, 201)

@lessons_blueprint.route('/lessons/<int:lesson_id>', methods=['PUT'])
@validate_json([])
def update_lesson(data, lesson_id):
    lesson = lesson_service.update_lesson(lesson_id, data)
    if lesson:
        return success_response(lesson.__dict__)
    return error_response('Lesson not found', 404)

@lessons_blueprint.route('/lessons/<int:lesson_id>', methods=['DELETE'])
def delete_lesson(lesson_id):
    lesson = lesson_service.delete_lesson(lesson_id)
    if lesson:
        return success_response({'message': 'Lesson deleted'})
    return error_response('Lesson not found', 404)