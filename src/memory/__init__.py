from .config import Settings, get_settings, ensure_db_dir
from .consolidation import ConsolidationResult, ConsolidatedFact, consolidate_session
from .database import Database, create_database
from .ddl import setup_ddl_listeners, setup_engine_pragmas
from .episodic import EpisodicLog, EpisodicRepository, create_episodic_repository
from .exceptions import (
    MemoryError,
    DatabaseError,
    RetrievalError,
    ConsolidationError,
    ValidationError,
    NotFoundError,
)
from .logging import get_logger, StructuredLogger
from .llm import (
    LLMClientProtocol,
    LLMResponse,
    MockLLMClient,
    OpenRouterClient,
    LLMClientError,
    AuthenticationError,
    InsufficientCreditsError,
)
from .maintenance import MemoryMaintenance
from .models import SemanticMemory
from .prompts.loader import PromptLoader
from .protocols import MemoryRepositoryProtocol, RetrievalProtocol
from .repository import MemoryRepository, create_repository
from .retrieval import ContextBlock, RetrievalGate, create_retrieval_gate
from .schemas import (
    SemanticMemoryBase,
    SemanticMemoryCreate,
    SemanticMemoryRead,
    SemanticMemorySearchResult,
    SemanticMemoryUpdate,
)
from .worker import DreamingWorker, ConsolidationStats

__all__ = [
    "Settings",
    "get_settings",
    "ensure_db_dir",
    "Database",
    "create_database",
    "setup_ddl_listeners",
    "setup_engine_pragmas",
    "MemoryError",
    "DatabaseError",
    "RetrievalError",
    "ConsolidationError",
    "ValidationError",
    "NotFoundError",
    "get_logger",
    "StructuredLogger",
    "SemanticMemory",
    "MemoryRepositoryProtocol",
    "RetrievalProtocol",
    "MemoryRepository",
    "create_repository",
    "ContextBlock",
    "RetrievalGate",
    "create_retrieval_gate",
    "SemanticMemoryBase",
    "SemanticMemoryCreate",
    "SemanticMemoryRead",
    "SemanticMemorySearchResult",
    "SemanticMemoryUpdate",
    # Phase 3
    "EpisodicLog",
    "EpisodicRepository",
    "create_episodic_repository",
    "LLMClientProtocol",
    "LLMResponse",
    "MockLLMClient",
    "OpenRouterClient",
    "LLMClientError",
    "AuthenticationError",
    "InsufficientCreditsError",
    "PromptLoader",
    "ConsolidationResult",
    "ConsolidatedFact",
    "consolidate_session",
    "DreamingWorker",
    "ConsolidationStats",
    "MemoryMaintenance",
]