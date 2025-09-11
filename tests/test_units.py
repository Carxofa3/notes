import json
from tests.base_test import client, db_session
from app.models.lesson import Lesson
from app.models.unit import Unit

def test_get_units(client, db_session):
    lesson = Lesson(title='Lesson 1', description='Description 1')
    unit1 = Unit(title='Unit 1', lesson=lesson)
    unit2 = Unit(title='Unit 2', lesson=lesson)
    db_session.add_all([lesson, unit1, unit2])
    db_session.commit()

    response = client.get(f'/api/units?lesson_id={lesson.id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2

def test_create_unit(client, db_session):
    lesson = Lesson(title='Lesson 1', description='Description 1')
    db_session.add(lesson)
    db_session.commit()

    response = client.post('/api/units', json={'title': 'New Unit', 'lesson_id': lesson.id})
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['title'] == 'New Unit'
    assert db_session.query(Unit).count() == 1

def test_update_unit(client, db_session):
    lesson = Lesson(title='Lesson 1', description='Description 1')
    unit = Unit(title='Old Title', lesson=lesson)
    db_session.add_all([lesson, unit])
    db_session.commit()

    response = client.put(f'/api/units/{unit.id}', json={'title': 'New Title'})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == 'New Title'
    db_session.refresh(unit)
    assert unit.title == 'New Title'

def test_delete_unit(client, db_session):
    lesson = Lesson(title='Lesson 1', description='Description 1')
    unit = Unit(title='Unit to delete', lesson=lesson)
    db_session.add_all([lesson, unit])
    db_session.commit()

    response = client.delete(f'/api/units/{unit.id}')
    assert response.status_code == 200
    assert db_session.query(Unit).count() == 0