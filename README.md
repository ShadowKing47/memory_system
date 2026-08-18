# AI Agent Memory System

Production-grade memory system for AI agents with SQLite + FTS5 backend.

## Architecture

- **Phase 1**: Semantic Memory Storage (SQLite + FTS5) - ✅ Complete
- **Phase 2**: Retrieval Gate (Hybrid Search) - ✅ Complete
- **Phase 3**: Memory Maintenance & Dreaming - ⏳ Planned
- **Evaluation & Observability** - ⏳ Planned

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run demo
PYTHONPATH=src python -m memory.main
```

## Project Structure

```
src/memory/
├── __init__.py      # Public API
├── models.py        # SQLAlchemy ORM models
├── database.py      # Connection & schema management
├── repository.py    # CRUD operations (Repository pattern)
├── retrieval.py     # Retrieval Gate (Phase 2)
└── main.py          # Demo / usage example
```

## Usage

```python
from memory import Database, RetrievalGate

db = Database("state.db")

# Add facts
with db.session() as session:
    repo = MemoryRepository(session)
    repo.add_fact("user", "User prefers dark mode")
    repo.add_fact("project", "Uses Python 3.11")

# Supersede (invalidates old, adds new)
repo.supersede_fact("user", "User prefers light mode")

# Retrieve context for LLM
gate = RetrievalGate(db)
context = gate.build_context("What does the user prefer?")
# Returns formatted context block for prompt injection

# Search API
results = gate.search("Python", limit=5)
```

## Features

- **Valid-time semantics**: `valid_from` / `valid_to` for fact supersession
- **FTS5 full-text search**: Keyword search with ranking
- **Auto-sync triggers**: FTS5 index maintained via SQLite triggers
- **Repository pattern**: Clean separation of data access
- **Retrieval Gate**: Priority-based context building

## Requirements

- Python 3.11+
- SQLAlchemy 2.0+
- SQLite with FTS5 support (standard)

## Testing

```bash
PYTHONPATH=src python -m memory.main
```