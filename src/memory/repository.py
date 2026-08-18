from datetime import datetime
from typing import Optional

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from .models import SemanticMemory


class MemoryRepository:
    def __init__(self, session: Session):
        self.session = session

    def add_fact(
        self,
        entity: str,
        fact: str,
        source: Optional[str] = None,
        valid_from: Optional[datetime] = None,
    ) -> SemanticMemory:
        memory = SemanticMemory(
            entity=entity,
            fact=fact,
            source=source,
            valid_from=valid_from or datetime.utcnow(),
        )
        self.session.add(memory)
        self.session.flush()
        return memory

    def supersede_fact(self, entity: str, new_fact: str, source: Optional[str] = None) -> SemanticMemory:
        now = datetime.utcnow()
        self.session.execute(
            update(SemanticMemory)
            .where(SemanticMemory.entity == entity)
            .where(SemanticMemory.valid_to.is_(None))
            .values(valid_to=now)
        )
        return self.add_fact(entity, new_fact, source, now)

    def search_facts(self, query: str, limit: int = 10) -> list[SemanticMemory]:
        sanitized_query = self._sanitize_fts_query(query)
        results = self.session.execute(
            text(
                """
                SELECT m.* FROM semantic_memory m
                JOIN semantic_memory_fts f ON m.id = f.rowid
                WHERE semantic_memory_fts MATCH :query
                AND m.valid_to IS NULL
                ORDER BY rank
                LIMIT :limit
                """
            ),
            {"query": sanitized_query, "limit": limit},
        ).mappings().all()
        return [self.session.get(SemanticMemory, r["id"]) for r in results]

    @staticmethod
    def _sanitize_fts_query(query: str) -> str:
        special_chars = ['"', "'", "?", "*", "-", "+", "^", "(", ")", ":", "|"]
        for char in special_chars:
            query = query.replace(char, " ")
        return " ".join(query.split())

    def get_valid_facts_by_entity(self, entity: str) -> list[SemanticMemory]:
        return list(
            self.session.execute(
                select(SemanticMemory).where(
                    SemanticMemory.entity == entity,
                    SemanticMemory.valid_to.is_(None),
                )
            ).scalars().all()
        )

    def get_all_valid_facts(self, limit: int = 100) -> list[SemanticMemory]:
        return list(
            self.session.execute(
                select(SemanticMemory)
                .where(SemanticMemory.valid_to.is_(None))
                .limit(limit)
            ).scalars().all()
        )

    def delete_fact(self, fact_id: int) -> bool:
        memory = self.session.get(SemanticMemory, fact_id)
        if memory:
            self.session.delete(memory)
            return True
        return False