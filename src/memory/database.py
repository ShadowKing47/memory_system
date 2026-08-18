from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from .models import Base


class Database:
    def __init__(self, db_path: str = "state.db"):
        self.db_path = Path(db_path).resolve()
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
            echo=False,
        )
        self.SessionLocal = sessionmaker(
            bind=self.engine, autoflush=False, autocommit=False
        )
        self._init_db()

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        Base.metadata.create_all(self.engine)
        with self.engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.execute(text("""
                CREATE VIRTUAL TABLE IF NOT EXISTS semantic_memory_fts USING fts5(
                    fact, content='semantic_memory', content_rowid='id'
                )
            """))
            conn.execute(text("""
                CREATE TRIGGER IF NOT EXISTS semantic_memory_ai AFTER INSERT ON semantic_memory BEGIN
                    INSERT INTO semantic_memory_fts(rowid, fact) VALUES (new.id, new.fact);
                END
            """))
            conn.execute(text("""
                CREATE TRIGGER IF NOT EXISTS semantic_memory_ad AFTER DELETE ON semantic_memory BEGIN
                    INSERT INTO semantic_memory_fts(semantic_memory_fts, rowid, fact)
                    VALUES ('delete', old.id, old.fact);
                END
            """))
            conn.execute(text("""
                CREATE TRIGGER IF NOT EXISTS semantic_memory_au AFTER UPDATE ON semantic_memory BEGIN
                    INSERT INTO semantic_memory_fts(semantic_memory_fts, rowid, fact)
                    VALUES ('delete', old.id, old.fact);
                    INSERT INTO semantic_memory_fts(rowid, fact) VALUES (new.id, new.fact);
                END
            """))

    @contextmanager
    def session(self) -> Session:
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_session(self) -> Session:
        return self.SessionLocal()