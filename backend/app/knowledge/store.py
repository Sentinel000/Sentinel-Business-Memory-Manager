"""HydraDB knowledge store.

One HydraDB *database* per company — the tenant boundary, which the vendor states is
absolute ("no cross-database aggregation, ever"). Within it, a single collection:
collections are retrieval-isolating, so splitting meetings from SOPs would fragment
the context graph and force us to merge incomparable relevance scores by hand.
Sources are distinguished by the document's own type and metadata instead.

The store is a narrow seam on purpose. Everything above it speaks in facts and
recalls, so swapping the backend (the README keeps pgvector as a latency fallback)
does not reach into the agent layer.
"""

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache
from typing import Any, Literal, Protocol

from app.config import settings

logger = logging.getLogger(__name__)

#: A single collection per database. See the module docstring for why.
KNOWLEDGE_COLLECTION = "knowledge"

FactType = Literal["decision", "fact", "context"]

#: Filterable metadata. Fields must be declared with ``enable_match`` *before*
#: ingestion — an undeclared field does not error, the filter is silently ignored,
#: which would return unscoped results that look scoped. Adding fields later is
#: possible but is not known to apply retroactively.
#:
#: ``fact_key`` is deliberately absent: the app_knowledge ``id`` is the upsert key,
#: so deduplication is handled by the API rather than by a filter of ours.
#:
#: ``source_type`` is also absent — it is a reserved built-in chunk field and the API
#: rejects it as a custom property (verified: INVALID_INPUT on database creation). The
#: source category travels on the item's ``type`` instead and comes back on the chunk.
METADATA_SCHEMA: list[dict[str, Any]] = [
    {"name": "subject", "data_type": "VARCHAR", "max_length": 128, "enable_match": True},
    {"name": "fact_type", "data_type": "VARCHAR", "max_length": 32, "enable_match": True},
    {"name": "speaker", "data_type": "VARCHAR", "max_length": 200, "enable_match": True},
    {"name": "source_ref", "data_type": "VARCHAR", "max_length": 128, "enable_match": True},
]


@dataclass
class RecalledFact:
    """One fact returned from recall, shaped for a tool response.

    Carries its provenance so the agent can cite rather than assert — Rule 6 applied
    to knowledge.
    """

    statement: str
    source_quote: str | None = None
    speaker: str | None = None
    subject: str | None = None
    fact_type: str | None = None
    source_ref: str | None = None
    source_type: str | None = None
    occurred_at: str | None = None
    score: float | None = None

    def to_summary(self) -> dict[str, Any]:
        """Summary shape. Rule 4: tools return summaries, not fat payloads."""
        return {
            k: v
            for k, v in {
                "statement": self.statement,
                "said_by": self.speaker,
                "quote": self.source_quote,
                "subject": self.subject,
                "type": self.fact_type,
                "occurred_at": self.occurred_at,
                "source_ref": self.source_ref,
            }.items()
            if v
        }


@dataclass
class IngestResult:
    ok: bool
    fact_id: str
    error: str | None = None


#: Predicates that describe how a fact reached us rather than what the company knows.
#:
#: ``build_statement_text`` appends "(speaker, meeting title)" so a chunk read cold
#: still carries its attribution. The graph builder reads that parenthetical as
#: authorship, so every meeting becomes a document node with a spoke per speaker.
#: Verified on live data: these were 4 of 10 edges. They are real relations, but they
#: describe provenance, so they are flagged here and hidden by default in the UI
#: rather than dropped — the distinction is presentational, not factual.
PROVENANCE_PREDICATES = frozenset({"authored", "author_of", "wrote"})


@dataclass
class GraphNode:
    """One entity in the knowledge graph."""

    id: str
    name: str
    #: Lower-cased. The API returns UPPERCASE (PERSON, ORGANIZATION, CONCEPT,
    #: DOCUMENT) despite the SDK documenting lowercase, so it is normalised once
    #: here instead of at every call site that wants to colour by type.
    type: str
    #: Source app the evidence came from ("slack", "google"); empty for plain ingest.
    provider: str | None = None


@dataclass
class GraphEvidence:
    """Why the graph believes an edge exists."""

    predicate: str
    context: str | None = None
    timestamp: str | None = None
    chunk_id: str | None = None


@dataclass
class GraphEdge:
    """A relation, with every evidence entry that supports it collapsed into one.

    The API returns a triplet group per evidencing chunk, so the same pair can arrive
    several times. Drawing each separately produces overlapping duplicate lines that
    read as a denser graph than the data supports.

    ``confidence`` is deliberately absent. Every edge on live data scored exactly
    0.80 — it is a placeholder, and encoding a constant as line weight would render a
    signal that does not exist.
    """

    id: str
    source: str
    target: str
    predicate: str
    evidence: list[GraphEvidence]
    is_provenance: bool = False


@dataclass
class KnowledgeGraph:
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    #: The API caps results. A partial force layout is indistinguishable from a
    #: complete one, so this has to reach the UI.
    truncated: bool = False


class KnowledgeStore(Protocol):
    """What the agent layer is allowed to assume about knowledge memory."""

    def provision(self, database: str) -> bool: ...

    def ingest_fact(
        self,
        *,
        database: str,
        statement: str,
        source_quote: str,
        speaker: str,
        subject: str,
        fact_type: FactType,
        source_ref: str,
        source_type: str = "transcript",
        occurred_at: datetime | date | None = None,
        meeting_title: str | None = None,
        confidence: float | None = None,
    ) -> IngestResult: ...

    def forget_source(self, *, database: str, source_ref: str) -> int: ...

    def recall(
        self,
        *,
        database: str,
        query: str,
        subject: str | None = None,
        fact_type: str | None = None,
        as_of: str | None = None,
        limit: int = 6,
    ) -> list[RecalledFact]: ...

    def graph_relations(
        self, *, database: str, source_ref: str | None = None, limit: int = 150
    ) -> KnowledgeGraph: ...


def build_fact_id(source_ref: str, statement: str) -> str:
    """Deterministic id, so re-running extraction upserts instead of duplicating.

    The API treats the app_knowledge ``id`` as the upsert key, which is what makes
    Rule 3 (idempotent writes) hold without a dedup query of our own. Commas are not
    permitted in ids, hence the hex digest.
    """
    digest = hashlib.sha256(f"{source_ref}::{statement.strip()}".encode()).hexdigest()
    return f"fact_{digest[:32]}"


def build_statement_text(
    statement: str,
    *,
    speaker: str,
    occurred_at: datetime | date | None,
    meeting_title: str | None,
) -> str:
    """Render a fact as a self-contained, date-prefixed sentence.

    The date belongs in the indexed text, not only in metadata: metadata cannot be
    range-filtered, so a model reasoning over "what did we decide in March" reads the
    date off the retrieved chunk. A bare value ("$49") retrieves badly and reasons
    worse.
    """
    parts: list[str] = []
    if occurred_at is not None:
        stamp = occurred_at.date() if isinstance(occurred_at, datetime) else occurred_at
        parts.append(f"{stamp.isoformat()} — ")

    parts.append(statement.strip())

    attribution = ", ".join(p for p in (speaker, meeting_title) if p)
    if attribution:
        parts.append(f" ({attribution})")

    return "".join(parts)


class HydraKnowledgeStore:
    """HydraDB-backed implementation.

    Every method is failure-tolerant by design. Knowledge recall is an enrichment on
    top of Postgres truth, so an outage must degrade the answer, never break the
    request.
    """

    def __init__(self, token: str, timeout: float = 30.0) -> None:
        from hydra_db import HydraDB

        self._client = HydraDB(token=token, timeout=timeout)

    # ---------------------------------------------------------------- provisioning

    def provision(self, database: str) -> bool:
        """Create the company's database and declare its filterable fields.

        Idempotent: an existing database is treated as success, since provisioning
        runs on onboarding and again lazily on first write.
        """
        try:
            self._client.databases.create(
                database=database,
                database_metadata_schema=METADATA_SCHEMA,  # type: ignore[arg-type]
            )
            logger.info("Provisioned HydraDB database %s", database)
            return True
        except Exception as exc:
            if _is_already_exists(exc):
                logger.debug("HydraDB database %s already exists", database)
                return True
            logger.warning("HydraDB provisioning failed for %s: %s", database, exc)
            return False

    def is_ready(self, database: str) -> bool:
        """Whether the database has finished provisioning and accepts writes."""
        try:
            infra = self._client.databases.status(database=database).data.infra
            return bool(getattr(infra, "ready_for_ingestion", False))
        except Exception as exc:
            logger.warning("HydraDB status check failed for %s: %s", database, exc)
            return False

    # --------------------------------------------------------------------- writing

    def ingest_fact(
        self,
        *,
        database: str,
        statement: str,
        source_quote: str,
        speaker: str,
        subject: str,
        fact_type: FactType,
        source_ref: str,
        source_type: str = "transcript",
        occurred_at: datetime | date | None = None,
        meeting_title: str | None = None,
        confidence: float | None = None,
    ) -> IngestResult:
        text = build_statement_text(
            statement, speaker=speaker, occurred_at=occurred_at, meeting_title=meeting_title
        )
        fact_id = build_fact_id(source_ref, statement)

        # Uploaded as a document rather than via app_knowledge. Verified against the
        # live API: app_knowledge stores the serialized item as the chunk body, so
        # recall hands the agent raw JSON. The document path indexes the prose itself.
        document_metadata = [
            {
                "id": fact_id,
                "metadata": {
                    "subject": subject,
                    "fact_type": fact_type,
                    "speaker": speaker,
                    "source_ref": source_ref,
                },
                # Free-form: returned with the chunk for citation, never filterable.
                "additional_metadata": _compact(
                    {
                        "source_quote": source_quote[:400],
                        "occurred_at": _iso(occurred_at),
                        "meeting_title": meeting_title,
                        # "source_type" is reserved by the API in additional_metadata
                        # as well as in the schema, so the source category is carried
                        # under our own name.
                        "origin": source_type,
                        "confidence": confidence,
                    }
                ),
            }
        ]

        try:
            self._client.context.ingest(
                database=database,
                collection=KNOWLEDGE_COLLECTION,
                type="knowledge",
                documents=(f"{fact_id}.txt", text.encode("utf-8"), "text/plain"),
                document_metadata=json.dumps(document_metadata),
                # Re-running extraction on the same meeting overwrites rather than
                # duplicating: the id is the upsert key. Rule 3.
                upsert="true",
            )
            return IngestResult(ok=True, fact_id=fact_id)
        except Exception as exc:
            logger.warning("HydraDB ingest failed for %s: %s", database, exc)
            return IngestResult(ok=False, fact_id=fact_id, error=str(exc))

    def indexing_state(self, database: str, fact_ids: list[str]) -> dict[str, str]:
        """Per-source indexing status.

        ``collection`` is required here. Omitting it does not fall through to a
        default — the lookup reports FILE_NOT_FOUND for sources that exist and are
        indexing normally, which reads as a failed ingest when it is nothing of the
        kind.
        """
        try:
            statuses = self._client.context.status(
                database=database, ids=fact_ids, collection=KNOWLEDGE_COLLECTION
            ).data.statuses
            return {s.id: (s.indexing_status or "unknown") for s in statuses}
        except Exception as exc:
            logger.warning("HydraDB status lookup failed for %s: %s", database, exc)
            return {}

    # -------------------------------------------------------------------- deleting

    def source_fact_ids(self, *, database: str, source_ref: str) -> list[str]:
        """Every fact id ingested from one source, across all pages.

        Read-only, so it is safe to call to preview what a delete would remove.
        Raises rather than degrading: a partial list here becomes a partial delete,
        which leaves orphan facts still answering chat questions.
        """
        ids: list[str] = []
        page = 1
        while True:
            try:
                data = self._client.context.list(
                    database=database,
                    collection=KNOWLEDGE_COLLECTION,
                    type="knowledge",
                    filters={"metadata": {"source_ref": source_ref}},  # type: ignore[arg-type]
                    page=page,
                    page_size=100,
                ).data
            except Exception as exc:
                raise KnowledgeUnavailable(
                    f"Could not list facts for {source_ref!r}: {exc}"
                ) from exc

            sources = getattr(data, "sources", None) or []
            ids.extend(str(src.id) for src in sources if getattr(src, "id", None))
            # Stop on a short page rather than trusting a total we did not verify.
            if len(sources) < 100:
                return ids
            page += 1

    def forget_source(self, *, database: str, source_ref: str) -> int:
        """Delete every fact ingested from one source. Returns how many.

        Unlike the rest of this class, this **raises on failure instead of
        degrading**. Recall is enrichment over Postgres truth, so a failed read can
        safely return nothing; a failed delete cannot, because the caller is about
        to remove the Postgres row. Silently swallowing it leaves the meeting gone
        while its facts keep answering "what did we decide about pricing".
        """
        ids = self.source_fact_ids(database=database, source_ref=source_ref)
        if not ids:
            return 0

        try:
            data = self._client.context.delete(
                database=database,
                collection=KNOWLEDGE_COLLECTION,
                type="knowledge",
                ids=ids,
            ).data
        except Exception as exc:
            raise KnowledgeUnavailable(
                f"Could not delete {len(ids)} facts for {source_ref!r}: {exc}"
            ) from exc

        # Verified against the live API: a refused delete still returns HTTP 200 with
        # a success envelope. The refusal is in the payload — `deleted_count: 0`,
        # `success: false`, and a per-id reason. Trusting the absence of an exception
        # reports facts as deleted that are all still there, which is the precise
        # failure this method exists to prevent.
        failures = [
            (r.id, r.error or "unknown")
            for r in (getattr(data, "results", None) or [])
            if not getattr(r, "deleted", False)
        ]
        deleted = int(getattr(data, "deleted_count", 0) or 0)

        if failures:
            reason = failures[0][1]
            # The common one: a fact still in `graph_creation` cannot be deleted yet.
            # Surfaced verbatim so the caller can tell the founder to retry rather
            # than reporting a delete that did not happen.
            raise KnowledgeUnavailable(
                f"{len(failures)} of {len(ids)} facts for {source_ref!r} could not be "
                f"deleted: {reason}"
            )

        logger.info("Deleted %d facts for source %s from %s", deleted, source_ref, database)
        return deleted

    # --------------------------------------------------------------------- reading

    def recall(
        self,
        *,
        database: str,
        query: str,
        subject: str | None = None,
        fact_type: str | None = None,
        as_of: str | None = None,
        limit: int = 6,
    ) -> list[RecalledFact]:
        filters = _compact({"subject": subject, "fact_type": fact_type})

        kwargs: dict[str, Any] = {
            "database": database,
            "collection": KNOWLEDGE_COLLECTION,
            "type": "knowledge",
            "query": query,
            "max_results": limit,
            # The engine resolves superseded facts itself; this is what makes a
            # Postgres fact ledger unnecessary.
            "temporal_reasoning": True,
        }
        if filters:
            kwargs["metadata_filters"] = filters
        if as_of:
            # Evaluate the query as of a point in time rather than now.
            kwargs["temporal_now"] = as_of

        try:
            result = self._client.query(**kwargs)
        except Exception as exc:
            logger.warning("HydraDB recall failed for %s: %s", database, exc)
            raise KnowledgeUnavailable(str(exc)) from exc

        return _parse_chunks(result)


    def corpus_size(self, database: str) -> int | None:
        """How many facts are ingested, independent of the graph.

        Distinguishes "nothing recorded" from "recorded, graph still building" —
        which look identical from the relations endpoint alone. Degrades to None,
        since it only enriches a message.
        """
        try:
            stats = self._client.databases.stats(database=database).data
            collection = getattr(stats, "knowledge_collection", None)
            count = getattr(collection, "row_count", None)
            return int(count) if count is not None else None
        except Exception as exc:
            logger.warning("HydraDB stats failed for %s: %s", database, exc)
            return None

    def graph_relations(
        self, *, database: str, source_ref: str | None = None, limit: int = 150
    ) -> KnowledgeGraph:
        """The company's knowledge graph: entities and the relations between them.

        Omitting ``source_ref`` returns the whole database. Passing one scopes to a
        single ingested fact — note that is a ``fact_<sha>`` id, not a meeting id,
        because that is the unit we ingest.

        Raises rather than returning an empty graph. An empty graph is a legitimate
        answer ("nothing recorded yet") and the panel renders it as such, so a
        failure that degraded to empty would be indistinguishable from real emptiness.
        """
        try:
            data = self._client.context.relations(
                database=database,
                collection=KNOWLEDGE_COLLECTION,
                type="knowledge",
                id=source_ref,
                limit=limit,
            ).data
        except Exception as exc:
            logger.warning("HydraDB relations failed for %s: %s", database, exc)
            raise KnowledgeUnavailable(str(exc)) from exc

        return _parse_graph(data)


class KnowledgeUnavailable(RuntimeError):
    """Recall could not be served. Callers degrade; they do not fail the request."""


# ------------------------------------------------------------------------ helpers


def _compact(data: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in data.items() if v not in (None, "")}


def _iso(value: datetime | date | None) -> str | None:
    return value.isoformat() if value is not None else None


def _is_already_exists(exc: Exception) -> bool:
    text = str(exc).lower()
    return "already exists" in text or "conflict" in text or "409" in text


def _parse_chunks(result: Any) -> list[RecalledFact]:
    """Flatten a retrieval result into facts, tolerating shape drift.

    The response envelope is vendor-controlled and the docs mix v1 and v2 shapes, so
    every field is read defensively rather than assumed.
    """
    chunks = getattr(getattr(result, "data", None), "chunks", None) or []
    facts: list[RecalledFact] = []

    for chunk in chunks:
        meta = _as_dict(getattr(chunk, "metadata", None))
        extra = _as_dict(getattr(chunk, "additional_metadata", None))
        content = getattr(chunk, "chunk_content", None)
        if not content:
            continue

        facts.append(
            RecalledFact(
                statement=str(content).strip(),
                source_quote=extra.get("source_quote"),
                speaker=meta.get("speaker"),
                subject=meta.get("subject"),
                fact_type=meta.get("fact_type"),
                source_ref=meta.get("source_ref"),
                source_type=extra.get("origin") or getattr(chunk, "source_type", None),
                occurred_at=extra.get("occurred_at"),
                score=getattr(chunk, "relevancy_score", None),
            )
        )

    return facts


def _parse_graph(data: Any) -> KnowledgeGraph:
    """Flatten triplet groups into deduplicated nodes and edges.

    Read defensively for the same reason as ``_parse_chunks``: the envelope is
    vendor-controlled. An entity with no id is skipped rather than synthesised — a
    node the graph cannot address is a node nothing can link to.
    """
    nodes: dict[str, GraphNode] = {}
    edges: dict[str, GraphEdge] = {}

    for triplet in getattr(data, "relations", None) or []:
        source = _parse_entity(getattr(triplet, "source", None))
        target = _parse_entity(getattr(triplet, "target", None))
        if source is None or target is None:
            continue

        nodes.setdefault(source.id, source)
        nodes.setdefault(target.id, target)

        for ev in getattr(triplet, "relations", None) or []:
            predicate = (
                getattr(ev, "canonical_predicate", None)
                or getattr(ev, "raw_predicate", None)
                or "related to"
            ).strip()

            # One edge per (pair, predicate). The same pair legitimately carries
            # several predicates; the same predicate arriving twice is one relation
            # evidenced twice.
            key = f"{source.id}|{target.id}|{predicate}"
            edge = edges.get(key)
            if edge is None:
                edge = GraphEdge(
                    id=key,
                    source=source.id,
                    target=target.id,
                    predicate=predicate,
                    evidence=[],
                    is_provenance=predicate.lower().replace(" ", "_")
                    in PROVENANCE_PREDICATES,
                )
                edges[key] = edge

            context = (getattr(ev, "context", None) or "").strip()
            edge.evidence.append(
                GraphEvidence(
                    predicate=predicate,
                    context=context or None,
                    timestamp=getattr(ev, "timestamp", None),
                    chunk_id=getattr(ev, "chunk_id", None)
                    or getattr(triplet, "chunk_id", None),
                )
            )

    return KnowledgeGraph(
        nodes=list(nodes.values()),
        edges=list(edges.values()),
        truncated=bool(getattr(data, "is_truncated", False)),
    )


def _parse_entity(entity: Any) -> GraphNode | None:
    if entity is None:
        return None
    entity_id = getattr(entity, "entity_id", None)
    if not entity_id:
        return None

    provider = (getattr(entity, "provider", None) or "").strip()
    return GraphNode(
        id=str(entity_id),
        name=(getattr(entity, "name", None) or "unnamed").strip(),
        # UPPERCASE on the wire despite the SDK documenting lowercase.
        type=(getattr(entity, "type", None) or "unknown").strip().lower(),
        provider=provider or None,
    )


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump()
        except Exception:
            return {}
    return {}


@lru_cache
def get_knowledge_store() -> HydraKnowledgeStore | None:
    """The process-wide store, or None when HydraDB is not configured.

    Returning None rather than raising is deliberate: the whole system runs without
    knowledge memory, just with thinner answers. Tools check for None and say so.
    """
    token = (settings.hydra_db_api_key or "").strip()
    if not token:
        logger.info("HYDRA_DB_API_KEY not set — knowledge memory disabled.")
        return None
    try:
        return HydraKnowledgeStore(token=token, timeout=settings.hydra_timeout_seconds)
    except Exception as exc:
        logger.warning("HydraDB client could not be constructed: %s", exc)
        return None
