# app/api/lessons.py
from flask_restx import Namespace, Resource, fields
from app.services import lesson_service

ns = Namespace('lessons', description='Lesson related operations')

lesson_model = ns.model('Lesson', {
    'id': fields.Integer(readonly=True, description='The lesson unique identifier'),
    'name': fields.String(required=True, description='The lesson name'),
    'display_order': fields.Integer(description='The display order of the lesson'),
})

lesson_input_model = ns.model('LessonInput', {
    'name': fields.String(required=True, description='The lesson name')
})

lesson_update_model = ns.model('LessonUpdate', {
    'name': fields.String(description='The new lesson name')
})

@ns.route('/')
class LessonList(Resource):
    @ns.doc('list_lessons')
    @ns.marshal_list_with(lesson_model)
    def get(self):
        """List all lessons"""
        return lesson_service.get_all_lessons()

    @ns.doc('create_lesson')
    @ns.expect(lesson_input_model, validate=True)
    @ns.marshal_with(lesson_model, code=201)
    def post(self):
        """Create a new lesson"""
        return lesson_service.create_lesson(ns.payload), 201

@ns.route('/reorder')
class LessonReorder(Resource):
    @ns.doc('reorder_lessons')
    @ns.expect([fields.Integer], validate=True)
    @ns.response(204, 'Lessons reordered successfully')
    def post(self):
        """Reorder the lessons"""
        lesson_service.reorder_lessons(ns.payload)
        return '', 204

@ns.route('/<int:id>')
@ns.response(404, 'Lesson not found')
@ns.param('id', 'The lesson identifier')
class Lesson(Resource):
    @ns.doc('get_lesson')
    @ns.marshal_with(lesson_model)
    def get(self, id):
        """Fetch a lesson given its identifier"""
        return lesson_service.get_lesson_by_id(id)

    @ns.doc('update_lesson')
    @ns.expect(lesson_update_model, validate=True)
    @ns.marshal_with(lesson_model)
    def put(self, id):
        """Update a lesson given its identifier"""
        return lesson_service.update_lesson(id, ns.payload)

    @ns.doc('delete_lesson')
    @ns.response(204, 'Lesson deleted')
    def delete(self, id):
        """Delete a lesson given its identifier"""
        lesson_service.delete_lesson(id)
        return '', 204
