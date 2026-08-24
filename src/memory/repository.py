from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from memory.config import get_settings
from .exceptions import DatabaseError, NotFoundError
from .logging import get_logger
from .models import SemanticMemory
from .protocols import MemoryRepositoryProtocol
from .schemas import (
    SemanticMemoryCreate,
    SemanticMemoryRead,
    SemanticMemorySearchResult,
    SemanticMemoryUpdate,
)


class MemoryRepository:
    def __init__(self, session: Session):
        self._session = session
        self._settings = get_settings()
        self._logger = get_logger(__name__)

    @property
    def session(self) -> Session:
        return self._session

    def add_fact(self, data: SemanticMemoryCreate, valid_from: Optional[datetime] = None) -> SemanticMemoryRead:
        try:
            memory = SemanticMemory(
                entity=data.entity,
                fact=data.fact,
                source=data.source,
                valid_from=valid_from or datetime.now(timezone.utc),
            )
            self._session.add(memory)
            self._session.flush()
            self._logger.info("fact_added", entity=data.entity, fact_id=memory.id)
            return SemanticMemoryRead.model_validate(memory)
        except Exception as e:
            self._logger.exception("fact_add_failed", entity=data.entity, error=str(e))
            raise DatabaseError("Failed to add fact", e) from e

    def supersede_fact(self, entity: str, data: SemanticMemoryUpdate) -> SemanticMemoryRead:
        try:
            now = datetime.now(timezone.utc)
            self._session.execute(
                update(SemanticMemory)
                .where(SemanticMemory.entity == entity)
                .where(SemanticMemory.valid_to.is_(None))
                .values(valid_to=now)
            )
            memory = SemanticMemory(
                entity=entity,
                fact=data.fact,
                source=data.source,
                valid_from=now,
            )
            self._session.add(memory)
            self._session.flush()
            self._logger.info("fact_superseded", entity=entity, new_fact_id=memory.id)
            return SemanticMemoryRead.model_validate(memory)
        except Exception as e:
            self._logger.exception("fact_supersede_failed", entity=entity, error=str(e))
            raise DatabaseError("Failed to supersede fact", e) from e

    def search_facts(self, query: str, limit: int | None = None) -> list[SemanticMemorySearchResult]:
        limit = limit or self._settings.fts5_query_limit
        sanitized_query = self._sanitize_fts_query(query)
        try:
            stmt = text(
                """
                SELECT m.* FROM semantic_memory m
                JOIN semantic_memory_fts f ON m.id = f.rowid
                WHERE semantic_memory_fts MATCH :query
                AND m.valid_to IS NULL
                ORDER BY rank
                LIMIT :limit
                """
            ).bindparams(query=sanitized_query, limit=limit)
            results = self._session.execute(select(SemanticMemory).from_statement(stmt)).scalars().all()
            self._logger.debug("fact_search", query=sanitized_query, results=len(results))
            return [SemanticMemorySearchResult.model_validate(r) for r in results]
        except Exception as e:
            self._logger.exception("fact_search_failed", query=sanitized_query, error=str(e))
            raise DatabaseError("Failed to search facts", e) from e

    @staticmethod
    def _sanitize_fts_query(query: str) -> str:
        special_chars = ['"', "'", "?", "*", "-", "+", "^", "(", ")", ":", "|"]
        for char in special_chars:
            query = query.replace(char, " ")
        return " ".join(query.split())

    def get_valid_facts_by_entity(self, entity: str) -> list[SemanticMemoryRead]:
        try:
            memories = list(
                self._session.execute(
                    select(SemanticMemory).where(
                        SemanticMemory.entity == entity,
                        SemanticMemory.valid_to.is_(None),
                    )
                ).scalars().all()
            )
            return [SemanticMemoryRead.model_validate(m) for m in memories]
        except Exception as e:
            self._logger.exception("get_facts_by_entity_failed", entity=entity, error=str(e))
            raise DatabaseError("Failed to get facts by entity", e) from e

    def get_all_valid_facts(self, limit: int | None = None) -> list[SemanticMemoryRead]:
        limit = limit or self._settings.retrieval_recent_limit
        try:
            memories = list(
                self._session.execute(
                    select(SemanticMemory)
                    .where(SemanticMemory.valid_to.is_(None))
                    .limit(limit)
                ).scalars().all()
            )
            return [SemanticMemoryRead.model_validate(m) for m in memories]
        except Exception as e:
            self._logger.exception("get_all_facts_failed", error=str(e))
            raise DatabaseError("Failed to get all facts", e) from e

    def get_all_facts(self, limit: int | None = None) -> list[SemanticMemoryRead]:
        limit = limit or self._settings.retrieval_recent_limit
        try:
            memories = list(
                self._session.execute(
                    select(SemanticMemory).limit(limit)
                ).scalars().all()
            )
            return [SemanticMemoryRead.model_validate(m) for m in memories]
        except Exception as e:
            self._logger.exception("get_all_facts_failed", error=str(e))
            raise DatabaseError("Failed to get all facts", e) from e

    def delete_fact(self, fact_id: int) -> bool:
        try:
            memory = self._session.get(SemanticMemory, fact_id)
            if not memory:
                raise NotFoundError("Fact", fact_id)
            self._session.delete(memory)
            self._session.flush()
            self._logger.info("fact_deleted", fact_id=fact_id)
            return True
        except NotFoundError:
            raise
        except Exception as e:
            self._logger.exception("fact_delete_failed", fact_id=fact_id, error=str(e))
            raise DatabaseError("Failed to delete fact", e) from e


def create_repository(session: Session) -> MemoryRepositoryProtocol:
    return MemoryRepository(session)