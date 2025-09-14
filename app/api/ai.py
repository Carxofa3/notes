from flask_restx import Namespace, Resource, reqparse
from app.services import ai_service, note_service
from app.database import db

ns = Namespace('ai', description='AI related operations')

search_parser = reqparse.RequestParser()
search_parser.add_argument('q', type=str, required=True, help='Search query', location='args')

@ns.route('/search')
class Search(Resource):
    @ns.doc('search_notes')
    @ns.expect(search_parser)
    def get(self):
        """Searches notes by semantic similarity"""
        args = search_parser.parse_args()
        query = args['q']
        results = ai_service.search_notes_by_query(query)
        return results, 200

@ns.route('/format-note/<int:note_id>')
@ns.param('note_id', 'The note identifier')
class FormatNote(Resource):
    @ns.doc('format_note')
    @ns.response(200, 'Note formatted successfully')
    @ns.response(500, 'AI formatting failed')
    def post(self, note_id):
        """Formats a note's content using AI"""
        note = note_service.get_note_by_id(note_id)
        if not note.content:
            return {'message': 'Note has no content to format'}, 400

        formatted_content = ai_service.format_text(note.content)

        if formatted_content:
            note.content = formatted_content
            db.session.commit()
            return {'formatted_content': formatted_content}, 200
        else:
            return {'message': 'Failed to format note with AI'}, 500
