from enum import Enum

from sqlalchemy import Integer, String, select
from sqlalchemy.orm import Mapped, mapped_column
from werkzeug.security import check_password_hash, generate_password_hash

from src.models import Base, db


class Role(str, Enum):
    ADMIN = 'ADMIN'
    SELLER = 'SELLER'
    PENDING = 'PENDING'


class Users(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=Role.PENDING.value)
    active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    def __init__(self, email, password, name, role=Role.PENDING.value):
        self.email = email
        self.password = generate_password_hash(password)
        self.name = name
        self.role = role.value if isinstance(role, Role) else role
        self.active = 1

    def __repr__(self):
        return f'<Users {self.email}>'

    @classmethod
    def get_by_id(cls, user_id):
        return db.session.get(cls, user_id)

    @classmethod
    def get_by_email(cls, email):
        return db.session.scalar(select(cls).where(cls.email == email))

    @classmethod
    def get_paginated(cls, page=1, per_page=3):
        query = select(cls).offset((page - 1) * per_page).limit(per_page)
        users = db.session.scalars(query).all()
        total = db.session.query(cls).count()
        return users, total

    def check_password(self, password):
        return check_password_hash(self.password, password)

    @staticmethod
    def save(user):
        db.session.add(user)
        db.session.commit()

    @staticmethod
    def update(user):
        db.session.add(user)
        db.session.commit()
