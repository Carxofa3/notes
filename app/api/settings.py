from flask_restx import Namespace, Resource, fields
from app.services import settings_service

ns = Namespace('settings', description='Application settings operations')

setting_model = ns.model('Setting', {
    'key': fields.String(required=True, description='The setting key'),
    'value': fields.Raw(required=True, description='The setting value'),
})

@ns.route('/')
class Settings(Resource):
    @ns.doc('get_all_settings')
    def get(self):
        """Get all settings"""
        return settings_service.get_all_settings()

    @ns.doc('update_setting')
    @ns.expect(setting_model)
    def post(self):
        """Update a setting"""
        data = ns.payload
        key = data.get('key')
        value = data.get('value')
        # The key is validated by the model
        settings_service.update_setting(key, value)
        return {'message': 'Setting updated successfully'}, 200
