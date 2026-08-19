from memory import (
    Database,
    RetrievalGate,
    SemanticMemoryCreate,
    SemanticMemoryUpdate,
    create_database,
    create_retrieval_gate,
    get_settings,
)


def main():
    settings = get_settings()
    db = create_database(settings)

    with db.session() as session:
        from memory import create_repository
        repo = create_repository(session)

        repo.add_fact(SemanticMemoryCreate(entity="user", fact="User prefers dark mode", source="preferences"))
        repo.add_fact(SemanticMemoryCreate(entity="user", fact="User works as a software engineer", source="profile"))
        repo.add_fact(SemanticMemoryCreate(entity="project", fact="Project uses Python 3.11", source="config"))
        repo.add_fact(SemanticMemoryCreate(entity="project", fact="Project uses SQLAlchemy 2.0", source="config"))

        print("=== Initial facts ===")
        for fact in repo.get_all_valid_facts():
            print(f"  [{fact.entity}] {fact.fact}")

        repo.supersede_fact("user", SemanticMemoryUpdate(fact="User prefers light mode", source="preferences_updated"))

        print("\n=== After supersede (user preferences) ===")
        for fact in repo.get_valid_facts_by_entity("user"):
            print(f"  [{fact.entity}] {fact.fact} (valid_to: {fact.valid_to})")

    print("\n=== Retrieval Gate: keyword search ===")
    gate = create_retrieval_gate(db)
    context = gate.build_context("user prefers")
    print(context or "No results")

    print("\n=== Retrieval Gate: search for project ===")
    context = gate.build_context("Python")
    print(context or "No results")

    print("\n=== Retrieval Gate: search API ===")
    results = gate.search("Python", limit=3)
    for r in results:
        print(f"  [{r['entity']}] {r['fact']}")


if __name__ == "__main__":
    main()