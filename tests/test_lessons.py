import json
from tests.base_test import client, db_session
from app.models.lesson import Lesson

def test_get_lessons(client, db_session):
    lesson1 = Lesson(title='Lesson 1', description='Description 1')
    lesson2 = Lesson(title='Lesson 2', description='Description 2')
    db_session.add_all([lesson1, lesson2])
    db_session.commit()

    response = client.get('/api/lessons')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2

def test_create_lesson(client, db_session):
    response = client.post('/api/lessons', json={'title': 'New Lesson', 'description': 'New Description'})
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['title'] == 'New Lesson'
    assert db_session.query(Lesson).count() == 1

def test_update_lesson(client, db_session):
    lesson = Lesson(title='Old Title', description='Old Description')
    db_session.add(lesson)
    db_session.commit()

    response = client.put(f'/api/lessons/{lesson.id}', json={'title': 'New Title'})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == 'New Title'
    db_session.refresh(lesson)
    assert lesson.title == 'New Title'

def test_delete_lesson(client, db_session):
    lesson = Lesson(title='Lesson to delete', description='description')
    db_session.add(lesson)
    db_session.commit()

    response = client.delete(f'/api/lessons/{lesson.id}')
    assert response.status_code == 200
    assert db_session.query(Lesson).count() == 0