import pytest
from app import create_app
from app.database import db
from app.models import Base

@pytest.fixture(scope='function')
def app():
    app = create_app('testing')
    with app.app_context():
        Base.metadata.create_all(bind=db.engine)
        yield app
        Base.metadata.drop_all(bind=db.engine)

@pytest.fixture(scope='function')
def client(app):
    return app.test_client()
