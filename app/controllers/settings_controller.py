from flask import Blueprint, request, jsonify
from app.services.settings_service import SettingsService
from app.utils.responses import success_response, error_response

settings_blueprint = Blueprint('settings', __name__)

@settings_blueprint.route('/settings', methods=['GET'])
def get_settings():
    """Get current user settings"""
    try:
        user_id = request.args.get('user_id', 'default')
        settings = SettingsService.get_user_settings(user_id)
        return success_response(data=settings)
    except Exception as e:
        return error_response(f"Failed to retrieve settings: {str(e)}")

@settings_blueprint.route('/settings', methods=['POST'])
def update_settings():
    """Update user settings"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        
        # Validate color if provided
        if 'primary_color' in data:
            if not data['primary_color'].startswith('#') or len(data['primary_color']) != 7:
                return error_response("Invalid color format. Use hex format (#RRGGBB)")
        
        settings = SettingsService.update_settings(user_id, data)
        return success_response(data=settings, message="Settings updated successfully")
    except Exception as e:
        return error_response(f"Failed to update settings: {str(e)}")

@settings_blueprint.route('/settings/generate-palette', methods=['POST'])
def generate_color_palette():
    """Generate complementary color palette from primary color"""
    try:
        data = request.get_json()
        primary_color = data.get('primary_color')
        
        if not primary_color:
            return error_response("Primary color is required")
        
        palette = SettingsService.generate_color_palette(primary_color)
        return success_response(data={'palette': palette})
    except Exception as e:
        return error_response(f"Failed to generate color palette: {str(e)}")

@settings_blueprint.route('/settings/reset', methods=['POST'])
def reset_settings():
    """Reset settings to default values"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        
        settings = SettingsService.reset_to_defaults(user_id)
        return success_response(data=settings, message="Settings reset to defaults")
    except Exception as e:
        return error_response(f"Failed to reset settings: {str(e)}")

@settings_blueprint.route('/settings/export', methods=['GET'])
def export_settings():
    """Export user settings as JSON"""
    try:
        user_id = request.args.get('user_id', 'default')
        settings = SettingsService.export_settings(user_id)
        return success_response(data=settings)
    except Exception as e:
        return error_response(f"Failed to export settings: {str(e)}")

@settings_blueprint.route('/settings/import', methods=['POST'])
def import_settings():
    """Import user settings from JSON"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        settings_data = data.get('settings')
        
        if not settings_data:
            return error_response("Settings data is required")
        
        settings = SettingsService.import_settings(user_id, settings_data)
        return success_response(data=settings, message="Settings imported successfully")
    except Exception as e:
        return error_response(f"Failed to import settings: {str(e)}")
