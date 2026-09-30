# app/api/academic.py
from flask import request
from flask_restx import Namespace, Resource, fields
from app.services.academic_service import academic_service

ns = Namespace('academic', description='Tier 2 Privacy-Preserving Academic Verification API')

academic_verify_model = ns.model('AcademicVerifyInput', {
    'claim': fields.String(required=True, description='The claim to verify against open academic databases')
})

@ns.route('/verify')
class AcademicVerify(Resource):
    @ns.expect(academic_verify_model, validate=True)
    def post(self):
        """Verify an isolated proposition against Wikipedia & Semantic Scholar"""
        data = request.get_json(silent=True) or {}
        claim = data.get('claim', '').strip()
        if not claim:
            return {'message': 'Claim cannot be empty'}, 400

        result = academic_service.verify_claim(claim)
        return result, 200
