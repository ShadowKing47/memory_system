from dataclasses import dataclass
from typing import Optional

from .database import Database
from .repository import MemoryRepository


@dataclass
class ContextBlock:
    label: str
    content: str
    priority: int = 0


class RetrievalGate:
    def __init__(self, db: Database):
        self.db = db

    def build_context(
        self,
        user_query: str,
        keyword_limit: int = 5,
        include_recent: bool = False,
        recent_limit: int = 10,
    ) -> str:
        context_blocks = []

        with self.db.session() as session:
            repo = MemoryRepository(session)

            keyword_results = repo.search_facts(user_query, limit=keyword_limit)
            if keyword_results:
                facts = "\n".join([f"- {r.fact}" for r in keyword_results])
                context_blocks.append(
                    ContextBlock(
                        label="Relevant Facts (Keyword Match)",
                        content=facts,
                        priority=1,
                    )
                )

            if include_recent:
                recent_facts = repo.get_all_valid_facts(limit=recent_limit)
                if recent_facts:
                    facts = "\n".join([f"- {r.fact}" for r in recent_facts])
                    context_blocks.append(
                        ContextBlock(
                            label="Recent Facts",
                            content=facts,
                            priority=2,
                        )
                    )

        context_blocks.sort(key=lambda b: b.priority)

        if not context_blocks:
            return ""

        return "\n\n".join(f"{block.label}:\n{block.content}" for block in context_blocks)

    def search(self, query: str, limit: int = 5) -> list[dict]:
        with self.db.session() as session:
            repo = MemoryRepository(session)
            results = repo.search_facts(query, limit=limit)
            return [
                {
                    "id": r.id,
                    "entity": r.entity,
                    "fact": r.fact,
                    "source": r.source,
                    "valid_from": r.valid_from.isoformat() if r.valid_from else None,
                }
                for r in results
            ]