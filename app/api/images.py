from flask_restx import Namespace, Resource
from werkzeug.datastructures import FileStorage
from app.services import image_service
from flask import request

ns = Namespace('images', description='Media and image upload operations')

upload_parser = ns.parser()
upload_parser.add_argument('file', location='files', type=FileStorage, required=True)

@ns.route('/upload/<int:note_id>')
@ns.param('note_id', 'The ID of the note to associate the media with')
class ImageUpload(Resource):
    @ns.expect(upload_parser)
    def post(self, note_id):
        """Upload media (image, audio, video)"""
        if 'file' not in request.files:
            return {'message': 'No file part in the request'}, 400
        file = request.files['file']
        if not file or file.filename == '':
            return {'message': 'No file selected for uploading'}, 400

        filename = image_service.save_image(file, note_id)
        if filename:
            return {'url': f'/static/uploads/{filename}', 'filename': filename}, 201
        return {'message': 'Failed to upload media file'}, 400

@ns.route('/upload')
class GeneralMediaUpload(Resource):
    @ns.expect(upload_parser)
    def post(self):
        """Upload media without a specific note ID"""
        if 'file' not in request.files:
            return {'message': 'No file part in the request'}, 400
        file = request.files['file']
        if not file or file.filename == '':
            return {'message': 'No file selected for uploading'}, 400

        filename = image_service.save_image(file, None)
        if filename:
            return {'url': f'/static/uploads/{filename}', 'filename': filename}, 201
        return {'message': 'Failed to upload media file'}, 400
