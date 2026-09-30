# app/api/gliner.py
from flask import request
from flask_restx import Namespace, Resource, fields
from app.services.gliner_service import gliner_service

ns = Namespace('gliner', description='GLiNER Neural Entity Extraction & Model Server')

extract_input_model = ns.model('GlinerExtractInput', {
    'text': fields.String(required=True, description='Context or proposition to extract academic entities from'),
    'labels': fields.List(fields.String, required=False, description='List of entity labels to extract (zero-shot)'),
    'threshold': fields.Float(required=False, default=0.35, description='Confidence threshold')
})

lan_toggle_model = ns.model('GlinerLanToggleInput', {
    'enabled': fields.Boolean(required=True, description='Enable or disable serving GLiNER on LAN to connected devices')
})

@ns.route('/status')
class GlinerStatus(Resource):
    def get(self):
        """Get GLiNER model hub status, download state, device, and request metrics"""
        return gliner_service.get_status(), 200

@ns.route('/download')
class GlinerDownload(Resource):
    def post(self):
        """Trigger auto-download of GLiNER model weights (urchade/gliner_small-v2.1)"""
        result = gliner_service.start_download_async()
        return result, 202

@ns.route('/extract')
class GlinerExtract(Resource):
    @ns.expect(extract_input_model, validate=True)
    def post(self):
        """Extract academic entities and claims using GLiNER neural engine"""
        data = request.get_json(silent=True) or {}
        text = data.get('text', '')
        labels = data.get('labels')
        threshold = data.get('threshold', 0.35)

        entities = gliner_service.extract_entities(text, labels=labels, threshold=threshold)
        return {
            'entities': entities,
            'count': len(entities),
            'model': gliner_service.DEFAULT_MODEL,
            'device': gliner_service.get_status()['device']
        }, 200

@ns.route('/lan-toggle')
class GlinerLanToggle(Resource):
    @ns.expect(lan_toggle_model, validate=True)
    def post(self):
        """Toggle serving GLiNER model to mobile and LAN peers"""
        data = request.get_json(silent=True) or {}
        enabled = data.get('enabled', True)
        return gliner_service.set_lan_serving(enabled), 200
