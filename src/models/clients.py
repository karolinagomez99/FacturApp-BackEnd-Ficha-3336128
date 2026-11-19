from enum import Enum

from sqlalchemy import Integer, String, select
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base, db


class DocumentType(str, Enum):
    CC = 'CC'
    NIT = 'NIT'
    CE = 'CE'


class Clients(Base):
    __tablename__ = 'clients'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_type: Mapped[str] = mapped_column(String(10), nullable=False)
    document_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    def __init__(
        self, document_type, document_number, name, email, phone, address,
        active=1,
    ):
        self.document_type = (
            document_type.value if isinstance(document_type, DocumentType) else document_type
        )
        self.document_number = document_number
        self.name = name
        self.email = email
        self.phone = phone
        self.address = address
        self.active = active

    def __repr__(self):
        return f'<Clients {self.document_number}>'

    @classmethod
    def get_paginated(cls, page=1, per_page=3):
        clients = db.session.scalars(
            select(cls).offset((page - 1) * per_page).limit(per_page)
        ).all()
        total = db.session.query(cls).count()
        return clients, total

    @classmethod
    def get_by_id(cls, client_id):
        return db.session.get(cls, client_id)

    @classmethod
    def get_by_document_number(cls, document_number):
        return db.session.scalar(
            select(cls).where(cls.document_number == document_number)
        )

    @staticmethod
    def save(client):
        db.session.add(client)
        db.session.commit()

    @staticmethod
    def update(client):
        db.session.add(client)
        db.session.commit()
