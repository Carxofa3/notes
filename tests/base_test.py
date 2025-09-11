import pytest
from app import create_app
from app.utils.database import SessionLocal, engine
from app.models.lesson import Base

@pytest.fixture(scope='module')
def app():
    app = create_app('testing')
    with app.app_context():
        Base.metadata.create_all(bind=engine)
        yield app
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope='module')
def client(app):
    return app.test_client()

@pytest.fixture(scope='function')
def db_session(app):
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()