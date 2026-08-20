# AI Agent Memory System

Production-grade memory system for AI agents with SQLite + FTS5 backend.

## Architecture

- **Phase 1**: Semantic Memory Storage (SQLite + FTS5) - ✅ Complete
- **Phase 2**: Retrieval Gate (Hybrid Search) - ✅ Complete
- **Phase 3**: Memory Maintenance & Dreaming - ✅ Complete
- **Phase 4**: CLI Tool Integration (Typer + Rich) - ⏳ Planned
- **Evaluation & Observability** - ⏳ Planned

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Copy .env.example to .env and add your OpenRouter API key
cp .env.example .env

# Run demo
python main.py

# Run tests
PYTHONPATH=src python -m pytest tests/ -v
```

## Project Structure

```
├── config.py              # Pydantic Settings (env-driven)
├── main.py                # Demo / usage example
├── requirements.txt       # Pinned dependencies
├── pyproject.toml         # Modern packaging + tool config
├── .env                   # Local environment (gitignored)
├── .env.example           # Template for environment variables
├── src/memory/
│   ├── __init__.py        # Public API exports
│   ├── models.py          # SQLAlchemy ORM models (SemanticMemory, EpisodicLog)
│   ├── database.py        # Connection & schema management
│   ├── ddl.py             # FTS5 DDL + triggers via SQLAlchemy events
│   ├── repository.py      # CRUD operations (Repository pattern)
│   ├── retrieval.py       # Retrieval Gate (Phase 2)
│   ├── schemas.py         # Pydantic validation models
│   ├── protocols.py       # Abstract interfaces (Protocol)
│   ├── exceptions.py      # Custom exception hierarchy
│   ├── logging.py         # Structured JSON logging
│   ├── consolidation.py   # Pure async consolidation logic (Phase 3)
│   ├── episodic.py        # EpisodicLog model + repository (Phase 3)
│   ├── worker.py          # Async DreamingWorker (Phase 3)
│   ├── maintenance.py     # MemoryMaintenance facade (Phase 3)
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── protocol.py    # LLMClientProtocol, LLMResponse
│   │   └── client.py      # Async OpenRouter client with retry logic
│   └── prompts/
│       ├── loader.py      # PromptLoader with version resolution
│       └── consolidation_v1.txt  # Versioned prompt template
├── tests/
│   ├── conftest.py        # Shared fixtures
│   ├── test_config.py     # Settings validation
│   ├── test_repository.py # CRUD + FTS tests
│   ├── test_retrieval.py  # Retrieval Gate tests
│   ├── test_prompts.py    # PromptLoader tests (Phase 3)
│   ├── test_consolidation.py # Consolidation logic tests (Phase 3)
│   ├── test_episodic.py   # EpisodicLog tests (Phase 3)
│   └── test_worker.py     # DreamingWorker tests (Phase 3)
└── trash/                 # Archive (gitignored)
```

## Configuration

All settings via `.env` (see `.env.example`):

### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_PATH` | `state.db` | SQLite database file path |
| `LOG_LEVEL` | `INFO` | Logging level |
| `FTS5_QUERY_LIMIT` | `10` | Max FTS5 search results |
| `RETRIEVAL_KEYWORD_LIMIT` | `5` | Keyword search limit |
| `RETRIEVAL_RECENT_LIMIT` | `10` | Recent facts limit |

### Phase 3: OpenRouter & Consolidation

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | *required* | OpenRouter API key |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | OpenRouter base URL |
| `CONSOLIDATION_MODEL` | `nvidia/nemotron-3-ultra-550b-a55b:free` | Consolidation model |
| `CONSOLIDATION_MAX_TOKENS` | `1024` | Max tokens for consolidation |
| `CONSOLIDATION_TEMPERATURE` | `0.1` | Temperature for consolidation |
| `CONSOLIDATION_PROMPT_VERSION` | `latest` | Prompt version for consolidation |

### Phase 3: Worker Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DREAM_INTERVAL_MINUTES` | `60` | Dream interval in minutes |
| `DREAM_BATCH_SIZE` | `50` | Batch size for consolidation |
| `DREAM_MIN_MESSAGES` | `10` | Minimum messages for consolidation |
| `PROMPTS_DIR` | `src/memory/prompts` | Prompts directory path |

## Usage

### Phase 1-2: Semantic Memory & Retrieval

```python
from memory import (
    Database,
    RetrievalGate,
    SemanticMemoryCreate,
    SemanticMemoryUpdate,
    create_database,
    create_retrieval_gate,
    get_settings,
)

# Initialize with settings from .env
settings = get_settings()
db = create_database(settings)

# Add facts (validated via Pydantic)
with db.session() as session:
    from memory import create_repository
    repo = create_repository(session)

    repo.add_fact(SemanticMemoryCreate(entity="user", fact="User prefers dark mode", source="preferences"))
    repo.add_fact(SemanticMemoryCreate(entity="user", fact="User works as a software engineer", source="profile"))
    repo.add_fact(SemanticMemoryCreate(entity="project", fact="Project uses Python 3.11", source="config"))

    # Supersede (invalidates old, adds new with valid_to timestamp)
    repo.supersede_fact("user", SemanticMemoryUpdate(fact="User prefers light mode", source="preferences_updated"))

# Retrieve context for LLM prompt injection
gate = create_retrieval_gate(db)
context = gate.build_context("user prefers")
# Returns formatted context block

# Search API
results = gate.search("Python", limit=5)
```

### Phase 3: Memory Maintenance & Dreaming

```python
import asyncio
from memory import (
    MemoryMaintenance,
    create_database,
    get_settings,
)

async def main():
    settings = get_settings()
    db = create_database(settings)
    maintenance = MemoryMaintenance(db, settings)

    # Option 1: Run consolidation once (manual trigger)
    result = await maintenance.consolidate_once(session_id="session-123")
    print(f"Extracted: {result.facts_extracted}, Upserted: {result.facts_upserted}")

    # Option 2: Start background worker (runs every DREAM_INTERVAL_MINUTES)
    async with maintenance.worker() as worker:
        # Worker runs consolidation in background
        # Keep alive...
        await asyncio.sleep(3600)  # Run for 1 hour

    # Option 3: Check worker stats
    stats = maintenance.get_worker_stats()
    print(f"Total runs: {stats.total_runs}, Facts extracted: {stats.total_facts_extracted}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Episodic Logging (for Dreaming)

```python
from memory import create_database, get_settings
from memory.episodic import create_episodic_repository

settings = get_settings()
db = create_database(settings)

with db.session() as session:
    episodic_repo = create_episodic_repository(session)
    
    # Log user/assistant interactions
    episodic_repo.add_log("session-123", "user", "I prefer dark mode")
    episodic_repo.add_log("session-123", "assistant", "Noted! I'll remember that.")
    episodic_repo.add_log("session-123", "user", "Also, the project uses Python 3.11")
    
    # Later, trigger consolidation to extract semantic facts
    # from these episodic logs
```

## Features

### Phase 1-2: Core Memory
- **Valid-time semantics**: `valid_from` / `valid_to` for fact supersession
- **FTS5 full-text search**: Keyword search with ranking (BM25)
- **Auto-sync triggers**: FTS5 index maintained via SQLite triggers (INSERT/UPDATE/DELETE)
- **Repository pattern**: Clean separation of data access
- **Retrieval Gate**: Priority-based context building (keyword match > recent)
- **Pydantic validation**: Input/output validation via `SemanticMemoryCreate`, `SemanticMemoryRead`, etc.
- **Structured logging**: JSON logs with context (entity, fact_id, query)
- **Custom exceptions**: `DatabaseError`, `RetrievalError`, `NotFoundError`, `ValidationError`
- **Protocol interfaces**: `MemoryRepositoryProtocol`, `RetrievalProtocol` for swappability
- **Config-driven**: All limits via `Settings` from `.env`
- **Testable**: Factory functions (`create_repository`, `create_database`, `create_retrieval_gate`)

### Phase 3: Memory Maintenance & Dreaming
- **Episodic logging**: Raw interaction storage with session grouping
- **Async consolidation**: Background "dreaming" extracts semantic facts from episodic logs
- **Versioned prompts**: `.txt` templates in `prompts/` with `PromptLoader` (v1, v2, latest)
- **OpenRouter integration**: Async `httpx` client with `reasoning_details` support
- **Exponential backoff**: 3 retries with `tenacity` (1s → 2s → 4s)
- **Pure async worker**: No threads, `asyncio.TaskGroup`, graceful shutdown
- **Structured output**: JSON array of `{entity, fact, is_update}` facts
- **Deduplication & validation**: Pydantic validation at boundaries
- **Observability**: Consolidation stats (runs, facts, errors, duration)

## Requirements

- Python 3.11+
- SQLAlchemy 2.0+
- SQLite with FTS5 support (standard)
- OpenRouter API key (for Phase 3)

## Testing

```bash
# Run all tests
PYTHONPATH=src python -m pytest tests/ -v

# Run specific test file
PYTHONPATH=src python -m pytest tests/test_repository.py -v

# Run Phase 3 tests
PYTHONPATH=src python -m pytest tests/test_prompts.py tests/test_consolidation.py tests/test_episodic.py tests/test_worker.py -v
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Lint
ruff check src/

# Type check
mypy src/
```

## Senior Engineer Practices Applied

- **Single Responsibility**: Each module has one job
- **Dependency Injection**: `Database`, `Repository`, `RetrievalGate`, `DreamingWorker` accept dependencies
- **Protocol Interfaces**: Abstract base for swappable backends (`LLMClientProtocol`, `MemoryRepositoryProtocol`)
- **Config via Environment**: No hardcoded values; all via `pydantic-settings`
- **Structured Logging**: JSON with context; `warning` for recoverable, `exception` on caught errors
- **Custom Exceptions**: Typed error hierarchy for clear handling
- **Validation at Boundaries**: Pydantic schemas for API, not just data carriers
- **YAGNI**: No Phase 4 code yet; only what's needed for Phase 1-3
- **Immutable Results**: `frozen=True` dataclasses for context blocks, results
- **Timezone-aware**: `datetime.now(timezone.utc)` throughout
- **Prompt Versioning**: Git-trackable `.txt` templates, no code deployment for prompt changes
- **Retry Logic**: Exponential backoff with `tenacity`, circuit-breaker patterns
- **Async-First**: No blocking calls, `asyncio` native, no thread pools