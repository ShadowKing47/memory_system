# AI Agent Memory System

Production-grade memory system for AI agents with SQLite + FTS5 backend.

## Architecture

- **Phase 1**: Semantic Memory Storage (SQLite + FTS5) - ✅ Complete
- **Phase 2**: Retrieval Gate (Hybrid Search) - ✅ Complete
- **Phase 3**: Memory Maintenance & Dreaming - ⏳ Planned
- **Phase 4**: CLI Tool Integration (Typer + Rich) - ⏳ Planned
- **Evaluation & Observability** - ⏳ Planned

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run demo
python main.py
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
│   ├── models.py          # SQLAlchemy ORM models
│   ├── database.py        # Connection & schema management
│   ├── ddl.py             # FTS5 DDL + triggers via SQLAlchemy events
│   ├── repository.py      # CRUD operations (Repository pattern)
│   ├── retrieval.py       # Retrieval Gate (Phase 2)
│   ├── schemas.py         # Pydantic validation models
│   ├── protocols.py       # Abstract interfaces (Protocol)
│   ├── exceptions.py      # Custom exception hierarchy
│   └── logging.py         # Structured JSON logging
├── tests/
│   ├── conftest.py        # Shared fixtures
│   ├── test_config.py     # Settings validation
│   ├── test_repository.py # CRUD + FTS tests
│   └── test_retrieval.py  # Retrieval Gate tests
└── trash/                 # Archive (gitignored)
```

## Configuration

All settings via `.env` (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_PATH` | `state.db` | SQLite database file path |
| `LOG_LEVEL` | `INFO` | Logging level |
| `FTS5_QUERY_LIMIT` | `10` | Max FTS5 search results |
| `RETRIEVAL_KEYWORD_LIMIT` | `5` | Keyword search limit |
| `RETRIEVAL_RECENT_LIMIT` | `10` | Recent facts limit |

## Usage

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

## Features

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

## Requirements

- Python 3.11+
- SQLAlchemy 2.0+
- SQLite with FTS5 support (standard)

## Testing

```bash
# Run all tests
PYTHONPATH=src python -m pytest tests/ -v

# Run specific test file
PYTHONPATH=src python -m pytest tests/test_repository.py -v
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
