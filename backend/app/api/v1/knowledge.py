"""Knowledge graph — read-only view of what the company knows and how it connects.

Founder-only, matching the scoping of the chat read tool: employees live in Slack and
never open the dashboard.
"""

from fastapi import APIRouter, Query

from app.dependencies import CompanyId, CompanyRepo, FounderUser
from app.exceptions import NotFoundError
from app.knowledge.store import KnowledgeUnavailable, get_knowledge_store
from app.schemas.knowledge import (
    GraphEdgeRead,
    GraphEvidenceRead,
    GraphNodeRead,
    KnowledgeGraphRead,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

_NOT_CONFIGURED = (
    "Knowledge memory is not configured for this workspace, so there is no graph to "
    "show yet."
)
_UNREACHABLE = (
    "Knowledge memory could not be reached, so the graph could not be loaded. This is "
    "a connection problem, not an empty graph."
)


@router.get("/graph", response_model=KnowledgeGraphRead)
def get_knowledge_graph(
    repo: CompanyRepo,
    company_id: CompanyId,
    _: FounderUser,
    limit: int = Query(150, ge=1, le=500, description="Max relations to fetch."),
    source_ref: str | None = Query(
        None, description="Scope to one ingested fact id (fact_<sha>)."
    ),
) -> KnowledgeGraphRead:
    """Entities and relations extracted from everything the company has recorded.

    Never 500s on a knowledge outage. An unavailable graph and an empty graph are
    different answers and the panel renders them differently, so both come back as
    a 200 carrying the distinction.
    """
    company = repo.get(company_id)
    if company is None:
        raise NotFoundError("Company not found.")

    store = get_knowledge_store()
    if store is None or not company.hydra_tenant_id:
        return KnowledgeGraphRead(available=False, note=_NOT_CONFIGURED)

    database = company.hydra_tenant_id

    try:
        graph = store.graph_relations(
            database=database, source_ref=source_ref, limit=limit
        )
    except KnowledgeUnavailable:
        return KnowledgeGraphRead(available=False, note=_UNREACHABLE)

    return KnowledgeGraphRead(
        available=True,
        nodes=[
            GraphNodeRead(id=n.id, name=n.name, type=n.type, provider=n.provider)
            for n in graph.nodes
        ],
        edges=[
            GraphEdgeRead(
                id=e.id,
                source=e.source,
                target=e.target,
                predicate=e.predicate,
                is_provenance=e.is_provenance,
                evidence=[
                    GraphEvidenceRead(
                        predicate=ev.predicate,
                        context=ev.context,
                        timestamp=ev.timestamp,
                        chunk_id=ev.chunk_id,
                    )
                    for ev in e.evidence
                ],
            )
            for e in graph.edges
        ],
        truncated=graph.truncated,
        # Only worth a round trip when the graph is empty, to tell "nothing ingested"
        # apart from "ingested, still building".
        fact_count=store.corpus_size(database) if not graph.nodes else None,
    )
