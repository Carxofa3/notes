from flask import Blueprint, request
from app.services import unit_service
from app.utils.responses import success_response, error_response
from app.utils.validators import validate_json

units_blueprint = Blueprint('units', __name__)

@units_blueprint.route('/units', methods=['GET'])
def get_units():
    lesson_id = request.args.get('lesson_id')
    if not lesson_id:
        return error_response('Missing lesson_id parameter', 400)
    units = unit_service.get_units_by_lesson(lesson_id)
    return success_response(units)

@units_blueprint.route('/units', methods=['POST'])
@validate_json(['title', 'lesson_id'])
def create_unit(data):
    unit = unit_service.create_unit(data['title'], data['lesson_id'])
    return success_response(unit, 201)

@units_blueprint.route('/units/<int:unit_id>', methods=['PUT'])
@validate_json([])
def update_unit(data, unit_id):
    unit = unit_service.update_unit(unit_id, data)
    if unit:
        return success_response(unit)
    return error_response('Unit not found', 404)

@units_blueprint.route('/units/<int:unit_id>', methods=['DELETE'])
def delete_unit(unit_id):
    unit = unit_service.delete_unit(unit_id)
    if unit:
        return success_response({'message': 'Unit deleted'})
    return error_response('Unit not found', 404)