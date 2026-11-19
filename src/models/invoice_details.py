from sqlalchemy import Float, ForeignKey, Integer, select
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base, db


class InvoiceDetails(Base):
    __tablename__ = 'invoice_details'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey('invoices.id'), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)

    def __init__(self, invoice_id, product_id, quantity, unit_price):
        self.invoice_id = invoice_id
        self.product_id = product_id
        self.quantity = quantity
        self.unit_price = unit_price

    def __repr__(self):
        return f'<InvoiceDetails invoice={self.invoice_id} product={self.product_id}>'

    @classmethod
    def get_by_id(cls, detail_id):
        return db.session.get(cls, detail_id)

    @classmethod
    def get_by_invoice(cls, invoice_id):
        return db.session.scalars(
            select(cls).where(cls.invoice_id == invoice_id).order_by(cls.id)
        ).all()

    @classmethod
    def get_by_invoice_and_product(cls, invoice_id, product_id):
        return db.session.scalar(
            select(cls).where(
                cls.invoice_id == invoice_id,
                cls.product_id == product_id,
            )
        )

    @staticmethod
    def save(detail):
        db.session.add(detail)
        db.session.commit()

    @staticmethod
    def update(detail):
        db.session.add(detail)
        db.session.commit()

    @staticmethod
    def delete(detail):
        db.session.delete(detail)
        db.session.commit()
