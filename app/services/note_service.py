from app.utils.database import get_db
from app.models.note import Note

def get_notes_by_unit(unit_id):
    db = next(get_db())
    return db.query(Note).filter(Note.unit_id == unit_id).all()

def create_note(title, content, lesson_id, unit_id):
    db = next(get_db())
    note = Note(title=title, content=content, lesson_id=lesson_id, unit_id=unit_id)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note

def update_note(note_id, data):
    db = next(get_db())
    note = db.query(Note).filter(Note.id == note_id).first()
    if note:
        for key, value in data.items():
            setattr(note, key, value)
        db.commit()
        db.refresh(note)
    return note

def delete_note(note_id):
    db = next(get_db())
    note = db.query(Note).filter(Note.id == note_id).first()
    if note:
        db.delete(note)
        db.commit()
    return note