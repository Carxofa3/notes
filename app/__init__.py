from flask import Flask, Blueprint, send_from_directory, render_template
from flask_migrate import Migrate
from flask_cors import CORS
from .database import db
from config.config import config
import os

migrate = Migrate()

def create_app(config_name='default'):
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')
    app.config.from_object(config[config_name])

    # Enable CORS for all routes (essential for Android mobile app & remote peer mesh)
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

    db.init_app(app)
    migrate.init_app(app, db)

    # Automatically create tables if not present (crucial for standalone .exe and fresh installs)
    with app.app_context():
        try:
            from .models import models as _models  # noqa: F401 - ensures all models are loaded
            db.create_all()
        except Exception as e:
            print(f"[Database] Warning during auto-table creation: {e}")

    # Register API blueprints
    from .api import api_bp
    from .api.decide import decide_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(decide_bp) # Registers /v1/decide at root

    # Legacy webui static folder for backward compatibility
    webui_bp = Blueprint('webui', __name__, static_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'webui', 'static')), static_url_path='/webui/static')
    app.register_blueprint(webui_bp)

    # Modern frontend SPA dist directory
    dist_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist'))

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        if path.startswith('api') or path.startswith('v1') or path.startswith('webui'):
            return {'message': 'Not found'}, 404
        
        target_file = os.path.join(dist_dir, path)
        if path and os.path.exists(target_file):
            return send_from_directory(dist_dir, path)
        
        # If dist/index.html exists, serve modern Svelte SPA
        dist_index = os.path.join(dist_dir, 'index.html')
        if os.path.exists(dist_index):
            return send_from_directory(dist_dir, 'index.html')
            
        # Fallback to legacy index.html template if dist not built yet
        return render_template('index.html')

    return app
