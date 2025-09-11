from flask import Flask
from config.config import config
from app.database import db
from app.controllers.main_controller import main_blueprint
from app.controllers.lessons_controller import lessons_blueprint
from app.controllers.units_controller import units_blueprint
from app.controllers.notes_controller import notes_blueprint
from app.controllers.settings_controller import settings_blueprint
from app.controllers.images_controller import images_blueprint
from app.controllers.ai_controller import ai_blueprint
from app.controllers.lessons_units_controller import lessons_units_blueprint

def create_app(config_name='default'):
    app = Flask(__name__, template_folder='../webui/templates', static_folder='../webui/static')
    app.config.from_object(config[config_name])

    db.init_app(app)

    app.register_blueprint(main_blueprint)
    app.register_blueprint(lessons_blueprint, url_prefix='/api')
    app.register_blueprint(units_blueprint, url_prefix='/api')
    app.register_blueprint(notes_blueprint, url_prefix='/api')
    app.register_blueprint(settings_blueprint, url_prefix='/api')
    app.register_blueprint(images_blueprint, url_prefix='/api/images')
    app.register_blueprint(ai_blueprint, url_prefix='/api/ai')
    app.register_blueprint(lessons_units_blueprint, url_prefix='/api')

    return app
