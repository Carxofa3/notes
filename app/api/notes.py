# app/api/notes.py
from flask_restx import Namespace, Resource, fields
from app.services import note_service

ns = Namespace('notes', description='Note related operations')

note_model = ns.model('Note', {
    'id': fields.Integer(readonly=True, description='The note unique identifier'),
    'title': fields.String(required=True, description='The note title'),
    'content': fields.String(description='The note content'),
    'unit_id': fields.Integer(required=True, description='The unit identifier'),
    'ai_formatted_content': fields.String(readonly=True, description='AI formatted content'),
})

note_input_model = ns.model('NoteInput', {
    'title': fields.String(required=True, description='The note title'),
    'content': fields.String(description='The note content'),
    'unit_id': fields.Integer(required=False, description='The unit identifier'),
})

note_update_model = ns.model('NoteUpdate', {
    'title': fields.String(description='The new note title'),
    'content': fields.String(description='The new note content'),
})

@ns.route('/by-unit/<int:unit_id>')
@ns.param('unit_id', 'The unit identifier')
class NoteList(Resource):
    @ns.doc('list_notes_for_unit')
    @ns.marshal_list_with(note_model)
    def get(self, unit_id):
        """List all notes for a given unit"""
        return note_service.get_all_notes_for_unit(unit_id)

    @ns.doc('create_note_for_unit')
    @ns.expect(note_input_model, validate=True)
    @ns.marshal_with(note_model, code=201)
    def post(self, unit_id):
        """Create a new note for a given unit"""
        payload = dict(ns.payload or {})
        payload['unit_id'] = unit_id
        return note_service.create_note(unit_id, payload), 201

@ns.route('/<int:id>')
@ns.response(404, 'Note not found')
@ns.param('id', 'The note identifier')
class Note(Resource):
    @ns.doc('get_note')
    @ns.marshal_with(note_model)
    def get(self, id):
        """Fetch a note given its identifier"""
        return note_service.get_note_by_id(id)

    @ns.doc('update_note')
    @ns.expect(note_update_model, validate=True)
    @ns.marshal_with(note_model)
    def put(self, id):
        """Update a note given its identifier"""
        return note_service.update_note(id, ns.payload)

    @ns.doc('delete_note')
    @ns.response(204, 'Note deleted')
    def delete(self, id):
        """Delete a note given its identifier"""
        note_service.delete_note(id)
        return '', 204
