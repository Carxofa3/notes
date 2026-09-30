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

from flask import request
from flask_restx import fields
from app.services.llm_escalation import llm_escalation

escalate_input_model = ns.model('EscalateContradictionInput', {
    'claim': fields.String(required=True, description='The contradicted claim'),
    'slide_excerpt': fields.String(required=True, description='The slide excerpt evidence'),
    'web_evidence': fields.String(required=False, description='Optional external web evidence')
})

synthesize_input_model = ns.model('SynthesizeLectureInput', {
    'content': fields.String(required=True, description='Raw student lecture notes to synthesize')
})

@ns.route('/escalate-contradiction')
class EscalateContradiction(Resource):
    @ns.doc('escalate_contradiction')
    @ns.expect(escalate_input_model, validate=True)
    def post(self):
        """Offload complex contradiction resolution to Heavy LLM (Tailscale Ollama / Cloud)"""
        data = request.get_json(silent=True) or {}
        claim = data.get('claim', '').strip()
        slide_excerpt = data.get('slide_excerpt', '').strip()
        web_evidence = data.get('web_evidence', '')
        if not claim:
            return {'message': 'Claim cannot be empty'}, 400
        res = llm_escalation.resolve_contradiction(claim, slide_excerpt, web_evidence)
        return res, 200

@ns.route('/synthesize-lecture')
class SynthesizeLecture(Resource):
    @ns.doc('synthesize_lecture')
    @ns.expect(synthesize_input_model, validate=True)
    def post(self):
        """Transform rough student notes into a structured study guide with formulas and exam traps"""
        data = request.get_json(silent=True) or {}
        content = data.get('content', '').strip()
        if not content:
            return {'message': 'Content cannot be empty'}, 400
        synthesized = llm_escalation.synthesize_lecture_notes(content)
        return {'synthesized_content': synthesized}, 200
