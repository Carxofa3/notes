from flask import Flask
from config.config import config
from app.controllers.main_controller import main_blueprint
from app.controllers.lessons_controller import lessons_blueprint
from app.controllers.units_controller import units_blueprint
from app.controllers.notes_controller import notes_blueprint

def create_app(config_name='default'):
    app = Flask(__name__, template_folder='../webui/templates', static_folder='../webui/static')
    app.config.from_object(config[config_name])

    app.register_blueprint(main_blueprint)
    app.register_blueprint(lessons_blueprint, url_prefix='/api')
    app.register_blueprint(units_blueprint, url_prefix='/api')
    app.register_blueprint(notes_blueprint, url_prefix='/api')

    return app
