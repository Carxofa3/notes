import os
import uuid
from flask import Blueprint, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from PIL import Image
import io
from app.services.note_service import NoteService
from app.utils.responses import success_response, error_response

images_blueprint = Blueprint('images', __name__)

# Configuration
UPLOAD_FOLDER = 'webui/static/uploads'
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def optimize_image(image_data, quality='medium'):
    """Optimize image based on quality setting"""
    try:
        image = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if necessary
        if image.mode in ('RGBA', 'P'):
            image = image.convert('RGB')
        
        # Quality settings
        quality_map = {
            'low': {'quality': 60, 'max_size': (800, 600)},
            'medium': {'quality': 80, 'max_size': (1200, 900)},
            'high': {'quality': 95, 'max_size': (1920, 1440)}
        }
        
        settings = quality_map.get(quality, quality_map['medium'])
        
        # Resize if too large
        image.thumbnail(settings['max_size'], Image.Resampling.LANCZOS)
        
        # Save optimized image
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=settings['quality'], optimize=True)
        return output.getvalue()
        
    except Exception as e:
        raise Exception(f"Image optimization failed: {str(e)}")

@images_blueprint.route('/upload', methods=['POST'])
def upload_image():
    """Upload and attach image to a note"""
    try:
        if 'file' not in request.files:
            return error_response("No file provided")
        
        file = request.files['file']
        note_id = request.form.get('note_id')
        quality = request.form.get('quality', 'medium')
        
        if file.filename == '':
            return error_response("No file selected")
        
        if not allowed_file(file.filename):
            return error_response("File type not allowed. Supported: PNG, JPG, JPEG, GIF, WEBP, SVG")
        
        # Check file size
        file_data = file.read()
        if len(file_data) > MAX_FILE_SIZE:
            return error_response("File too large. Maximum size is 5MB")
        
        file.seek(0)  # Reset file pointer
        
        # Create unique filename
        file_extension = secure_filename(file.filename).rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
        
        # Ensure upload directory exists
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        
        # Optimize image (except SVG)
        if file_extension.lower() != 'svg':
            try:
                optimized_data = optimize_image(file_data, quality)
                with open(file_path, 'wb') as f:
                    f.write(optimized_data)
            except Exception as e:
                # If optimization fails, save original
                file.save(file_path)
        else:
            # Save SVG as-is
            file.save(file_path)
        
        # Get file info
        file_size = os.path.getsize(file_path)
        
        image_info = {
            'id': str(uuid.uuid4()),
            'filename': unique_filename,
            'original_name': secure_filename(file.filename),
            'path': f"/static/uploads/{unique_filename}",
            'size': file_size,
            'type': file_extension,
            'uploaded_at': datetime.utcnow().isoformat()
        }
        
        # Attach to note if note_id provided
        if note_id:
            try:
                NoteService.attach_image(note_id, image_info)
            except Exception as e:
                # Clean up uploaded file if attachment fails
                if os.path.exists(file_path):
                    os.remove(file_path)
                return error_response(f"Failed to attach image to note: {str(e)}")
        
        return success_response(data=image_info, message="Image uploaded successfully")
        
    except Exception as e:
        return error_response(f"Upload failed: {str(e)}")

@images_blueprint.route('/delete/<image_id>', methods=['DELETE'])
def delete_image(image_id):
    """Delete an uploaded image"""
    try:
        note_id = request.args.get('note_id')
        
        if not note_id:
            return error_response("Note ID is required")
        
        # Remove image from note and delete file
        result = NoteService.remove_image(note_id, image_id)
        
        return success_response(data=result, message="Image deleted successfully")
        
    except Exception as e:
        return error_response(f"Failed to delete image: {str(e)}")

@images_blueprint.route('/list/<note_id>', methods=['GET'])
def list_images(note_id):
    """List all images attached to a note"""
    try:
        images = NoteService.get_note_images(note_id)
        return success_response(data={'images': images})
        
    except Exception as e:
        return error_response(f"Failed to retrieve images: {str(e)}")

# Serve uploaded files
@images_blueprint.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded image files"""
    try:
        return send_from_directory(UPLOAD_FOLDER, filename)
    except Exception as e:
        return error_response(f"File not found: {str(e)}")

from datetime import datetime
