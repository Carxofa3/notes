import os
from dotenv import load_dotenv

load_dotenv()

def get_database_uri():
    if os.environ.get('DATABASE_URL'):
        return os.environ.get('DATABASE_URL')
    
    # 1. If notes.db exists in current working directory, use it
    local_db = os.path.join(os.getcwd(), 'notes.db')
    if os.path.exists(local_db):
        clean_local = local_db.replace('\\', '/')
        return f"sqlite:///{clean_local}"
    
    # 2. Otherwise, store in persistent user home directory (~/.notes_workstation/notes.db)
    # This prevents SQLite database loss when running standalone portable EXEs
    data_dir = os.path.join(os.path.expanduser('~'), '.notes_workstation')
    try:
        os.makedirs(data_dir, exist_ok=True)
        user_db = os.path.join(data_dir, 'notes.db').replace('\\', '/')
        return f"sqlite:///{user_db}"
    except Exception:
        return 'sqlite:///notes.db'

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_API_BASE = os.environ.get('LLM_API_BASE')
    LLAMA_CPP_NODE = os.environ.get('LLAMA_CPP_NODE') or os.environ.get('TAILSCALE_LLM_NODE') or 'http://localhost:8080'
    LLM_MODEL = os.environ.get('LLM_MODEL') or 'default'
    EMBEDDINGS_API_KEY = os.environ.get('EMBEDDINGS_API_KEY')
    EMBEDDINGS_API_BASE = os.environ.get('EMBEDDINGS_API_BASE')
    EMBEDDINGS_MODEL = os.environ.get('EMBEDDINGS_MODEL') or 'text-embedding-ada-002'
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'app', 'static', 'uploads')

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = get_database_uri()

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = get_database_uri()

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestConfig,
    'default': DevelopmentConfig
}