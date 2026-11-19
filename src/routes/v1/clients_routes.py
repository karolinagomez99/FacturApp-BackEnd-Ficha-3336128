from flask import Blueprint, jsonify, request

from src.models.clients import Clients, DocumentType
from src.models.users import Role
from src.utils.auth import role_required, token_required


clients_bp = Blueprint('clients_v1', __name__, url_prefix='/api/v1')
DOCUMENT_TYPES = [document_type.value for document_type in DocumentType]


def _client_json(client):
    return {
        'id': client.id,
        'document_type': client.document_type,
        'document_number': client.document_number,
        'name': client.name,
        'email': client.email,
        'phone': client.phone,
        'address': client.address,
        'active': client.active,
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


def _validate(data, existing_client=None, partial=False):
    errors = {}
    updates = {}
    fields = ('document_type', 'document_number', 'name', 'email', 'phone', 'address')

    for field in fields:
        if partial and field not in data:
            continue
        value = data.get(field)
        if field == 'document_type':
            if not value:
                errors[field] = f'{field} is required'
            else:
                value = str(value).strip().upper()
                if value not in DOCUMENT_TYPES:
                    errors[field] = 'document_type must be one of: CC, NIT, CE'
                else:
                    updates[field] = value
        elif field == 'email':
            if not value:
                errors[field] = 'email is required'
            elif '@' not in str(value):
                errors[field] = 'email is not valid'
            else:
                updates[field] = value
        elif not value:
            errors[field] = f'{field} is required'
        else:
            updates[field] = value

    if 'document_number' in updates:
        if existing_client is None or updates['document_number'] != existing_client.document_number:
            duplicate = Clients.get_by_document_number(updates['document_number'])
            if duplicate:
                errors['document_number'] = 'document_number must be unique'

    if existing_client is not None and 'active' in data:
        active = data['active']
        if isinstance(active, bool) or active not in (0, 1):
            errors['active'] = 'active must be 0 or 1'
        else:
            updates['active'] = active

    return updates, errors


@clients_bp.route('/clients', methods=['GET'])
@token_required
@role_required(Role.ADMIN, Role.SELLER)
def get_clients():
    page = max(1, request.args.get('page', default=1, type=int) or 1)
    per_page = max(1, request.args.get('per_page', default=3, type=int) or 3)
    clients, total_clients = Clients.get_paginated(page=page, per_page=per_page)
    total_pages = (total_clients + per_page - 1) // per_page
    return jsonify({
        'data': [_client_json(client) for client in clients],
        'meta': {
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'total_clients': total_clients,
            'has_next': page < total_pages,
            'has_prev': page > 1,
        },
    }), 200


@clients_bp.route('/clients/<int:client_id>', methods=['GET'])
@token_required
@role_required(Role.ADMIN, Role.SELLER)
def get_client_by_id(client_id):
    client = Clients.get_by_id(client_id)
    if not client:
        return jsonify({'success': False, 'message': 'Client not found'}), 404
    return jsonify(_client_json(client)), 200


@clients_bp.route('/clients', methods=['POST'])
@token_required
@role_required(Role.ADMIN)
def post_client():
    data = _body()
    updates, errors = _validate(data)
    if errors:
        return _validation_error(errors)

    client = Clients(**updates)
    Clients.save(client)
    return jsonify(_client_json(client)), 201


@clients_bp.route('/clients/<int:client_id>', methods=['PUT'])
@token_required
@role_required(Role.ADMIN)
def put_client(client_id):
    client = Clients.get_by_id(client_id)
    if not client:
        return jsonify({'success': False, 'message': 'Client not found'}), 404

    updates, errors = _validate(_body(), existing_client=client, partial=True)
    if errors:
        return _validation_error(errors)

    for field, value in updates.items():
        setattr(client, field, value)
    Clients.update(client)
    return jsonify(_client_json(client)), 200
