from sqlalchemy import Float, ForeignKey, Integer, String, select
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base, db


class Products(Base):
    __tablename__ = 'products'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    price: Mapped[float] = mapped_column(Float, nullable=False)
    stock: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    category_id: Mapped[int] = mapped_column(ForeignKey('categories.id'), nullable=False)
    active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    def __init__(self, name, description, price, stock, category_id):
        self.name = name
        self.description = description
        self.price = price
        self.stock = stock
        self.category_id = category_id
        self.active = 1

    def __repr__(self):
        return f'<Products {self.name}>'

    @classmethod
    def get_paginated(cls, page=1, per_page=3):
        products = db.session.scalars(
            select(cls).offset((page - 1) * per_page).limit(per_page)
        ).all()
        total = db.session.query(cls).count()
        return products, total

    @classmethod
    def get_by_id(cls, product_id):
        return db.session.get(cls, product_id)

    @classmethod
    def get_by_name(cls, name):
        return db.session.scalar(select(cls).where(cls.name == name))

    @staticmethod
    def save(product):
        db.session.add(product)
        db.session.commit()

    @staticmethod
    def update(product):
        db.session.add(product)
        db.session.commit()
