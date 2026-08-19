from sqlalchemy import DDL, event
from sqlalchemy.engine import Engine

from .models import SemanticMemory


FTS5_CREATE = DDL("""
    CREATE VIRTUAL TABLE IF NOT EXISTS semantic_memory_fts USING fts5(
        fact, content='semantic_memory', content_rowid='id'
    )
""").execute_if(dialect="sqlite")

TRIGGER_AI = DDL("""
    CREATE TRIGGER IF NOT EXISTS semantic_memory_ai AFTER INSERT ON semantic_memory BEGIN
        INSERT INTO semantic_memory_fts(rowid, fact) VALUES (new.id, new.fact);
    END
""").execute_if(dialect="sqlite")

TRIGGER_AD = DDL("""
    CREATE TRIGGER IF NOT EXISTS semantic_memory_ad AFTER DELETE ON semantic_memory BEGIN
        INSERT INTO semantic_memory_fts(semantic_memory_fts, rowid, fact)
        VALUES ('delete', old.id, old.fact);
    END
""").execute_if(dialect="sqlite")

TRIGGER_AU = DDL("""
    CREATE TRIGGER IF NOT EXISTS semantic_memory_au AFTER UPDATE ON semantic_memory BEGIN
        INSERT INTO semantic_memory_fts(semantic_memory_fts, rowid, fact)
        VALUES ('delete', old.id, old.fact);
        INSERT INTO semantic_memory_fts(rowid, fact) VALUES (new.id, new.fact);
    END
""").execute_if(dialect="sqlite")


FTS5_DROP = DDL("""
    DROP TRIGGER IF EXISTS semantic_memory_ai;
    DROP TRIGGER IF EXISTS semantic_memory_ad;
    DROP TRIGGER IF EXISTS semantic_memory_au;
    DROP TABLE IF EXISTS semantic_memory_fts;
""").execute_if(dialect="sqlite")


def setup_ddl_listeners() -> None:
    event.listen(SemanticMemory.__table__, "after_create", FTS5_CREATE)
    event.listen(SemanticMemory.__table__, "after_create", TRIGGER_AI)
    event.listen(SemanticMemory.__table__, "after_create", TRIGGER_AD)
    event.listen(SemanticMemory.__table__, "after_create", TRIGGER_AU)
    event.listen(SemanticMemory.__table__, "before_drop", FTS5_DROP)


def setup_engine_pragmas(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def set_pragmas(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()