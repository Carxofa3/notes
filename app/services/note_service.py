import os
import re
import json
from datetime import datetime
from app.database import db
from app.models import Note
from app.utils.text_processing import TextProcessor

class NoteService:
    
    @staticmethod
    def get_notes_by_unit(unit_id):
        return db.session.query(Note).filter(Note.unit_id == unit_id).all()
    
    @staticmethod
    def create_note(title, content, lesson_id, unit_id, auto_process=True):
        """Create a new note with optional auto-processing"""
        note = Note(title=title, content=content, lesson_id=lesson_id, unit_id=unit_id)
        
        if auto_process:
            NoteService._process_note_content(note)
        
        db.session.add(note)
        db.session.commit()
        return note
    
    @staticmethod
    def update_note(note_id, data, auto_process=True):
        """Update a note with optional auto-processing"""
        note = db.session.query(Note).filter(Note.id == note_id).first()
        if note:
            # Update basic fields
            for key, value in data.items():
                if hasattr(note, key):
                    setattr(note, key, value)
            
            # Auto-process content if it changed
            if auto_process and ('content' in data or 'formatted_content' in data):
                NoteService._process_note_content(note)
            
            note.updated_at = datetime.utcnow()
            db.session.commit()
        return note
    
    @staticmethod
    def delete_note(note_id):
        """Delete a note and clean up associated images"""
        note = db.session.query(Note).filter(Note.id == note_id).first()
        if note:
            # Clean up attached images
            if note.attached_images:
                for image in note.attached_images:
                    NoteService._delete_image_file(image)
            
            db.session.delete(note)
            db.session.commit()
        return note
    
    @staticmethod
    def attach_image(note_id, image_info):
        """Attach an image to a note"""
        note = db.session.query(Note).filter(Note.id == note_id).first()
        if not note:
            raise Exception("Note not found")
        
        # Initialize attached_images if None
        if note.attached_images is None:
            note.attached_images = []
        
        # Add image info to the list
        attached_images = note.attached_images.copy() if note.attached_images else []
        attached_images.append(image_info)
        note.attached_images = attached_images
        
        note.updated_at = datetime.utcnow()
        db.session.commit()
        return note
    
    @staticmethod
    def remove_image(note_id, image_id):
        """Remove an image from a note"""
        note = db.session.query(Note).filter(Note.id == note_id).first()
        if not note:
            raise Exception("Note not found")
        
        if note.attached_images:
            # Find and remove the image
            original_count = len(note.attached_images)
            attached_images = [img for img in note.attached_images if img.get('id') != image_id]
            
            if len(attached_images) < original_count:
                # Find the deleted image info for file cleanup
                deleted_image = next((img for img in note.attached_images if img.get('id') == image_id), None)
                if deleted_image:
                    NoteService._delete_image_file(deleted_image)
                
                note.attached_images = attached_images
                note.updated_at = datetime.utcnow()
                db.session.commit()
                return {'success': True, 'deleted_image': deleted_image}
        
        raise Exception("Image not found")
    
    @staticmethod
    def get_note_images(note_id):
        """Get all images attached to a note"""
        note = db.session.query(Note).filter(Note.id == note_id).first()
        if not note:
            raise Exception("Note not found")
        
        return note.attached_images or []
    
    @staticmethod
    def _process_note_content(note):
        """Process note content for auto-detection and metadata"""
        try:
            # Auto-detect title if enabled
            if not note.auto_title or note.title.startswith('Note '):
                detected_title = TextProcessor.detect_title(note.content)
                if detected_title:
                    note.auto_title = detected_title
            
            # Detect headings and generate schema
            headings = TextProcessor.extract_headings(note.content)
            note.detected_headings = headings
            
            # Generate content schema
            schema = TextProcessor.generate_content_schema(note.content)
            note.content_schema = schema
            
            # Calculate word count and reading time
            note.word_count = TextProcessor.count_words(note.content)
            note.reading_time = TextProcessor.estimate_reading_time(note.content)
            
        except Exception as e:
            print(f"Error processing note content: {e}")
    
    @staticmethod
    def _delete_image_file(image_info):
        """Delete an image file from the filesystem"""
        try:
            if 'filename' in image_info:
                file_path = os.path.join('webui/static/uploads', image_info['filename'])
                if os.path.exists(file_path):
                    os.remove(file_path)
        except Exception as e:
            print(f"Error deleting image file: {e}")
    
    @staticmethod
    def get_note_by_id(note_id):
        """Get a single note by ID"""
        return db.session.query(Note).filter(Note.id == note_id).first()
    
    @staticmethod
    def search_notes(query, lesson_id=None, unit_id=None):
        """Search notes by content or title"""
        search = db.session.query(Note).filter(
            Note.content.ilike(f'%{query}%') | Note.title.ilike(f'%{query}%')
        )
        
        if lesson_id:
            search = search.filter(Note.lesson_id == lesson_id)
        if unit_id:
            search = search.filter(Note.unit_id == unit_id)
        
        return search.all()

# Legacy function compatibility
def get_notes_by_unit(unit_id):
    return NoteService.get_notes_by_unit(unit_id)

def create_note(title, content, lesson_id, unit_id):
    return NoteService.create_note(title, content, lesson_id, unit_id)

def update_note(note_id, data):
    return NoteService.update_note(note_id, data)

def delete_note(note_id):
    return NoteService.delete_note(note_id)
