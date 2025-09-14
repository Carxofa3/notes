from flask import Flask
from flask_migrate import Migrate
from .database import db
from config.config import config

migrate = Migrate()

def create_app(config_name='default'):
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')
    app.config.from_object(config[config_name])

    db.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints here
    from .api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    return app
