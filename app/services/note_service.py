from app.database import db
from app.models import Note

def get_notes_by_unit(unit_id):
    return db.session.query(Note).filter(Note.unit_id == unit_id).all()

def create_note(title, content, lesson_id, unit_id):
    note = Note(title=title, content=content, lesson_id=lesson_id, unit_id=unit_id)
    db.session.add(note)
    db.session.commit()
    return note

def update_note(note_id, data):
    note = db.session.query(Note).filter(Note.id == note_id).first()
    if note:
        for key, value in data.items():
            setattr(note, key, value)
        db.session.commit()
    return note

def delete_note(note_id):
    note = db.session.query(Note).filter(Note.id == note_id).first()
    if note:
        db.session.delete(note)
        db.session.commit()
    return note