from typing import Protocol, runtime_checkable

from .schemas import (
    SemanticMemoryCreate,
    SemanticMemoryRead,
    SemanticMemorySearchResult,
    SemanticMemoryUpdate,
)


@runtime_checkable
class MemoryRepositoryProtocol(Protocol):
    def add_fact(self, data: SemanticMemoryCreate) -> SemanticMemoryRead: ...

    def supersede_fact(self, entity: str, data: SemanticMemoryUpdate) -> SemanticMemoryRead: ...

    def search_facts(self, query: str, limit: int) -> list[SemanticMemorySearchResult]: ...

    def get_valid_facts_by_entity(self, entity: str) -> list[SemanticMemoryRead]: ...

    def get_all_valid_facts(self, limit: int) -> list[SemanticMemoryRead]: ...

    def delete_fact(self, fact_id: int) -> bool: ...


@runtime_checkable
class RetrievalProtocol(Protocol):
    def build_context(
        self,
        user_query: str,
        keyword_limit: int | None = None,
        include_recent: bool = False,
        recent_limit: int | None = None,
    ) -> str: ...

    def search(self, query: str, limit: int) -> list[dict]: ...