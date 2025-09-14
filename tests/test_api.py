# tests/test_api.py
import pytest
from app import create_app, db

@pytest.fixture
def app():
    app = create_app(config_name='testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

# --- Lesson Tests ---

def test_get_lessons_empty(client):
    """Test getting lessons when there are none."""
    response = client.get('/api/lessons/')
    assert response.status_code == 200
    assert response.json == []

def test_create_lesson(client):
    """Test creating a new lesson."""
    response = client.post('/api/lessons/', json={'name': 'Test Lesson'})
    assert response.status_code == 201
    assert response.json['name'] == 'Test Lesson'

    response = client.get('/api/lessons/')
    assert response.status_code == 200
    assert len(response.json) == 1
    assert response.json[0]['name'] == 'Test Lesson'

def test_create_lesson_no_name(client):
    """Test creating a lesson with no name."""
    response = client.post('/api/lessons/', json={})
    assert response.status_code == 400

def test_get_lesson_by_id(client):
    """Test getting a single lesson by its ID."""
    post_response = client.post('/api/lessons/', json={'name': 'Another Test Lesson'})
    lesson_id = post_response.json['id']
    response = client.get(f'/api/lessons/{lesson_id}')
    assert response.status_code == 200
    assert response.json['name'] == 'Another Test Lesson'

def test_get_lesson_not_found(client):
    """Test getting a lesson that does not exist."""
    response = client.get('/api/lessons/999')
    assert response.status_code == 404

# --- Settings Tests ---

def test_get_settings_empty(client):
    """Test getting settings when there are none."""
    response = client.get('/api/settings/')
    assert response.status_code == 200
    assert response.json == {}

def test_update_setting(client):
    """Test creating and updating a setting."""
    # Create a new setting
    response = client.post('/api/settings/', json={'key': 'test_key', 'value': 'test_value'})
    assert response.status_code == 200
    assert response.json['message'] == 'Setting updated successfully'

    # Verify the setting was created
    response = client.get('/api/settings/')
    assert response.status_code == 200
    assert response.json['test_key'] == 'test_value'

    # Update the setting
    response = client.post('/api/settings/', json={'key': 'test_key', 'value': 'new_value'})
    assert response.status_code == 200

    # Verify the setting was updated
    response = client.get('/api/settings/')
    assert response.status_code == 200
    assert response.json['test_key'] == 'new_value'
