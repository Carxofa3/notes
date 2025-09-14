from flask import Blueprint, request, jsonify
from app.services.ai_service import AIService
from app.utils.responses import success_response, error_response

ai_blueprint = Blueprint('ai', __name__)

@ai_blueprint.route('/test-connection', methods=['POST'])
def test_ai_connection():
    """Test connection to AI API"""
    try:
        data = request.get_json()
        base_url = data.get('base_url')
        api_key = data.get('api_key')
        
        if not base_url or not api_key:
            return error_response("Base URL and API key are required")
        
        result = AIService.test_api_connection(base_url, api_key)
        
        if result['success']:
            return success_response(data=result, message="Connection successful")
        else:
            return error_response(result['error'])
            
    except Exception as e:
        return error_response(f"Connection test failed: {str(e)}")

@ai_blueprint.route('/format-note/<int:note_id>', methods=['POST'])
def format_note(note_id):
    """Format note content using AI"""
    try:
        result = AIService.format_note_content(note_id)
        
        if result['success']:
            return success_response(data=result, message="Note formatted successfully")
        else:
            return error_response(result['error'])
            
    except Exception as e:
        return error_response(f"Formatting failed: {str(e)}")

@ai_blueprint.route('/embed-note/<int:note_id>', methods=['POST'])
def embed_note(note_id):
    """Generate embeddings for a specific note"""
    try:
        result = AIService.embed_note(note_id)
        
        if result['success']:
            return success_response(data=result, message="Embeddings generated successfully")
        else:
            return error_response(result['error'])
            
    except Exception as e:
        return error_response(f"Embedding failed: {str(e)}")

@ai_blueprint.route('/search', methods=['GET'])
def search_notes():
    """Search notes using semantic similarity"""
    try:
        query = request.args.get('q', '').strip()
        limit = int(request.args.get('limit', 10))
        
        if not query:
            return success_response(data={'results': []})
        
        result = AIService.search_notes(query, limit)
        
        if result['success']:
            return success_response(data=result)
        else:
            return error_response(result['error'])
            
    except Exception as e:
        return error_response(f"Search failed: {str(e)}")

@ai_blueprint.route('/batch-embed', methods=['POST'])
def batch_embed_notes():
    """Generate embeddings for all notes"""
    try:
        result = AIService.batch_embed_all_notes()
        
        if result['success']:
            return success_response(data=result, message="Batch embedding completed")
        else:
            return error_response(result['error'])
            
    except Exception as e:
        return error_response(f"Batch embedding failed: {str(e)}")
