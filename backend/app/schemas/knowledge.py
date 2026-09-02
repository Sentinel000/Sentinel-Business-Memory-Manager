"""Knowledge graph read models."""

from pydantic import BaseModel, Field


class GraphEvidenceRead(BaseModel):
    """Why the graph believes a relation exists — the founder's audit trail."""

    predicate: str
    context: str | None = None
    timestamp: str | None = None
    chunk_id: str | None = None


class GraphNodeRead(BaseModel):
    id: str
    name: str
    #: Lower-cased by the store: person, organization, concept, document, knowledge.
    type: str
    provider: str | None = None


class GraphEdgeRead(BaseModel):
    id: str
    source: str
    target: str
    predicate: str
    evidence: list[GraphEvidenceRead] = Field(default_factory=list)
    #: An "authored"-style relation describing how a fact reached us rather than
    #: what the company knows. Hidden by default in the panel.
    is_provenance: bool = False


class KnowledgeGraphRead(BaseModel):
    """The graph, or an explanation of why there isn't one.

    ``available`` is false when knowledge memory is unconfigured or unreachable.
    That is distinct from an empty graph, which is a real answer — a company that
    has not recorded anything yet. Collapsing the two would tell a founder nothing
    was decided when in fact nothing was searched.
    """

    available: bool = True
    note: str | None = None
    nodes: list[GraphNodeRead] = Field(default_factory=list)
    edges: list[GraphEdgeRead] = Field(default_factory=list)
    #: Result cap hit. A partial force layout looks exactly like a complete one.
    truncated: bool = False
    #: Facts ingested, from the corpus itself rather than the graph. A corpus with
    #: rows but no edges means indexing is still building the graph.
    fact_count: int | None = None
