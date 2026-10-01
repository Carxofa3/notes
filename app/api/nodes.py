# app/api/nodes.py
"""
Nodes & Cluster Management API (LM Studio Nodes Style).
Allows viewing discovered & paired peers, inspecting their RAM/VRAM specs,
configuring local llama.cpp exposure to the peer network, and remotely triggering GLiNER downloads.
"""

from flask import request
from flask_restx import Namespace, Resource, fields
import requests
from app.services.sync_service import sync_service

ns = Namespace('nodes', description='Cluster Peer Management, Capability Configuration, and Model Routing')

self_config_model = ns.model('NodeSelfConfig', {
    'name': fields.String(required=False, description='Custom friendly device name for this workstation'),
    'llamacpp_enabled': fields.Boolean(required=False, description='Expose local llama.cpp server to peer network'),
    'llamacpp_local_port': fields.Integer(required=False, default=8080, description='Port where llama-server is listening locally')
})

peer_rename_model = ns.model('PeerRename', {
    'alias': fields.String(required=True, description='Custom alias/nickname for this peer node')
})

select_llm_model = ns.model('SelectLlm', {
    'endpoint': fields.String(required=False, description='Peer endpoint URL to use as cluster LLM provider (or empty to use local)')
})

trigger_gliner_model = ns.model('TriggerGliner', {
    'peer_url': fields.String(required=True, description='Base HTTP URL of remote peer (e.g. http://192.168.0.60:5000)')
})


@ns.route('/cluster')
class ClusterOverview(Resource):
    def get(self):
        """Get full cluster overview: local node specs, discovered peers, and active LLM routing"""
        return sync_service.get_cluster_overview(), 200


@ns.route('/self/config')
class NodeSelfConfig(Resource):
    def get(self):
        """Get local node configuration, hardware specs, and service states"""
        return {
            "name": sync_service.get_node_name(),
            "llamacpp": sync_service.get_llamacpp_config()
        }, 200

    @ns.expect(self_config_model, validate=True)
    def post(self):
        """Update local node friendly name and llama.cpp exposure configuration"""
        data = request.get_json(silent=True) or {}
        if 'name' in data:
            sync_service.set_node_name(data['name'])
        if 'llamacpp_enabled' in data or 'llamacpp_local_port' in data:
            enabled = data.get('llamacpp_enabled', sync_service.is_llamacpp_enabled())
            port = data.get('llamacpp_local_port', sync_service.get_llamacpp_local_port())
            sync_service.set_llamacpp_config(enabled, port)

        return {
            'message': 'Configuration updated successfully',
            'name': sync_service.get_node_name(),
            'llamacpp': sync_service.get_llamacpp_config()
        }, 200


@ns.route('/self/llamacpp-health')
class LlamaCppHealth(Resource):
    def get(self):
        """Check if local llama-server on configured port is alive and responding"""
        return sync_service.check_local_llamacpp_health(), 200


@ns.route('/peers/<string:peer_id>/rename')
class PeerRename(Resource):
    @ns.expect(peer_rename_model, validate=True)
    def post(self, peer_id):
        """Assign a custom nickname/alias to a discovered or paired peer"""
        data = request.get_json(silent=True) or {}
        alias = data.get('alias', '')
        sync_service.set_peer_alias(peer_id, alias)
        return {
            'message': f'Peer {peer_id} renamed to {alias}',
            'peer_id': peer_id,
            'alias': alias
        }, 200


@ns.route('/peers/<string:peer_id>/trigger-gliner')
class PeerTriggerGliner(Resource):
    @ns.expect(trigger_gliner_model, validate=True)
    def post(self, peer_id):
        """Trigger remote GLiNER model download and serving on another peer"""
        data = request.get_json(silent=True) or {}
        peer_url = data.get('peer_url')
        if not peer_url:
            return {'error': 'peer_url is required'}, 400
        result = sync_service.trigger_remote_gliner(peer_url)
        return result, 200 if result.get('success') else 502


@ns.route('/select-llm')
class SelectLlm(Resource):
    @ns.expect(select_llm_model, validate=True)
    def post(self):
        """Select which peer node serves LLM synthesis requests for this device"""
        data = request.get_json(silent=True) or {}
        endpoint = data.get('endpoint')
        sync_service.set_active_llm_provider(endpoint)
        return {
            'message': 'Active cluster LLM updated',
            'active_llm_provider': sync_service.get_active_llm_provider()
        }, 200


@ns.route('/proxy/llm', defaults={'subpath': ''})
@ns.route('/proxy/llm/<path:subpath>')
class LlamaCppProxy(Resource):
    """
    Transparent Reverse Proxy to local llama.cpp server.
    Allows any peer on LAN or Tailscale to send inference requests to this node's
    local llama-server without opening additional firewall ports.
    """
    def post(self, subpath=''):
        local_port = sync_service.get_llamacpp_local_port()
        path_str = f"/{subpath}" if subpath else "/completion"
        target_url = f"http://127.0.0.1:{local_port}{path_str}"

        try:
            req_data = request.get_json(silent=True) or {}
            resp = requests.post(
                target_url,
                json=req_data,
                headers={'Content-Type': 'application/json'},
                timeout=60
            )
            return resp.json(), resp.status_code
        except Exception as e:
            return {
                'error': f'Failed to proxy to local llama.cpp on port {local_port}: {str(e)}',
                'target_url': target_url
            }, 502

    def get(self, subpath=''):
        local_port = sync_service.get_llamacpp_local_port()
        path_str = f"/{subpath}" if subpath else "/health"
        target_url = f"http://127.0.0.1:{local_port}{path_str}"

        try:
            resp = requests.get(target_url, timeout=5)
            try:
                return resp.json(), resp.status_code
            except Exception:
                return resp.text, resp.status_code
        except Exception as e:
            return {
                'error': f'Local llama.cpp on port {local_port} unreachable: {str(e)}',
                'target_url': target_url
            }, 502
