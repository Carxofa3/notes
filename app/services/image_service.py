import os
import time
import uuid
from werkzeug.utils import secure_filename
from flask import current_app
from app.models.models import Image, Note
from app.database import db

def save_image(file, note_id):
    if not file or not file.filename:
        return None

    base_name = secure_filename(file.filename) or "upload"
    # Collision-proof filename with timestamp and short token
    unique_prefix = f"{int(time.time())}_{uuid.uuid4().hex[:8]}_"
    filename = f"{unique_prefix}{base_name}"

    upload_folder = current_app.config.get('UPLOAD_FOLDER')
    if not upload_folder:
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
    
    os.makedirs(upload_folder, exist_ok=True)

    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)

    # Associate with note in database if note exists
    try:
        if note_id and isinstance(note_id, int):
            note = db.session.get(Note, note_id)
            if note:
                new_image = Image(filename=filename, note_id=note_id)
                db.session.add(new_image)
                db.session.commit()
    except Exception as e:
        print(f"[MediaService] Note image record notice: {e}")

    return filename
