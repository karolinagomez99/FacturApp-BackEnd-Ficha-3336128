import math

from flask import Blueprint, jsonify, request

from src.models.categories import Categories
from src.models.products import Products
from src.models.users import Role
from src.utils.auth import role_required, token_required


products_bp = Blueprint('products_v1', __name__, url_prefix='/api/v1')


def _product_json(product):
    return {
        'id': product.id,
        'name': product.name,
        'description': product.description,
        'price': product.price,
        'stock': product.stock,
        'category_id': product.category_id,
        'active': product.active,
    }


def _validation_error(errors):
    return jsonify({
        'success': False,
        'message': 'Errors in data validation',
        'validation-errors': errors,
    }), 400


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _category_id(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, float) and not value.is_integer():
        return None
    try:
        category_id = int(value)
    except (TypeError, ValueError):
        return None
    return category_id if category_id > 0 else None


@products_bp.route('/products', methods=['GET'])
@token_required
@role_required(Role.ADMIN, Role.SELLER)
def get_products():
    page = max(1, request.args.get('page', default=1, type=int) or 1)
    per_page = max(1, request.args.get('per_page', default=3, type=int) or 3)
    products, total_products = Products.get_paginated(page=page, per_page=per_page)
    total_pages = (total_products + per_page - 1) // per_page
    return jsonify({
        'data': [_product_json(product) for product in products],
        'meta': {
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'total_products': total_products,
            'has_next': page < total_pages,
            'has_prev': page > 1,
        },
    }), 200


@products_bp.route('/products/<int:product_id>', methods=['GET'])
@token_required
@role_required(Role.ADMIN, Role.SELLER)
def get_product_by_id(product_id):
    product = Products.get_by_id(product_id)
    if not product:
        return jsonify({'success': False, 'message': 'Product not found'}), 404
    return jsonify(_product_json(product)), 200


@products_bp.route('/products', methods=['POST'])
@token_required
@role_required(Role.ADMIN)
def post_products():
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    name = data.get('name')
    description = data.get('description')
    raw_price = data.get('price')
    raw_stock = data.get('stock', 0)
    raw_category_id = data.get('category_id')
    errors = {}

    if not name:
        errors['name'] = 'name is required'
    elif Products.get_by_name(name):
        errors['name'] = 'name must be unique'

    price = None
    if raw_price is None:
        errors['price'] = 'price is required'
    else:
        price = _number(raw_price)
        if price is None:
            errors['price'] = 'price must be a number'
        elif price < 0:
            errors['price'] = 'price must be a non-negative number'

    stock = _number(raw_stock)
    if stock is None:
        errors['stock'] = 'stock must be a number'
    elif stock < 0:
        errors['stock'] = 'stock must be a non-negative number'

    category_id = _category_id(raw_category_id)
    if raw_category_id is None:
        errors['category_id'] = 'category_id is required'
    elif category_id is None or not Categories.get_by_id(category_id):
        errors['category_id'] = 'category_id does not exist'

    if errors:
        return _validation_error(errors)

    product = Products(
        name=name,
        description=description,
        price=price,
        stock=stock,
        category_id=category_id,
    )
    Products.save(product)
    return jsonify(_product_json(product)), 201


@products_bp.route('/products/<int:product_id>', methods=['PUT'])
@token_required
@role_required(Role.ADMIN)
def put_products(product_id):
    product = Products.get_by_id(product_id)
    if not product:
        return jsonify({'success': False, 'message': 'Product not found'}), 404

    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    errors = {}
    updates = {}

    if 'name' in data and data['name'] is not None:
        name = data['name']
        existing_product = Products.get_by_name(name)
        if name != product.name and existing_product:
            errors['name'] = 'name must be unique'
        else:
            updates['name'] = name

    if 'description' in data:
        updates['description'] = data['description']

    for field in ('price', 'stock'):
        if field not in data or data[field] is None:
            continue
        number = _number(data[field])
        if number is None:
            errors[field] = f'{field} must be a number'
        elif number < 0:
            errors[field] = f'{field} must be a non-negative number'
        else:
            updates[field] = number

    if 'category_id' in data and data['category_id'] is not None:
        category_id = _category_id(data['category_id'])
        if category_id is None or not Categories.get_by_id(category_id):
            errors['category_id'] = 'category_id does not exist'
        else:
            updates['category_id'] = category_id

    if errors:
        return _validation_error(errors)

    for field, value in updates.items():
        setattr(product, field, value)
    Products.update(product)
    return jsonify(_product_json(product)), 200
