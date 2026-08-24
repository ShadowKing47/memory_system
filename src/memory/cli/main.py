import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from memory import get_settings
from memory import (
    Database,
    RetrievalGate,
    SemanticMemoryCreate,
    SemanticMemoryUpdate,
    create_database,
    create_retrieval_gate,
    create_repository,
    MemoryMaintenance,
    ConsolidationResult,
)
from memory.episodic import create_episodic_repository

app = typer.Typer(
    name="memory",
    help="AI Agent Memory System CLI",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()


def get_db() -> Database:
    return create_database(get_settings())


@app.command()
def add(
    entity: str = typer.Argument(..., help="Entity name (e.g., user, project)"),
    fact: str = typer.Argument(..., help="Fact to store"),
    source: str = typer.Option("cli", "--source", help="Source of the fact"),
):
    """Add a semantic fact."""
    db = get_db()
    with db.session() as session:
        repo = create_repository(session)
        repo.add_fact(SemanticMemoryCreate(entity=entity, fact=fact, source=source))
        console.print(f"[green]Added fact for entity '{entity}'[/green]")


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(5, "--limit", "-l", help="Max results"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Search semantic memory."""
    db = get_db()
    gate = create_retrieval_gate(db)
    results = gate.search(query, limit=limit)

    if json_output:
        console.print_json(json.dumps(results))
    else:
        table = Table(title=f"Search: '{query}'")
        table.add_column("Entity", style="cyan")
        table.add_column("Fact", style="white")
        table.add_column("Score", justify="right", style="dim")
        for r in results:
            table.add_row(r["entity"], r["fact"], f"{r.get('score', 0):.3f}")
        console.print(table)


@app.command()
def context(
    query: str = typer.Argument(..., help="Query for context building"),
    include_recent: bool = typer.Option(True, "--recent/--no-recent", help="Include recent facts"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Build context block for LLM prompt injection."""
    db = get_db()
    gate = create_retrieval_gate(db)
    ctx = gate.build_context(query, include_recent=include_recent)

    if json_output:
        console.print_json(json.dumps({"query": query, "context": ctx} if ctx else {"query": query, "context": None}))
    else:
        if ctx:
            console.print(ctx)
        else:
            console.print("[yellow]No context found[/yellow]")


@app.command("list")
def list_facts(
    entity: Optional[str] = typer.Argument(None, help="Filter by entity (optional)"),
    all_facts: bool = typer.Option(False, "--all", "-a", help="Include superseded facts"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List semantic facts."""
    db = get_db()
    with db.session() as session:
        repo = create_repository(session)
        if entity:
            facts = repo.get_valid_facts_by_entity(entity) if not all_facts else repo.get_all_facts_by_entity(entity)
        else:
            facts = repo.get_all_valid_facts() if not all_facts else repo.get_all_facts()

    if json_output:
        console.print_json(json.dumps([{"id": f.id, "entity": f.entity, "fact": f.fact, "source": f.source, "valid_from": str(f.valid_from), "valid_to": str(f.valid_to) if f.valid_to else None} for f in facts]))
    else:
        table = Table(title=f"Facts{' for ' + entity if entity else ''}")
        table.add_column("ID", justify="right", style="dim")
        table.add_column("Entity", style="cyan")
        table.add_column("Fact", style="white")
        table.add_column("Source", style="dim")
        table.add_column("Valid To", style="yellow")
        for f in facts:
            table.add_row(str(f.id), f.entity, f.fact, f.source, str(f.valid_to) if f.valid_to else "∞")
        console.print(table)


@app.command()
def delete(
    fact_id: int = typer.Argument(..., help="Fact ID to delete"),
):
    """Delete a fact by ID."""
    db = get_db()
    with db.session() as session:
        repo = create_repository(session)
        repo.delete_fact(fact_id)
        console.print(f"[green]Deleted fact {fact_id}[/green]")


@app.command()
def supersede(
    entity: str = typer.Argument(..., help="Entity name"),
    fact: str = typer.Argument(..., help="New fact"),
    source: str = typer.Option("cli", "--source", help="Source of the new fact"),
):
    """Supersede the latest fact for an entity."""
    db = get_db()
    with db.session() as session:
        repo = create_repository(session)
        repo.supersede_fact(entity, SemanticMemoryUpdate(fact=fact, source=source))
        console.print(f"[green]Superseded fact for entity '{entity}'[/green]")


@app.command()
def log(
    session_id: str = typer.Argument(..., help="Session ID"),
    role: str = typer.Argument(..., help="Role: user or assistant"),
    content: str = typer.Argument(..., help="Message content"),
):
    """Add an episodic log entry."""
    db = get_db()
    with db.session() as session:
        repo = create_episodic_repository(session)
        repo.add_log(session_id, role, content)
        console.print(f"[green]Logged {role} message for session '{session_id}'[/green]")


@app.command("log-list")
def log_list(
    session_id: Optional[str] = typer.Argument(None, help="Session ID (optional, lists all sessions if omitted)"),
    limit: int = typer.Option(50, "--limit", "-l", help="Max results"),
):
    """List episodic logs."""
    db = get_db()
    with db.session() as session:
        repo = create_episodic_repository(session)
        if session_id:
            logs = repo.get_recent(session_id, limit=limit)
            title = f"Logs for session '{session_id}'"
        else:
            logs = repo.get_all_recent(limit=limit)
            title = "All Recent Logs"

        table = Table(title=title)
        table.add_column("ID", justify="right", style="dim")
        table.add_column("Session", style="cyan")
        table.add_column("Role", style="magenta")
        table.add_column("Content", style="white")
        table.add_column("Timestamp", style="dim")
        for log in logs:
            table.add_row(str(log.id), log.session_id, log.role, log.content[:80] + ("..." if len(log.content) > 80 else ""), str(log.created_at))
        console.print(table)


@app.command()
def consolidate(
    session_id: Optional[str] = typer.Option(None, "--session", "-s", help="Session ID (defaults to latest)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Run consolidation once for a session."""
    import asyncio

    db = get_db()
    maintenance = MemoryMaintenance(db, get_settings())

    async def run():
        return await maintenance.consolidate_once(session_id=session_id)

    result: ConsolidationResult = asyncio.run(run())

    if json_output:
        console.print_json(json.dumps({
            "facts_extracted": result.facts_extracted,
            "facts_upserted": result.facts_upserted,
            "facts_superseded": result.facts_superseded,
            "errors": result.errors,
            "duration_ms": result.duration_ms,
        }))
    else:
        console.print(f"[green]Consolidation complete[/green]")
        console.print(f"  Extracted: {result.facts_extracted}")
        console.print(f"  Upserted:  {result.facts_upserted}")
        console.print(f"  Superseded: {result.facts_superseded}")
        if result.errors:
            console.print(f"  Errors: {len(result.errors)}")
            for e in result.errors:
                console.print(f"    - {e}")


@app.command("worker-start")
def worker_start(
    background: bool = typer.Option(False, "--background", "-b", help="Run in background (not implemented)"),
):
    """Start the background consolidation worker."""
    import asyncio

    db = get_db()
    maintenance = MemoryMaintenance(db, get_settings())

    async def run():
        worker = await maintenance.start_worker()
        settings = get_settings()
        console.print(f"[green]Worker started[/green] (interval: {settings.dream_interval_minutes} min)")
        try:
            while worker.is_running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping worker...[/yellow]")
            await maintenance.stop_worker()
            console.print("[green]Worker stopped[/green]")

    asyncio.run(run())


@app.command("worker-status")
def worker_status(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Show worker statistics."""
    db = get_db()
    maintenance = MemoryMaintenance(db, get_settings())
    stats = maintenance.get_worker_stats()

    if stats is None:
        console.print("[yellow]Worker not running[/yellow]")
        return

    if json_output:
        console.print_json(json.dumps({
            "total_runs": stats.total_runs,
            "total_facts_extracted": stats.total_facts_extracted,
            "total_facts_upserted": stats.total_facts_upserted,
            "total_facts_superseded": stats.total_facts_superseded,
            "total_errors": stats.total_errors,
            "last_run_duration_ms": stats.last_run_duration_ms,
            "last_run_session": stats.last_run_session,
            "last_error": stats.last_error,
        }))
    else:
        table = Table(title="Worker Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        table.add_row("Total Runs", str(stats.total_runs))
        table.add_row("Facts Extracted", str(stats.total_facts_extracted))
        table.add_row("Facts Upserted", str(stats.total_facts_upserted))
        table.add_row("Facts Superseded", str(stats.total_facts_superseded))
        table.add_row("Total Errors", str(stats.total_errors))
        table.add_row("Last Run Duration (ms)", str(stats.last_run_duration_ms))
        table.add_row("Last Session", stats.last_run_session or "N/A")
        table.add_row("Last Error", stats.last_error or "None")
        console.print(table)


@app.command()
def stats(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Show database statistics."""
    db = get_db()
    with db.session() as session:
        from memory import create_repository
        from memory.episodic import create_episodic_repository

        repo = create_repository(session)
        episodic_repo = create_episodic_repository(session)

        valid_facts = repo.get_all_valid_facts()
        all_facts = repo.get_all_facts()
        session_ids = episodic_repo.get_session_ids(limit=1000)
        total_logs = sum(episodic_repo.count_by_session(sid) for sid in session_ids)

    if json_output:
        console.print_json(json.dumps({
            "valid_facts": len(valid_facts),
            "total_facts": len(all_facts),
            "superseded_facts": len(all_facts) - len(valid_facts),
            "sessions": len(session_ids),
            "total_logs": total_logs,
        }))
    else:
        table = Table(title="Database Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        table.add_row("Valid Facts", str(len(valid_facts)))
        table.add_row("Total Facts (incl. superseded)", str(len(all_facts)))
        table.add_row("Superseded Facts", str(len(all_facts) - len(valid_facts)))
        table.add_row("Sessions", str(len(session_ids)))
        table.add_row("Total Episodic Logs", str(total_logs))
        console.print(table)


if __name__ == "__main__":
    app()