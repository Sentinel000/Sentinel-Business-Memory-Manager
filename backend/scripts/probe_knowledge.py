"""Probe the HydraDB knowledge layer against a live account.

Not a test suite — a runnable inspection of what the graph actually contains, for
questions the app cannot answer from Postgres: did ingestion finish, what entities
and predicates were extracted, and is recall backed by real edges or nothing at all.

Read-only. Every call is a GET; nothing here creates, ingests, or deletes.

    python -m scripts.probe_knowledge                 # every sentinel_* database
    python -m scripts.probe_knowledge <database> ...  # only the ones named

Requires HYDRA_DB_API_KEY in the environment or backend/.env.
"""

import json
import sys
import typing

from app.config import settings
from app.knowledge.store import KNOWLEDGE_COLLECTION

#: How many graph edges and sources to pull per database. Kept small: this is a
#: shape probe, not an export, and the graph fans out fast.
SAMPLE = 10


def show(label: str, obj: typing.Any, limit: int = 4000) -> None:
    """Print a response body, truncated. Envelopes are unwrapped by the caller."""
    print(f"\n--- {label} ".ljust(72, "-"))
    if obj is None:
        print("(no data)")
        return
    payload = obj.model_dump() if hasattr(obj, "model_dump") else obj
    text = json.dumps(payload, indent=2, default=str)
    print(text[:limit] + ("\n… truncated" if len(text) > limit else ""))


def attempt(label: str, fn: typing.Callable[[], typing.Any]) -> typing.Any:
    """Run one probe. A failure is a finding, not a reason to stop the script."""
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 - reporting, not handling
        print(f"\n--- {label} ".ljust(72, "-"))
        print(f"FAILED  {type(exc).__name__}: {str(exc)[:600]}")
        return None


def summarize_relations(data: typing.Any) -> None:
    """The point of the whole script: what the graph builder actually derived.

    The raw envelope is verbose and mostly ids. What matters is which entities it
    found, and whether `raw_predicate` collapsed into a sensible
    `canonical_predicate` — a normalizer that flattens distinct relations into one
    is a silent recall killer that no query-side metric will show you.
    """
    relations = getattr(data, "relations", None) or []
    if not relations:
        print("  no edges — graph empty, still building, or nothing ingested")
        return

    print(f"  {len(relations)} triplet group(s), truncated={getattr(data, 'is_truncated', None)}")
    for triplet in relations:
        src = getattr(triplet, "source", None)
        tgt = getattr(triplet, "target", None)
        src_name = getattr(src, "name", "?")
        src_type = getattr(src, "type", "?")
        tgt_name = getattr(tgt, "name", "?")
        tgt_type = getattr(tgt, "type", "?")

        for ev in getattr(triplet, "relations", None) or []:
            canonical = getattr(ev, "canonical_predicate", None) or "?"
            raw = getattr(ev, "raw_predicate", None)
            conf = getattr(ev, "confidence", None)
            drift = f"  (raw: {raw})" if raw and raw != canonical else ""
            score = f"  conf={conf:.2f}" if isinstance(conf, (int, float)) else ""
            print(f"    ({src_name}:{src_type}) -[{canonical}]-> ({tgt_name}:{tgt_type}){score}{drift}")

            context = (getattr(ev, "context", None) or "").strip()
            if context:
                print(f"        evidence: {context[:160]}")


def probe(client: typing.Any, database: str) -> None:
    print("\n" + "=" * 72)
    print(f"DATABASE  {database}")
    print("=" * 72)

    status = attempt("databases.status", lambda: client.databases.status(database=database).data)
    show("databases.status", status, limit=1500)

    stats = attempt("databases.stats", lambda: client.databases.stats(database=database).data)
    show("databases.stats", stats, limit=1500)

    schema = attempt(
        "databases.get_metadata_schema",
        lambda: client.databases.get_metadata_schema(database=database).data,
    )
    show("metadata schema (must match METADATA_SCHEMA)", schema, limit=2000)

    # What is actually in the corpus. Without this, an empty graph is ambiguous:
    # nothing ingested and ingestion-failed look identical.
    listing = attempt(
        "context.list",
        lambda: client.context.list(
            database=database, collection=KNOWLEDGE_COLLECTION, type="knowledge",
            page=1, page_size=SAMPLE,
        ).data,
    )
    sources = getattr(listing, "sources", None) or []
    ids = [str(s.id) for s in sources if getattr(s, "id", None)]
    print(f"\n--- context.list ".ljust(72, "-"))
    print(f"  {len(ids)} source(s) on page 1: {ids[:SAMPLE]}")

    # /ingestion/verify_processing — the poll-after-upload endpoint.
    # `collection` is required; omitting it reports FILE_NOT_FOUND for sources that
    # exist and are indexing normally.
    if ids:
        batch = attempt(
            "context.status",
            lambda: client.context.status(
                database=database, ids=ids, collection=KNOWLEDGE_COLLECTION
            ).data,
        )
        print(f"\n--- context.status  [/ingestion/verify_processing] ".ljust(72, "-"))
        for s in getattr(batch, "statuses", None) or []:
            err = getattr(s, "error_message", None) or ""
            # `success` on each row is a constant echo of the envelope and is true
            # even for a source that failed. indexing_status is the real state.
            print(f"  {getattr(s, 'id', '?')[:40]:42} {getattr(s, 'indexing_status', '?'):12} {err[:60]}")

    # /list/graph_relations_by_id — id omitted returns the whole database's graph.
    print(f"\n--- context.relations (database-wide)  [/list/graph_relations_by_id] ".ljust(72, "-"))
    graph = attempt(
        "context.relations",
        lambda: client.context.relations(
            database=database, collection=KNOWLEDGE_COLLECTION, type="knowledge",
            limit=SAMPLE,
        ).data,
    )
    if graph is not None:
        summarize_relations(graph)

    # Then scoped to one source, which is the per-fact debugging view.
    if ids:
        print(f"\n--- context.relations (id={ids[0]}) ".ljust(72, "-"))
        scoped = attempt(
            "context.relations by id",
            lambda: client.context.relations(
                database=database, collection=KNOWLEDGE_COLLECTION, type="knowledge",
                id=ids[0], limit=SAMPLE,
            ).data,
        )
        if scoped is not None:
            summarize_relations(scoped)


def main() -> int:
    token = (settings.hydra_db_api_key or "").strip()
    if not token:
        print("HYDRA_DB_API_KEY is not set (environment or backend/.env).")
        return 1

    from hydra_db import HydraDB

    client = HydraDB(token=token, timeout=settings.hydra_timeout_seconds)

    databases = sys.argv[1:]
    if not databases:
        listing = attempt("databases.list", lambda: client.databases.list().data)
        if listing is None:
            return 1
        all_names = getattr(listing, "databases", None) or []
        print(f"account databases: {all_names}")
        # Only ours. The account also holds unrelated tenants.
        databases = [n for n in all_names if str(n).startswith("sentinel_")]

    if not databases:
        print("No sentinel_* databases found.")
        return 1

    for database in databases:
        probe(client, database)

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
