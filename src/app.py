import os

from dotenv import load_dotenv
from flask import Flask

from src.models import db
from src.routes import register_routes


def create_app(test_config=None):
    load_dotenv()
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE_URL=os.environ.get('DATABASE_URL'),
        JWT_SECRET_KEY=os.environ.get('JWT_SECRET_KEY'),
    )
    if test_config:
        app.config.update(test_config)
    if not app.config.get('JWT_SECRET_KEY'):
        raise RuntimeError('JWT_SECRET_KEY must be configured')

    db.init_app(app)

    from src.models import categories, clients, invoice_details, invoices, products, users

    _ = (categories, clients, invoice_details, invoices, products, users)
    with app.app_context():
        db.create_all()

    register_routes(app)
    return app


app = create_app()


if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1')
