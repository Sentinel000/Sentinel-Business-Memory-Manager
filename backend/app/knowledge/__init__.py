"""Knowledge memory layer — HydraDB.

Settled context lives here: decisions, rationale, SOPs. Operational state (tasks,
status, owners) stays in Postgres. The test for where something belongs is whether
it expires. See docs/features/hydradb-knowledge-layer/plan.md.
"""

from app.knowledge.store import (
    KNOWLEDGE_COLLECTION,
    METADATA_SCHEMA,
    FactType,
    GraphEdge,
    GraphEvidence,
    GraphNode,
    KnowledgeGraph,
    KnowledgeStore,
    KnowledgeUnavailable,
    RecalledFact,
    get_knowledge_store,
)

__all__ = [
    "KNOWLEDGE_COLLECTION",
    "METADATA_SCHEMA",
    "FactType",
    "GraphEdge",
    "GraphEvidence",
    "GraphNode",
    "KnowledgeGraph",
    "KnowledgeStore",
    "KnowledgeUnavailable",
    "RecalledFact",
    "get_knowledge_store",
]
