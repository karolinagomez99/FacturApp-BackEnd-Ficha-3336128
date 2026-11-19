from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, scoped_session, sessionmaker


class Base(DeclarativeBase):
    pass


class Database:
    def __init__(self):
        self.engine = None
        self.session_factory = None

    def init_app(self, app):
        database_url = app.config.get('DATABASE_URL')
        if not database_url:
            raise RuntimeError('DATABASE_URL must be configured')

        self.engine = create_engine(
            database_url,
            pool_pre_ping=not database_url.startswith('sqlite'),
        )
        self.session_factory = scoped_session(
            sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)
        )
        app.teardown_appcontext(self.teardown_session)

    @property
    def session(self):
        if self.session_factory is None:
            raise RuntimeError('Database has not been initialized')
        return self.session_factory

    def create_all(self):
        if self.engine is None:
            raise RuntimeError('Database has not been initialized')
        Base.metadata.create_all(self.engine)

    def teardown_session(self, exception=None):
        if self.session_factory is None:
            return
        if exception is not None:
            self.session.rollback()
        self.session.remove()


db = Database()
