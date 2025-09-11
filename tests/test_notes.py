import json
from tests.base_test import client, db_session
from app.models.lesson import Lesson
from app.models.unit import Unit
from app.models.note import Note

def test_get_notes(client, db_session):
    lesson = Lesson(title='Lesson 1', description='Description 1')
    unit = Unit(title='Unit 1', lesson=lesson)
    note1 = Note(title='Note 1', content='Content 1', lesson=lesson, unit=unit)
    note2 = Note(title='Note 2', content='Content 2', lesson=lesson, unit=unit)
    db_session.add_all([lesson, unit, note1, note2])
    db_session.commit()

    response = client.get(f'/api/notes?unit_id={unit.id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2

def test_create_note(client, db_session):
    lesson = Lesson(title='Lesson 1', description='Description 1')
    unit = Unit(title='Unit 1', lesson=lesson)
    db_session.add_all([lesson, unit])
    db_session.commit()

    response = client.post('/api/notes', json={'title': 'New Note', 'content': 'New Content', 'lesson_id': lesson.id, 'unit_id': unit.id})
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['title'] == 'New Note'
    assert db_session.query(Note).count() == 1

def test_update_note(client, db_session):
    lesson = Lesson(title='Lesson 1', description='Description 1')
    unit = Unit(title='Unit 1', lesson=lesson)
    note = Note(title='Old Title', content='Old Content', lesson=lesson, unit=unit)
    db_session.add_all([lesson, unit, note])
    db_session.commit()

    response = client.put(f'/api/notes/{note.id}', json={'title': 'New Title'})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == 'New Title'
    db_session.refresh(note)
    assert note.title == 'New Title'

def test_delete_note(client, db_session):
    lesson = Lesson(title='Lesson 1', description='Description 1')
    unit = Unit(title='Unit 1', lesson=lesson)
    note = Note(title='Note to delete', content='Content', lesson=lesson, unit=unit)
    db_session.add_all([lesson, unit, note])
    db_session.commit()

    response = client.delete(f'/api/notes/{note.id}')
    assert response.status_code == 200
    assert db_session.query(Note).count() == 0