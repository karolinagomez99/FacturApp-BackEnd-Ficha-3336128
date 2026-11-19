from flask import Blueprint, g, jsonify, request

from src.models.clients import Clients
from src.models.invoice_details import InvoiceDetails
from src.models.invoices import Invoices
from src.models.products import Products
from src.models.users import Role, Users
from src.utils.auth import role_required, token_required


invoices_bp = Blueprint('invoices_v1', __name__, url_prefix='/api/v1')


def _invoice_json(invoice):
    return {
        'id': invoice.id,
        'client_id': invoice.client_id,
        'user_id': invoice.user_id,
        'date': invoice.date.isoformat(),
        'total': invoice.total,
        'completed': invoice.completed,
        'active': invoice.active,
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


def _validate_references(data, partial=False, restrict_seller=False):
    errors = {}
    updates = {}
    fields = ('client_id', 'user_id')
    for field in fields:
        if partial and field not in data:
            continue
        raw_value = data.get(field)
        if raw_value is None:
            errors[field] = f'{field} is required'
            continue

        identifier = _as_id(raw_value)
        if identifier is None:
            errors[field] = f'{field} does not exist'
            continue

        if field == 'client_id':
            client = Clients.get_by_id(identifier)
            if not client:
                errors[field] = 'client_id does not exist'
            elif client.active != 1:
                errors[field] = 'client must be active'
            else:
                updates[field] = identifier
        else:
            user = Users.get_by_id(identifier)
            if not user:
                errors[field] = 'user_id does not exist'
            else:
                if user.active != 1:
                    errors[field] = 'user must be active'
                elif user.role != Role.SELLER.value:
                    errors[field] = 'user must have SELLER role'
                else:
                    updates[field] = identifier

            if (
                restrict_seller
                and g.current_user.role == Role.SELLER.value
                and identifier != g.current_user.id
            ):
                errors[field] = 'SELLER can only create invoices with their own user_id'

    return updates, errors


def _invoice_state_error(invoice):
    if invoice.active != 1:
        return 'Invoice is cancelled and cannot be modified'
    if invoice.completed:
        return 'Invoice is completed and cannot be modified'
    return None


def _conflict(message):
    return jsonify({'success': False, 'message': message}), 409


@invoices_bp.route('/invoices', methods=['POST'])
@token_required
@role_required(Role.ADMIN, Role.SELLER)
def post_invoice():
    updates, errors = _validate_references(
        _body(), restrict_seller=True,
    )
    if errors:
        return _validation_error(errors)

    invoice = Invoices(client_id=updates['client_id'], user_id=updates['user_id'])
    Invoices.save(invoice)
    return jsonify(_invoice_json(invoice)), 201


@invoices_bp.route('/invoices', methods=['GET'])
@token_required
@role_required(Role.ADMIN, Role.SELLER)
def get_invoices():
    page = max(1, request.args.get('page', default=1, type=int) or 1)
    per_page = max(1, request.args.get('per_page', default=3, type=int) or 3)
    invoices, total_invoices = Invoices.get_paginated(page=page, per_page=per_page)
    total_pages = (total_invoices + per_page - 1) // per_page
    return jsonify({
        'data': [_invoice_json(invoice) for invoice in invoices],
        'meta': {
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'total_invoices': total_invoices,
            'has_next': page < total_pages,
            'has_prev': page > 1,
        },
    }), 200


@invoices_bp.route('/invoices/<int:invoice_id>', methods=['GET'])
@token_required
@role_required(Role.ADMIN, Role.SELLER)
def get_invoice_by_id(invoice_id):
    invoice = Invoices.get_by_id(invoice_id)
    if not invoice:
        return jsonify({'success': False, 'message': 'Invoice not found'}), 404
    return jsonify(_invoice_json(invoice)), 200


@invoices_bp.route('/invoices/<int:invoice_id>', methods=['PUT'])
@token_required
@role_required(Role.ADMIN)
def put_invoice(invoice_id):
    invoice = Invoices.get_by_id(invoice_id)
    if not invoice:
        return jsonify({'success': False, 'message': 'Invoice not found'}), 404
    state_error = _invoice_state_error(invoice)
    if state_error:
        return _conflict(state_error)

    updates, errors = _validate_references(_body(), partial=True)
    if errors:
        return _validation_error(errors)

    for field, value in updates.items():
        setattr(invoice, field, value)
    Invoices.update(invoice)
    return jsonify(_invoice_json(invoice)), 200


@invoices_bp.route('/invoices/<int:invoice_id>/complete', methods=['PUT'])
@token_required
@role_required(Role.ADMIN, Role.SELLER)
def complete_invoice(invoice_id):
    invoice = Invoices.get_by_id(invoice_id)
    if not invoice:
        return jsonify({'success': False, 'message': 'Invoice not found'}), 404
    if invoice.active != 1:
        return _conflict('Invoice is cancelled and cannot be modified')
    if invoice.completed:
        return _conflict('Invoice is already completed')
    if not InvoiceDetails.get_by_invoice(invoice_id):
        return _conflict('Invoice has no details and cannot be completed')

    invoice.completed = True
    Invoices.update(invoice)
    return jsonify(_invoice_json(invoice)), 200


@invoices_bp.route('/invoices/<int:invoice_id>', methods=['DELETE'])
@token_required
@role_required(Role.ADMIN)
def cancel_invoice(invoice_id):
    invoice = Invoices.get_by_id(invoice_id)
    if not invoice:
        return jsonify({'success': False, 'message': 'Invoice not found'}), 404
    if invoice.active != 1:
        return _conflict('Invoice is already cancelled')

    for detail in InvoiceDetails.get_by_invoice(invoice_id):
        product = Products.get_by_id(detail.product_id)
        product.stock += detail.quantity
    invoice.active = 0
    Invoices.update(invoice)
    return jsonify(_invoice_json(invoice)), 200
