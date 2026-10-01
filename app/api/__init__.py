from flask import Blueprint
from flask_restx import Api

from .lessons import ns as lessons_ns
from .units import ns as units_ns
from .notes import ns as notes_ns
from .ai import ns as ai_ns
from .images import ns as images_ns
from .settings import ns as settings_ns
from .rag import ns as rag_ns
from .sync import ns as sync_ns
from .academic import ns as academic_ns
from .decide import ns as decide_ns, decide_bp
from .gliner import ns as gliner_ns
from .nodes import ns as nodes_ns
from .updater import ns as updater_ns

api_bp = Blueprint('api', __name__)

authorizations = {
    'apikey': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization',
        'description': 'Bearer token provided in the desktop pairing QR code'
    }
}

api = Api(
    api_bp,
    title='University Notes App API',
    version='2.1',
    description='A comprehensive API for university lecture notes, local course RAG, Tailscale P2P sync, and autonomous fact-checking',
    authorizations=authorizations,
    security='apikey'
)

api.add_namespace(lessons_ns, path='/lessons')
api.add_namespace(units_ns, path='/units')
api.add_namespace(notes_ns, path='/notes')
api.add_namespace(ai_ns, path='/ai')
api.add_namespace(images_ns, path='/images')
api.add_namespace(settings_ns, path='/settings')
api.add_namespace(rag_ns, path='/rag')
api.add_namespace(sync_ns, path='/sync')
api.add_namespace(academic_ns, path='/academic')
api.add_namespace(decide_ns, path='/decide')
api.add_namespace(gliner_ns, path='/gliner')
api.add_namespace(nodes_ns, path='/nodes')
api.add_namespace(updater_ns, path='/updater')
