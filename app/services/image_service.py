import os
from werkzeug.utils import secure_filename
from flask import current_app
from app.models.models import Image
from app.database import db

def save_image(file, note_id):
    if not file or not file.filename:
        return None

    filename = secure_filename(file.filename)
    upload_folder = current_app.config.get('UPLOAD_FOLDER')
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)

    new_image = Image(filename=filename, note_id=note_id)
    db.session.add(new_image)
    db.session.commit()

    return filename
