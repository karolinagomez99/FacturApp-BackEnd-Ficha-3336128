import math

from flask import Blueprint, jsonify, request
from sqlalchemy import select

from src.models import db
from src.models.invoice_details import InvoiceDetails
from src.models.invoices import Invoices
from src.models.products import Products
from src.models.users import Role
from src.utils.auth import role_required, token_required


invoice_details_bp = Blueprint(
    'invoice_details_v1', __name__, url_prefix='/api/v1',
)


def _detail_json(detail):
    return {
        'id': detail.id,
        'invoice_id': detail.invoice_id,
        'product_id': detail.product_id,
        'quantity': detail.quantity,
        'unit_price': detail.unit_price,
        'subtotal': round(detail.quantity * detail.unit_price, 2),
    }


def _validation_error(errors):
    return jsonify({
        'success': False,
        'message': 'Errors in data validation',
        'validation-errors': errors,
    }), 400


def _body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _as_id(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, float) and not value.is_integer():
        return None
    try:
        identifier = int(value)
    except (TypeError, ValueError):
        return None
    return identifier if identifier > 0 else None


def _quantity(value):
    if isinstance(value, bool):
        return None
    try:
        quantity = float(value)
    except (TypeError, ValueError):
        return None
    return quantity if math.isfinite(quantity) else None


def _invoice_or_error(invoice_id):
    invoice = Invoices.get_by_id(invoice_id)
    if not invoice:
        return None, (jsonify({'success': False, 'message': 'Invoice not found'}), 404)
    if invoice.active != 1:
        return None, (jsonify({
            'success': False,
            'message': 'Invoice is cancelled and cannot be modified',
        }), 409)
    if invoice.completed:
        return None, (jsonify({
            'success': False,
            'message': 'Invoice is completed and cannot be modified',
        }), 409)
    return invoice, None


@invoice_details_bp.route('/invoices/<int:invoice_id>/details', methods=['POST'])
@token_required
@role_required(Role.ADMIN, Role.SELLER)
def post_invoice_detail(invoice_id):
    invoice, error_response = _invoice_or_error(invoice_id)
    if error_response:
        return error_response

    data = _body()
    errors = {}
    product = None
    raw_product_id = data.get('product_id')
    if raw_product_id is None:
        errors['product_id'] = 'product_id is required'
    else:
        product_id = _as_id(raw_product_id)
        if product_id is None or not (product := Products.get_by_id(product_id)):
            errors['product_id'] = 'product_id does not exist'
        elif product.active != 1:
            errors['product_id'] = 'product must be active'

    raw_quantity = data.get('quantity')
    quantity = None
    if raw_quantity is None:
        errors['quantity'] = 'quantity is required'
    else:
        quantity = _quantity(raw_quantity)
        if quantity is None:
            errors['quantity'] = 'quantity must be a number'
        elif quantity <= 0:
            errors['quantity'] = 'quantity must be greater than 0'

    if product is not None and quantity is not None and quantity > 0:
        if quantity > product.stock:
            errors['quantity'] = f'not enough stock, available: {product.stock}'

    if errors:
        return _validation_error(errors)

    product = db.session.scalars(
        select(Products).where(Products.id == product.id).with_for_update()
    ).one()
    if quantity > product.stock:
        return _validation_error({
            'quantity': f'not enough stock, available: {product.stock}',
        })

    detail = InvoiceDetails.get_by_invoice_and_product(invoice_id, product.id)
    created = detail is None
    if created:
        detail = InvoiceDetails(
            invoice_id=invoice_id,
            product_id=product.id,
            quantity=quantity,
            unit_price=product.price,
        )
    else:
        detail.quantity += quantity

    product.stock -= quantity
    invoice.total = round(invoice.total + quantity * detail.unit_price, 2)
    if created:
        db.session.add(detail)
        status = 201
    else:
        db.session.add(detail)
        status = 200
    db.session.commit()
    return jsonify(_detail_json(detail)), status


@invoice_details_bp.route('/invoices/<int:invoice_id>/details', methods=['GET'])
@token_required
@role_required(Role.ADMIN, Role.SELLER)
def get_invoice_details(invoice_id):
    invoice = Invoices.get_by_id(invoice_id)
    if not invoice:
        return jsonify({'success': False, 'message': 'Invoice not found'}), 404
    details = InvoiceDetails.get_by_invoice(invoice_id)
    return jsonify({
        'invoice_id': invoice.id,
        'total': invoice.total,
        'data': [_detail_json(detail) for detail in details],
    }), 200


@invoice_details_bp.route(
    '/invoices/<int:invoice_id>/details/<int:detail_id>', methods=['PUT'],
)
@token_required
@role_required(Role.ADMIN)
def put_invoice_detail(invoice_id, detail_id):
    invoice = Invoices.get_by_id(invoice_id)
    if not invoice:
        return jsonify({'success': False, 'message': 'Invoice not found'}), 404
    detail = InvoiceDetails.get_by_id(detail_id)
    if not detail or detail.invoice_id != invoice_id:
        return jsonify({
            'success': False,
            'message': 'Invoice detail not found',
        }), 404
    if invoice.active != 1:
        return jsonify({
            'success': False,
            'message': 'Invoice is cancelled and cannot be modified',
        }), 409
    if invoice.completed:
        return jsonify({
            'success': False,
            'message': 'Invoice is completed and cannot be modified',
        }), 409

    data = _body()
    raw_quantity = data.get('quantity')
    errors = {}
    if raw_quantity is None:
        errors['quantity'] = 'quantity is required'
        quantity = None
    else:
        quantity = _quantity(raw_quantity)
        if quantity is None:
            errors['quantity'] = 'quantity must be a number'
        elif quantity <= 0:
            errors['quantity'] = 'quantity must be greater than 0'

    product = db.session.scalars(
        select(Products).where(Products.id == detail.product_id).with_for_update()
    ).one()
    difference = quantity - detail.quantity if quantity is not None else 0
    if quantity is not None and quantity > detail.quantity:
        if difference > product.stock:
            errors['quantity'] = f'not enough stock, available: {product.stock}'
    if errors:
        return _validation_error(errors)

    product.stock -= difference
    invoice.total = round(invoice.total + difference * detail.unit_price, 2)
    detail.quantity = quantity
    db.session.commit()
    return jsonify(_detail_json(detail)), 200


@invoice_details_bp.route(
    '/invoices/<int:invoice_id>/details/<int:detail_id>', methods=['DELETE'],
)
@token_required
@role_required(Role.ADMIN)
def delete_invoice_detail(invoice_id, detail_id):
    invoice = Invoices.get_by_id(invoice_id)
    if not invoice:
        return jsonify({'success': False, 'message': 'Invoice not found'}), 404
    detail = InvoiceDetails.get_by_id(detail_id)
    if not detail or detail.invoice_id != invoice_id:
        return jsonify({
            'success': False,
            'message': 'Invoice detail not found',
        }), 404
    if invoice.active != 1:
        return jsonify({
            'success': False,
            'message': 'Invoice is cancelled and cannot be modified',
        }), 409
    if invoice.completed:
        return jsonify({
            'success': False,
            'message': 'Invoice is completed and cannot be modified',
        }), 409

    product = db.session.scalars(
        select(Products).where(Products.id == detail.product_id).with_for_update()
    ).one()
    product.stock += detail.quantity
    invoice.total = round(invoice.total - detail.quantity * detail.unit_price, 2)
    db.session.delete(detail)
    db.session.commit()
    return jsonify({
        'success': True,
        'message': 'Invoice detail deleted',
    }), 200
