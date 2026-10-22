# app/api/units.py
from flask_restx import Namespace, Resource, fields
from app.services import unit_service
from flask import request

ns = Namespace('units', description='Unit related operations')

unit_model = ns.model('Unit', {
    'id': fields.Integer(readonly=True, description='The unit unique identifier'),
    'name': fields.String(required=True, description='The unit name'),
    'lesson_id': fields.Integer(required=True, description='The lesson identifier'),
    'display_order': fields.Integer(description='The display order of the unit'),
    'icon': fields.String(description='The unit icon'),
    'color': fields.String(description='The unit color'),
})

unit_input_model = ns.model('UnitInput', {
    'name': fields.String(required=True, description='The unit name'),
    'icon': fields.String(required=False, description='The unit icon'),
    'color': fields.String(required=False, description='The unit color'),
})

unit_update_model = ns.model('UnitUpdate', {
    'name': fields.String(description='The new unit name'),
    'icon': fields.String(description='The new unit icon'),
    'color': fields.String(description='The new unit color'),
})

# This is for creating a unit for a specific lesson
@ns.route('/by-lesson/<int:lesson_id>')
@ns.param('lesson_id', 'The lesson identifier')
class UnitList(Resource):
    @ns.doc('list_units_for_lesson')
    @ns.marshal_list_with(unit_model)
    def get(self, lesson_id):
        """List all units for a given lesson"""
        return unit_service.get_all_units_for_lesson(lesson_id)

    @ns.doc('create_unit_for_lesson')
    @ns.expect(unit_input_model, validate=False)
    @ns.marshal_with(unit_model, code=201)
    def post(self, lesson_id):
        """Create a new unit for a given lesson"""
        payload = request.get_json(silent=True) or {}
        return unit_service.create_unit(lesson_id, payload), 201

@ns.route('/reorder')
class UnitReorder(Resource):
    @ns.doc('reorder_units')
    @ns.expect([fields.Integer], validate=True)
    @ns.response(204, 'Units reordered successfully')
    def post(self):
        """Reorder the units"""
        unit_service.reorder_units(ns.payload)
        return '', 204

@ns.route('/<int:id>')
@ns.response(404, 'Unit not found')
@ns.param('id', 'The unit identifier')
class Unit(Resource):
    @ns.doc('get_unit')
    @ns.marshal_with(unit_model)
    def get(self, id):
        """Fetch a unit given its identifier"""
        return unit_service.get_unit_by_id(id)

    @ns.doc('update_unit')
    @ns.expect(unit_update_model, validate=False)
    @ns.marshal_with(unit_model)
    def put(self, id):
        """Update a unit given its identifier"""
        payload = request.get_json(silent=True) or {}
        return unit_service.update_unit(id, payload)

    @ns.doc('delete_unit')
    @ns.response(204, 'Unit deleted')
    def delete(self, id):
        """Delete a unit given its identifier"""
        unit_service.delete_unit(id)
        return '', 204
