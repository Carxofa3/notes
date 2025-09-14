import colorsys
import json
from app.models.models import Settings
from app.database import db
from datetime import datetime

class SettingsService:
    
    @staticmethod
    def get_user_settings(user_id='default'):
        """Get settings for a specific user"""
        settings = Settings.query.filter_by(user_id=user_id).first()
        if not settings:
            # Create default settings if none exist
            settings = SettingsService.create_default_settings(user_id)
        
        return {
            'id': settings.id,
            'user_id': settings.user_id,
            'primary_color': settings.primary_color,
            'color_palette': settings.color_palette,
            'dark_mode': settings.dark_mode,
            'custom_css': settings.custom_css,
            'editor_font_family': settings.editor_font_family,
            'editor_font_size': settings.editor_font_size,
            'editor_line_height': settings.editor_line_height,
            'auto_save_interval': settings.auto_save_interval,
            'spell_check': settings.spell_check,
            'auto_detect_titles': settings.auto_detect_titles,
            'auto_generate_schema': settings.auto_generate_schema,
            'default_note_color': settings.default_note_color,
            'export_format': settings.export_format,
            'image_quality': settings.image_quality,
            'max_image_size': settings.max_image_size,
            # AI settings
            'ai_base_url': settings.ai_base_url,
            'ai_api_key': '***' if settings.ai_api_key else None,  # Hide actual key
            'ai_model': settings.ai_model,
            'ai_embedding_model': settings.ai_embedding_model,
            'ai_enabled': settings.ai_enabled,
            'ai_auto_format': settings.ai_auto_format,
            'search_enabled': settings.search_enabled,
            'max_search_results': settings.max_search_results,
            'created_at': settings.created_at.isoformat() if settings.created_at else None,
            'updated_at': settings.updated_at.isoformat() if settings.updated_at else None
        }
    
    @staticmethod
    def create_default_settings(user_id='default'):
        """Create default settings for a user"""
        primary_color = '#4299e1'
        color_palette = SettingsService.generate_color_palette(primary_color)
        
        settings = Settings(
            user_id=user_id,
            primary_color=primary_color,
            color_palette=color_palette
        )
        
        db.session.add(settings)
        db.session.commit()
        return settings
    
    @staticmethod
    def update_settings(user_id, data):
        """Update user settings"""
        settings = Settings.query.filter_by(user_id=user_id).first()
        if not settings:
            settings = SettingsService.create_default_settings(user_id)
        
        # Update fields if provided
        updateable_fields = [
            'primary_color', 'dark_mode', 'custom_css',
            'editor_font_family', 'editor_font_size', 'editor_line_height',
            'auto_save_interval', 'spell_check', 'auto_detect_titles',
            'auto_generate_schema', 'default_note_color', 'export_format',
            'image_quality', 'max_image_size',
            # AI settings
            'ai_base_url', 'ai_api_key', 'ai_model', 'ai_embedding_model',
            'ai_enabled', 'ai_auto_format', 'search_enabled', 'max_search_results'
        ]
        
        for field in updateable_fields:
            if field in data:
                setattr(settings, field, data[field])
        
        # Generate new palette if primary color changed
        if 'primary_color' in data:
            color_palette = SettingsService.generate_color_palette(data['primary_color'])
            settings.color_palette = color_palette
        
        settings.updated_at = datetime.utcnow()
        db.session.commit()
        
        return SettingsService.get_user_settings(user_id)
    
    @staticmethod
    def generate_color_palette(primary_color):
        """Generate a complementary color palette from a primary color"""
        try:
            # Remove # if present
            hex_color = primary_color.lstrip('#')
            
            # Convert hex to RGB
            r = int(hex_color[0:2], 16) / 255.0
            g = int(hex_color[2:4], 16) / 255.0
            b = int(hex_color[4:6], 16) / 255.0
            
            # Convert to HSV
            h, s, v = colorsys.rgb_to_hsv(r, g, b)
            
            # Generate complementary colors
            palette = {
                'primary': primary_color,
                'secondary': SettingsService._hsv_to_hex((h + 0.33) % 1, s, v),  # Triadic
                'accent': SettingsService._hsv_to_hex((h + 0.66) % 1, s, v),     # Triadic
                'light': SettingsService._hsv_to_hex(h, s * 0.3, min(v + 0.3, 1)),  # Lighter version
                'dark': SettingsService._hsv_to_hex(h, s, max(v - 0.3, 0)),     # Darker version
                'muted': SettingsService._hsv_to_hex(h, s * 0.5, v),           # Muted version
                'complementary': SettingsService._hsv_to_hex((h + 0.5) % 1, s, v), # True complement
                'analogous_1': SettingsService._hsv_to_hex((h + 0.08) % 1, s, v), # Analogous colors
                'analogous_2': SettingsService._hsv_to_hex((h - 0.08) % 1, s, v),
            }
            
            # Add tints and shades
            palette.update({
                'tint_1': SettingsService._hsv_to_hex(h, s * 0.8, min(v + 0.1, 1)),
                'tint_2': SettingsService._hsv_to_hex(h, s * 0.6, min(v + 0.2, 1)),
                'shade_1': SettingsService._hsv_to_hex(h, s, max(v - 0.1, 0)),
                'shade_2': SettingsService._hsv_to_hex(h, s, max(v - 0.2, 0)),
            })
            
            return palette
            
        except Exception as e:
            # Return default palette if generation fails
            return {
                'primary': '#4299e1',
                'secondary': '#38b2ac',
                'accent': '#ed64a6',
                'light': '#ebf8ff',
                'dark': '#2c5282',
                'muted': '#90cdf4',
                'complementary': '#e1a142',
                'analogous_1': '#4299e1',
                'analogous_2': '#4299e1',
                'tint_1': '#63b3ed',
                'tint_2': '#90cdf4',
                'shade_1': '#3182ce',
                'shade_2': '#2c5282'
            }
    
    @staticmethod
    def _hsv_to_hex(h, s, v):
        """Convert HSV to hex color"""
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
    
    @staticmethod
    def reset_to_defaults(user_id):
        """Reset user settings to default values"""
        settings = Settings.query.filter_by(user_id=user_id).first()
        if settings:
            db.session.delete(settings)
            db.session.commit()
        
        # Create new default settings
        return SettingsService.create_default_settings(user_id)
    
    @staticmethod
    def export_settings(user_id):
        """Export user settings as a dictionary"""
        settings = SettingsService.get_user_settings(user_id)
        # Remove internal fields
        export_data = {k: v for k, v in settings.items() if k not in ['id', 'created_at', 'updated_at']}
        return export_data
    
    @staticmethod
    def import_settings(user_id, settings_data):
        """Import user settings from a dictionary"""
        # Validate and update settings
        return SettingsService.update_settings(user_id, settings_data)
