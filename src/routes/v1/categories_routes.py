from flask import Blueprint, jsonify, request

from src.models.categories import Categories
from src.models.products import Products
from src.models.users import Role
from src.utils.auth import role_required, token_required


categories_bp = Blueprint('categories_v1', __name__, url_prefix='/api/v1')


def _category_json(category):
    return {'id': category.id, 'name': category.name}


def _body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _validation_error(errors):
    return jsonify({
        'success': False,
        'message': 'Errors in data validation',
        'validation-errors': errors,
    }), 400


@categories_bp.route('/categories', methods=['GET'])
@token_required
@role_required(Role.ADMIN, Role.SELLER)
def get_categories():
    page = max(1, request.args.get('page', default=1, type=int) or 1)
    per_page = max(1, request.args.get('per_page', default=3, type=int) or 3)
    categories, total = Categories.get_paginated(page, per_page)
    total_pages = (total + per_page - 1) // per_page
    return jsonify({
        'data': [_category_json(category) for category in categories],
        'meta': {
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'total_categories': total,
            'has_next': page < total_pages,
            'has_prev': page > 1,
        },
    }), 200


@categories_bp.route('/categories/<int:category_id>', methods=['GET'])
@token_required
@role_required(Role.ADMIN, Role.SELLER)
def get_category(category_id):
    category = Categories.get_by_id(category_id)
    if not category:
        return jsonify({'success': False, 'message': 'Category not found'}), 404
    return jsonify(_category_json(category)), 200


@categories_bp.route('/categories', methods=['POST'])
@token_required
@role_required(Role.ADMIN)
def post_category():
    data = _body()
    name = data.get('name')
    if not name or not str(name).strip():
        return _validation_error({'name': 'name is required'})

    name = str(name).strip()
    if Categories.get_by_name(name):
        return _validation_error({'name': 'name must be unique'})

    category = Categories(name=name)
    Categories.save(category)
    return jsonify(_category_json(category)), 201


@categories_bp.route('/categories/<int:category_id>', methods=['PUT'])
@token_required
@role_required(Role.ADMIN)
def put_category(category_id):
    category = Categories.get_by_id(category_id)
    if not category:
        return jsonify({'success': False, 'message': 'Category not found'}), 404

    data = _body()
    name = data.get('name')
    if not name or not str(name).strip():
        return _validation_error({'name': 'name is required'})

    name = str(name).strip()
    existing = Categories.get_by_name(name)
    if existing and existing.id != category.id:
        return _validation_error({'name': 'name must be unique'})

    category.name = name
    Categories.update(category)
    return jsonify(_category_json(category)), 200


@categories_bp.route('/categories/<int:category_id>', methods=['DELETE'])
@token_required
@role_required(Role.ADMIN)
def delete_category(category_id):
    category = Categories.get_by_id(category_id)
    if not category:
        return jsonify({'success': False, 'message': 'Category not found'}), 404
    if Products.get_by_category(category_id):
        return jsonify({
            'success': False,
            'message': 'Category cannot be deleted because it has products',
        }), 409

    Categories.delete(category)
    return jsonify({'success': True, 'message': 'Category deleted'}), 200
