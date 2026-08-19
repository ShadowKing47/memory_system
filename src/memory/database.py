from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config import Settings, ensure_db_dir
from .ddl import setup_ddl_listeners, setup_engine_pragmas
from .logging import get_logger
from .models import Base


class Database:
    def __init__(self, settings: Settings | None = None):
        self._settings = settings or Settings()
        self._logger = get_logger(__name__)
        self._engine = self._create_engine()
        self._SessionLocal = sessionmaker(
            bind=self._engine, autoflush=False, autocommit=False
        )
        setup_ddl_listeners()
        setup_engine_pragmas(self._engine)
        self._init_db()

    def _create_engine(self):
        return create_engine(
            f"sqlite:///{self._settings.db_path}",
            connect_args={"check_same_thread": False},
            echo=False,
        )

    def _init_db(self) -> None:
        ensure_db_dir(self._settings)
        Base.metadata.create_all(self._engine)
        self._logger.info("database_initialized", path=self._settings.db_path)

    @property
    def engine(self):
        return self._engine

    @contextmanager
    def session(self) -> Session:
        session = self._SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_session(self) -> Session:
        return self._SessionLocal()


def create_database(settings: Settings | None = None) -> Database:
    return Database(settings)