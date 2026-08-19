from dataclasses import dataclass

from config import get_settings
from .database import Database
from .exceptions import RetrievalError
from .logging import get_logger
from .protocols import RetrievalProtocol
from .repository import MemoryRepository, create_repository


@dataclass(frozen=True)
class ContextBlock:
    label: str
    content: str
    priority: int = 0


class RetrievalGate:
    def __init__(self, db: Database):
        self._db = db
        self._settings = get_settings()
        self._logger = get_logger(__name__)

    def build_context(
        self,
        user_query: str,
        keyword_limit: int | None = None,
        include_recent: bool = False,
        recent_limit: int | None = None,
    ) -> str:
        keyword_limit = keyword_limit or self._settings.retrieval_keyword_limit
        recent_limit = recent_limit or self._settings.retrieval_recent_limit

        context_blocks = []

        try:
            with self._db.session() as session:
                repo = create_repository(session)

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
                self._logger.debug("context_empty", query=user_query)
                return ""

            result = "\n\n".join(f"{block.label}:\n{block.content}" for block in context_blocks)
            self._logger.debug("context_built", query=user_query, blocks=len(context_blocks))
            return result

        except Exception as e:
            self._logger.exception("context_build_failed", query=user_query, error=str(e))
            raise RetrievalError("Failed to build context", e) from e

    def search(self, query: str, limit: int | None = None) -> list[dict]:
        limit = limit or self._settings.fts5_query_limit
        try:
            with self._db.session() as session:
                repo = create_repository(session)
                results = repo.search_facts(query, limit=limit)
                return [
                    {
                        "id": r.id,
                        "entity": r.entity,
                        "fact": r.fact,
                        "source": r.source,
                        "valid_from": r.valid_from.isoformat() if r.valid_from else None,
                        "valid_to": r.valid_to.isoformat() if r.valid_to else None,
                    }
                    for r in results
                ]
        except Exception as e:
            self._logger.exception("search_failed", query=query, error=str(e))
            raise RetrievalError("Failed to search", e) from e


def create_retrieval_gate(db: Database) -> RetrievalProtocol:
    return RetrievalGate(db)