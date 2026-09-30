# app/api/decide.py
from flask import Blueprint, request, jsonify
from flask_restx import Namespace, Resource, fields
from app.services.decide_service import jev_engine

ns = Namespace('decide', description='GLiNER2.5-Decide / Jev-compatible decision API')
decide_bp = Blueprint('decide_v1', __name__)

decide_request_model = ns.model('DecideRequest', {
    'context': fields.String(required=True, description='The text context to evaluate'),
    'schema': fields.Raw(required=False, description='Dynamic schema configuration')
})

@decide_bp.route('/v1/decide', methods=['POST'])
def v1_decide():
    """Jev-compatible root /v1/decide endpoint"""
    data = request.get_json(silent=True) or {}
    context = data.get('context', '')
    schema = data.get('schema', {})
    result = jev_engine.evaluate(context, schema)
    return jsonify(result), 200

@ns.route('')
class DecideResource(Resource):
    @ns.doc('evaluate_context')
    @ns.expect(decide_request_model)
    def post(self):
        """Evaluate note context using the GLiNER2.5-Decide / Jev engine"""
        payload = request.get_json(silent=True) or {}
        context = payload.get('context', '')
        schema = payload.get('schema', {})
        result = jev_engine.evaluate(context, schema)
        return result, 200
