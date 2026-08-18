from memory import Database, MemoryRepository, RetrievalGate


def main():
    db = Database("state.db")

    with db.session() as session:
        repo = MemoryRepository(session)

        repo.add_fact("user", "User prefers dark mode", source="preferences")
        repo.add_fact("user", "User works as a software engineer", source="profile")
        repo.add_fact("project", "Project uses Python 3.11", source="config")
        repo.add_fact("project", "Project uses SQLAlchemy 2.0", source="config")

        print("=== Initial facts ===")
        for fact in repo.get_all_valid_facts():
            print(f"  [{fact.entity}] {fact.fact}")

        repo.supersede_fact("user", "User prefers light mode", source="preferences_updated")

        print("\n=== After supersede (user preferences) ===")
        for fact in repo.get_valid_facts_by_entity("user"):
            print(f"  [{fact.entity}] {fact.fact} (valid_to: {fact.valid_to})")

    print("\n=== Retrieval Gate: keyword search ===")
    gate = RetrievalGate(db)
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