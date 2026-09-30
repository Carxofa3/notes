# app/api/rag.py
import os
from flask import request
from flask_restx import Namespace, Resource, fields
from werkzeug.utils import secure_filename
from app.services.rag_service import rag_service
from app.models.models import CourseDocument, SlideChunk
from app.database import db

ns = Namespace('rag', description='Course Slide RAG and Local Verification API')

verify_input_model = ns.model('VerifyClaimInput', {
    'claim': fields.String(required=True, description='Proposition / claim to verify'),
    'note_id': fields.Integer(required=False, description='Associated note ID')
})

search_parser = ns.parser()
search_parser.add_argument('q', type=str, required=True, help='Search query across slides', location='args')
search_parser.add_argument('course', type=str, required=False, help='Course filter', location='args')

@ns.route('/documents')
class DocumentList(Resource):
    def get(self):
        """List all indexed course slide documents"""
        docs = CourseDocument.query.order_by(CourseDocument.uploaded_at.desc()).all()
        return [{
            'id': d.id,
            'filename': d.filename,
            'title': d.title,
            'course_name': d.course_name,
            'total_pages': d.total_pages,
            'uploaded_at': d.uploaded_at.isoformat() if d.uploaded_at else None,
            'chunks_count': len(d.chunks)
        } for d in docs], 200

@ns.route('/upload')
class UploadSlides(Resource):
    def post(self):
        """Upload and index a PDF lecture slide deck"""
        if 'file' not in request.files:
            return {'message': 'No file part in request'}, 400

        file = request.files['file']
        if file.filename == '':
            return {'message': 'No selected file'}, 400

        if not file.filename.lower().endswith('.pdf'):
            return {'message': 'Only PDF slide decks are supported'}, 400

        course_name = request.form.get('course_name', 'General Course')
        custom_title = request.form.get('title')

        upload_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'uploads', 'slides')
        os.makedirs(upload_dir, exist_ok=True)

        filename = secure_filename(file.filename)
        save_path = os.path.join(upload_dir, filename)
        file.save(save_path)

        try:
            doc = rag_service.ingest_pdf(save_path, course_name=course_name, custom_title=custom_title)
            chunks_count = len(doc.chunks)
            if chunks_count == 0:
                return {
                    'message': 'Slide deck uploaded, but no extractable text layer was detected (scanned or image-only PDF).',
                    'warning': 'No extractable text found in this PDF. It may be a scanned image-only PDF without an OCR text layer.',
                    'document_id': doc.id,
                    'title': doc.title,
                    'total_pages': doc.total_pages,
                    'chunks_indexed': 0
                }, 201

            return {
                'message': 'Slide deck successfully indexed',
                'document_id': doc.id,
                'title': doc.title,
                'total_pages': doc.total_pages,
                'chunks_indexed': chunks_count
            }, 201
        except Exception as e:
            return {'message': f'Failed to process PDF: {str(e)}'}, 500

@ns.route('/search')
class SearchSlides(Resource):
    @ns.expect(search_parser)
    def get(self):
        """Search slide chunks by BM25 keyword matching"""
        args = search_parser.parse_args()
        query = args['q']
        course = args.get('course')
        results = rag_service.search_slides(query, limit=10, course_name=course)
        return results, 200

@ns.route('/verify-claim')
class VerifyClaim(Resource):
    @ns.expect(verify_input_model, validate=True)
    def post(self):
        """Verify an isolated factual claim against local course slides"""
        data = request.get_json(silent=True) or {}
        claim = data.get('claim', '').strip()
        note_id = data.get('note_id')

        if not claim:
            return {'message': 'Claim cannot be empty'}, 400

        result = rag_service.verify_claim(claim, note_id=note_id)
        return result, 200
