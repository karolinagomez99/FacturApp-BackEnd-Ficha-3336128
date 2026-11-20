import os
import unittest

import jwt

os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['JWT_SECRET_KEY'] = 'tests-use-a-long-random-key-for-hmac-sha256'

from src.app import app
from src.models import db
from src.models.categories import Categories
from src.models.clients import Clients
from src.models.invoice_details import InvoiceDetails
from src.models.invoices import Invoices
from src.models.products import Products
from src.models.users import Role, Users
from src.utils.auth import generate_token


class ApiTests(unittest.TestCase):
    def setUp(self):
        with app.app_context():
            db.session.query(InvoiceDetails).delete()
            db.session.query(Invoices).delete()
            db.session.query(Products).delete()
            db.session.query(Clients).delete()
            db.session.query(Categories).delete()
            db.session.query(Users).delete()
            db.session.commit()

            self.category = Categories(name='General')
            db.session.add(self.category)
            db.session.commit()
            self.admin = Users('admin@test.local', 'pass123', 'Admin', Role.ADMIN.value)
            self.seller = Users('seller@test.local', 'pass123', 'Seller', Role.SELLER.value)
            Users.save(self.admin)
            Users.save(self.seller)
            self.product = Products('Product A', 'Description', 10, 5, self.category.id)
            self.second_product = Products('Product B', 'Description', 20, 5, self.category.id)
            Products.save(self.product)
            Products.save(self.second_product)
            self.client_record = Clients(
                'CC', '100', 'Client One', 'one@test.local', '123', 'Street',
            )
            Clients.save(self.client_record)
            self.admin_token = generate_token(self.admin)
            self.seller_token = generate_token(self.seller)

        self.http = app.test_client()
        self.admin_headers = {'Authorization': f'Bearer {self.admin_token}'}
        self.seller_headers = {'Authorization': f'Bearer {self.seller_token}'}

    def test_product_validation_does_not_mutate_rejected_update(self):
        response = self.http.put(
            f'/api/v1/products/{self.second_product.id}',
            headers=self.admin_headers,
            json={'name': self.product.name, 'price': 99},
        )
        self.assertEqual(response.status_code, 400)
        response = self.http.get(
            f'/api/v1/products/{self.second_product.id}',
            headers=self.admin_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['name'], 'Product B')
        self.assertEqual(response.json['price'], 20.0)

        response = self.http.post(
            '/api/v1/products',
            headers=self.admin_headers,
            json={'name': 'Free product', 'price': 0, 'category_id': self.category.id},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json['price'], 0.0)

        response = self.http.post(
            '/api/v1/products',
            headers=self.admin_headers,
            json={'name': 'Invalid', 'price': 'abc', 'stock': -1, 'category_id': 999},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            set(response.json['validation-errors']),
            {'price', 'stock', 'category_id'},
        )

    def test_client_update_is_validated_before_changes_and_accepts_zero_active(self):
        second_client = Clients(
            'NIT', '200', 'Client Two', 'two@test.local', '456', 'Road',
        )
        Clients.save(second_client)
        response = self.http.put(
            f'/api/v1/clients/{self.client_record.id}',
            headers=self.admin_headers,
            json={'name': 'Changed Name', 'document_number': second_client.document_number},
        )
        self.assertEqual(response.status_code, 400)
        response = self.http.get(
            f'/api/v1/clients/{self.client_record.id}',
            headers=self.admin_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['name'], 'Client One')

        response = self.http.put(
            f'/api/v1/clients/{self.client_record.id}',
            headers=self.admin_headers,
            json={'active': 0},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['active'], 0)

    def test_invoice_details_keep_stock_and_total_consistent_through_cancel(self):
        response = self.http.post(
            '/api/v1/invoices',
            headers=self.seller_headers,
            json={
                'client_id': self.client_record.id,
                'user_id': self.seller.id,
                'total': 999,
                'completed': True,
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json['total'], 0.0)
        self.assertFalse(response.json['completed'])
        invoice_id = response.json['id']

        response = self.http.post(
            f'/api/v1/invoices/{invoice_id}/details',
            headers=self.seller_headers,
            json={'product_id': self.product.id, 'quantity': 2, 'unit_price': 1},
        )
        self.assertEqual(response.status_code, 201)
        detail_id = response.json['id']
        self.assertEqual(response.json['unit_price'], 10.0)

        response = self.http.post(
            f'/api/v1/invoices/{invoice_id}/details',
            headers=self.seller_headers,
            json={'product_id': self.product.id, 'quantity': 8},
        )
        self.assertEqual(response.status_code, 400)
        product_response = self.http.get(
            f'/api/v1/products/{self.product.id}',
            headers=self.admin_headers,
        )
        self.assertEqual(product_response.json['stock'], 3.0)

        response = self.http.put(
            f'/api/v1/invoices/{invoice_id}/details/{detail_id}',
            headers=self.admin_headers,
            json={'quantity': 1},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['subtotal'], 10.0)

        response = self.http.put(
            f'/api/v1/invoices/{invoice_id}/complete',
            headers=self.seller_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json['completed'])
        response = self.http.put(
            f'/api/v1/invoices/{invoice_id}/details/{detail_id}',
            headers=self.admin_headers,
            json={'quantity': 2},
        )
        self.assertEqual(response.status_code, 409)

        response = self.http.delete(
            f'/api/v1/invoices/{invoice_id}',
            headers=self.admin_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['active'], 0)
        self.assertEqual(response.json['total'], 10.0)
        product_response = self.http.get(
            f'/api/v1/products/{self.product.id}',
            headers=self.admin_headers,
        )
        self.assertEqual(product_response.json['stock'], 5.0)

    def test_roles_and_authentication_are_enforced(self):
        response = self.http.get('/api/v1/clients')
        self.assertEqual(response.status_code, 401)

        response = self.http.post(
            '/api/v1/clients',
            headers=self.seller_headers,
            json={},
        )
        self.assertEqual(response.status_code, 403)

        response = self.http.post(
            '/api/v1/invoices',
            headers=self.seller_headers,
            json={'client_id': self.client_record.id, 'user_id': self.admin.id},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json['validation-errors']['user_id'],
            'SELLER can only create invoices with their own user_id',
        )

    def test_registration_and_role_assignment_use_user_model_methods(self):
        response = self.http.post(
            '/api/v1/register',
            json={
                'email': 'newuser@test.local',
                'password': 'pass123',
                'name': 'New User',
                'role': 'ADMIN',
            },
        )
        self.assertEqual(response.status_code, 201)

        with app.app_context():
            new_user = Users.get_by_email('newuser@test.local')
            self.assertEqual(new_user.role, Role.PENDING.value)
            new_user_id = new_user.id

        response = self.http.put(
            f'/api/v1/users/{new_user_id}/role',
            headers=self.admin_headers,
            json={'role': 'SELLER'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['role'], Role.SELLER.value)

    def test_inactive_user_cannot_login_or_use_malformed_signed_token(self):
        with app.app_context():
            self.admin.active = 0
            Users.update(self.admin)

        response = self.http.post('/api/v1/login', json={
            'email': 'admin@test.local',
            'password': 'pass123',
        })
        self.assertEqual(response.status_code, 403)

        malformed_token = jwt.encode(
            {'exp': 9999999999},
            app.config['JWT_SECRET_KEY'],
            algorithm='HS256',
        )
        response = self.http.get(
            '/api/v1/clients',
            headers={'Authorization': f'Bearer {malformed_token}'},
        )
        self.assertEqual(response.status_code, 401)

    def test_category_crud(self):
        response = self.http.post(
            '/api/v1/categories',
            headers=self.admin_headers,
            json={'name': 'Technology', 'description': 'Ignored by model'},
        )
        self.assertEqual(response.status_code, 201)
        category_id = response.json['id']

        response = self.http.get(
            f'/api/v1/categories/{category_id}',
            headers=self.seller_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['name'], 'Technology')

        response = self.http.put(
            f'/api/v1/categories/{category_id}',
            headers=self.admin_headers,
            json={'name': 'Computers'},
        )
        self.assertEqual(response.status_code, 200)

        response = self.http.delete(
            f'/api/v1/categories/{category_id}',
            headers=self.admin_headers,
        )
        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
