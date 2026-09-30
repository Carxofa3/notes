import os
from dotenv import load_dotenv

load_dotenv()

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
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///notes.db'

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///notes.db'

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestConfig,
    'default': DevelopmentConfig
}