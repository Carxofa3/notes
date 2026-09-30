# app/services/note_service.py
from app.database import db
from app.models.models import Note, Unit, Embedding
from app.services import ai_service

def get_all_notes_for_unit(unit_id):
    unit = Unit.query.get_or_404(unit_id)
    return unit.notes

def get_note_by_id(note_id):
    return Note.query.get_or_404(note_id)

def update_note_embeddings(note):
    """Generates and stores embeddings for the note content safely."""
    try:
        # Clear existing embeddings for the note
        Embedding.query.filter_by(note_id=note.id).delete()

        if note.content:
            phrase = note.content
            vector = ai_service.embed_text(phrase)
            if vector:
                embedding = Embedding(note_id=note.id, phrase=phrase, vector=vector)
                db.session.add(embedding)
    except Exception as e:
        # Graceful fallback: local offline note taking must never crash on embedding failure
        pass

def create_note(unit_id, data):
    unit = Unit.query.get_or_404(unit_id)
    new_note = Note(
        title=data.get('title'),
        content=data.get('content'),
        unit_id=unit.id
    )
    db.session.add(new_note)
    db.session.flush()  # Flush to get the new_note.id before creating embeddings
    update_note_embeddings(new_note)
    db.session.commit()
    return new_note

def update_note(note_id, data):
    note = get_note_by_id(note_id)
    note.title = data.get('title', note.title)
    note.content = data.get('content', note.content)
    # AI formatted content will be handled by the AI service
    update_note_embeddings(note)
    db.session.commit()
    return note

def delete_note(note_id):
    note = get_note_by_id(note_id)
    db.session.delete(note)
    db.session.commit()
