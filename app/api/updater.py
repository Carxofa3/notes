# app/api/updater.py
"""
Auto-Updater & Release Inspector API.
Checks GitHub releases for Notes Workstation and identifies the exact right asset for the client.
"""

from flask import request
from flask_restx import Namespace, Resource
from app.services.updater_service import updater_service

ns = Namespace('updater', description='Auto-Updater and GitHub Release Inspector')


@ns.route('/check')
class UpdaterCheck(Resource):
    def get(self):
        """
        Check for newer application releases on GitHub.
        Automatically recommends the correct asset for Windows, Android, or Linux.
        Optional query parameter: ?platform=windows|android|linux
        """
        platform_override = request.args.get('platform')
        user_agent = request.headers.get('User-Agent', '')

        # Auto-detect Android if query param omitted but request comes from Android WebView
        if not platform_override and 'Android' in user_agent:
            platform_override = 'android'

        result = updater_service.check_for_updates(platform_override)
        return result, 200


@ns.route('/version')
class AppVersion(Resource):
    def get(self):
        """Get currently running version of the application backend."""
        return {
            "version": updater_service.get_current_version(),
            "app_name": "Notes Workstation"
        }, 200
