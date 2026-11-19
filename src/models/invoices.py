from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, select
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base, db


class Invoices(Base):
    __tablename__ = 'invoices'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey('clients.id'), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    total: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    def __init__(self, client_id, user_id):
        self.client_id = client_id
        self.user_id = user_id
        self.date = datetime.now()
        self.total = 0.0
        self.completed = False
        self.active = 1

    def __repr__(self):
        return f'<Invoices {self.id}>'

    @classmethod
    def get_paginated(cls, page=1, per_page=3):
        invoices = db.session.scalars(
            select(cls).order_by(cls.id).offset((page - 1) * per_page).limit(per_page)
        ).all()
        total = db.session.query(cls).count()
        return invoices, total

    @classmethod
    def get_by_id(cls, invoice_id):
        return db.session.get(cls, invoice_id)

    @staticmethod
    def save(invoice):
        db.session.add(invoice)
        db.session.commit()

    @staticmethod
    def update(invoice):
        db.session.add(invoice)
        db.session.commit()
