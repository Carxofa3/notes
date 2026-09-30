# app/api/sync.py
import base64
from flask import request
from flask_restx import Namespace, Resource, fields
from app.services.sync_service import sync_service

ns = Namespace('sync', description='Tailscale P2P Sync and CRDT Coordination API')

peer_input_model = ns.model('PeerInput', {
    'device_name': fields.String(required=False, description='Peer device name'),
    'name': fields.String(required=False, description='Alternative device name key'),
    'magic_dns': fields.String(required=True, description='Peer MagicDNS address'),
    'ip': fields.String(required=False, description='Tailscale IP'),
    'port': fields.Integer(required=False, description='Port'),
    'fingerprint': fields.String(required=True, description='Ed25519 cert fingerprint')
})

crdt_delta_model = ns.model('CrdtDeltaInput', {
    'note_id': fields.Integer(required=True, description='Note ID'),
    'delta_base64': fields.String(required=True, description='Base64 encoded Yjs CRDT binary delta')
})

@ns.route('/pair-info')
class PairInfo(Resource):
    def get(self):
        """Get local device Tailscale pairing information and QR code payload"""
        return sync_service.get_device_info(), 200

@ns.route('/peers')
class PeerList(Resource):
    def get(self):
        """List all paired Tailscale peers"""
        return sync_service.list_peers(), 200

    @ns.expect(peer_input_model, validate=True)
    def post(self):
        """Register or pair a new Tailscale peer device"""
        data = request.get_json(silent=True) or {}
        peer = sync_service.register_peer(data)
        return {
            'message': 'Peer registered successfully',
            'peer_id': peer.id,
            'device_name': peer.device_name,
            'magic_dns': peer.magic_dns
        }, 201

@ns.route('/delta')
class CrdtDelta(Resource):
    @ns.expect(crdt_delta_model, validate=True)
    def post(self):
        """Import a binary CRDT update delta from a paired peer"""
        data = request.get_json(silent=True) or {}
        note_id = data.get('note_id')
        delta_b64 = data.get('delta_base64', '')
        try:
            delta_bytes = base64.b64decode(delta_b64)
            success = sync_service.import_crdt_delta(note_id, delta_bytes)
            if success:
                return {'message': 'CRDT delta applied successfully'}, 200
            return {'message': 'Note not found'}, 404
        except Exception as e:
            return {'message': f'Invalid delta format: {str(e)}'}, 400

@ns.route('/delta/<int:note_id>')
class GetCrdtDelta(Resource):
    def get(self, note_id):
        """Export current binary CRDT state for a note"""
        delta_bytes = sync_service.export_crdt_delta(note_id)
        if delta_bytes is None:
            return {'message': 'No CRDT state recorded for this note'}, 404
        return {
            'note_id': note_id,
            'delta_base64': base64.b64encode(delta_bytes).decode('utf-8')
        }, 200

@ns.route('/discovered-nodes')
class DiscoveredNodes(Resource):
    def get(self):
        """List all auto-discovered local LAN peer nodes (LM Studio Nodes style)"""
        return {
            'nodes': sync_service.get_discovered_nodes(),
            'local_device': sync_service.get_device_info()
        }, 200

