from flask import Blueprint, request
from app.services import note_service
from app.utils.responses import success_response, error_response
from app.utils.validators import validate_json

notes_blueprint = Blueprint('notes', __name__)

@notes_blueprint.route('/notes', methods=['GET'])
def get_notes():
    unit_id = request.args.get('unit_id')
    if not unit_id:
        return error_response('Missing unit_id parameter', 400)
    notes = note_service.get_notes_by_unit(unit_id)
    return success_response([note.__dict__ for note in notes])

@notes_blueprint.route('/notes', methods=['POST'])
@validate_json(['title', 'content', 'lesson_id'])
def create_note(data):
    note = note_service.create_note(data['title'], data['content'], data['lesson_id'], data.get('unit_id'))
    return success_response(note.__dict__, 201)

@notes_blueprint.route('/notes/<int:note_id>', methods=['PUT'])
@validate_json([])
def update_note(data, note_id):
    note = note_service.update_note(note_id, data)
    if note:
        return success_response(note.__dict__)
    return error_response('Note not found', 404)

@notes_blueprint.route('/notes/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    note = note_service.delete_note(note_id)
    if note:
        return success_response({'message': 'Note deleted'})
    return error_response('Note not found', 404)