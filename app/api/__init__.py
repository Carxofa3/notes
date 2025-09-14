from flask import Blueprint
from flask_restx import Api

from .lessons import ns as lessons_ns
from .units import ns as units_ns
from .notes import ns as notes_ns
from .ai import ns as ai_ns
from .images import ns as images_ns
from .settings import ns as settings_ns

api_bp = Blueprint('api', __name__)

authorizations = {
    'apikey': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'X-API-KEY'
    }
}

api = Api(
    api_bp,
    title='Notes App API',
    version='1.0',
    description='A comprehensive API for the Notes App',
    authorizations=authorizations,
    security='apikey'
)

api.add_namespace(lessons_ns, path='/lessons')
api.add_namespace(units_ns, path='/units')
api.add_namespace(notes_ns, path='/notes')
api.add_namespace(ai_ns, path='/ai')
api.add_namespace(images_ns, path='/images')
api.add_namespace(settings_ns, path='/settings')
