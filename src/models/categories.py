from sqlalchemy import Integer, String, select
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base, db


class Categories(Base):
    __tablename__ = 'categories'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f'<Categories {self.name}>'

    @classmethod
    def get_by_id(cls, category_id):
        return db.session.get(cls, category_id)

    @classmethod
    def get_by_name(cls, name):
        return db.session.scalar(select(cls).where(cls.name == name))

    @staticmethod
    def save(category):
        db.session.add(category)
        db.session.commit()

    @staticmethod
    def update(category):
        db.session.add(category)
        db.session.commit()
