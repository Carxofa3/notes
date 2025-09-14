from flask_restx import Namespace, Resource
from werkzeug.datastructures import FileStorage
from app.services import image_service
from flask import request

ns = Namespace('images', description='Image upload operations')

upload_parser = ns.parser()
upload_parser.add_argument('file', location='files', type=FileStorage, required=True)

@ns.route('/upload/<int:note_id>')
@ns.param('note_id', 'The ID of the note to associate the image with')
class ImageUpload(Resource):
    @ns.expect(upload_parser)
    def post(self, note_id):
        """Upload an image"""
        if 'file' not in request.files:
            return {'message': 'No file part in the request'}, 400
        file = request.files['file']
        if file.filename == '':
            return {'message': 'No file selected for uploading'}, 400

        filename = image_service.save_image(file, note_id)
        if filename:
            return {'url': f'/static/uploads/{filename}'}, 201
        return {'message': 'Failed to upload image'}, 400
