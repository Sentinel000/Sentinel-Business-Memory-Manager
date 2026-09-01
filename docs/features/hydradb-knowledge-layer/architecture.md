## Architecture: HydraDB Knowledge Layer

```mermaid
graph TD
    subgraph Sources["Human-authored sources"]
        TRANSCRIPT["Meeting transcript<br/>POST /api/v1/knowledge/transcripts"]
        FOUNDER["Founder<br/>POST /api/v1/chat"]
    end

    subgraph Factory["build_sentinel — factory._tools_for"]
        EXTRACTOR["entry = transcript<br/>Extractor agent"]
        CHAT["entry = chat, role = founder<br/>Chat agent (read-only)"]
    end

    subgraph Tools["Tool layer — audit-logged, summary returns"]
        CREATETASK["create_extracted_task<br/>EXISTING"]
        REMEMBER["remember_fact<br/>NEW — requires source_quote + speaker"]
        SEARCH["search_memory<br/>NEW"]
        QUERYTASKS["query_tasks<br/>EXISTING"]
    end

    subgraph Store["app/knowledge/store.py"]
        PROTO["KnowledgeStore protocol<br/>vendor-swappable seam"]
        HYDRACLIENT["HydraKnowledgeStore<br/>hydra_db.HydraDB"]
    end

    subgraph Persistence["Storage"]
        PG[("PostgreSQL<br/>tasks · employees · approvals · audit<br/>operational state — expires")]
        HYDRA[("HydraDB<br/>database = hydra_tenant_id<br/>one collection · context graph<br/>settled knowledge — superseded, not stale")]
    end

    TRANSCRIPT --> EXTRACTOR
    FOUNDER --> CHAT

    EXTRACTOR --> CREATETASK
    EXTRACTOR --> REMEMBER
    CHAT --> SEARCH
    CHAT --> QUERYTASKS

    CREATETASK -->|"status = pending_approval<br/>Rule 1"| PG
    QUERYTASKS -->|"exact WHERE — never fuzzy<br/>Rule 2"| PG

    REMEMBER --> PROTO
    SEARCH --> PROTO
    PROTO --> HYDRACLIENT

    HYDRACLIENT -->|"context.ingest — async<br/>poll indexing_status"| HYDRA
    HYDRACLIENT -->|"client.query<br/>metadata filter → semantic +<br/>keyword + graph → rerank"| HYDRA

    HYDRA -.->|"chunks + source_quote<br/>every answer cites its origin — Rule 6"| SEARCH
    HYDRA -.->|"unreachable → degrade,<br/>never 500"| PROTO

    ONBOARD["Company onboarding"] -->|"databases.create()<br/>+ match-enabled schema"| HYDRA
    ONBOARD -->|"persist hydra_tenant_id"| PG

    classDef new fill:#c1e1f7,stroke:#3398e1,color:#0c0a09
    classDef existing fill:#ffffff,stroke:#a8a29e,color:#0c0a09
    classDef store fill:#1c1917,stroke:#0c0a09,color:#ffffff
    class REMEMBER,SEARCH,PROTO,HYDRACLIENT new
    class CREATETASK,QUERYTASKS existing
    class PG,HYDRA store
```

### Write path

```mermaid
sequenceDiagram
    participant T as Transcript
    participant E as Extractor agent
    participant S as KnowledgeStore
    participant H as HydraDB
    participant P as PostgreSQL

    T->>E: raw transcript text
    E->>P: create_extracted_task(...) → pending_approval
    E->>S: remember_fact(statement, source_quote, speaker, subject, fact_type)
    Note over S: build date-prefixed statement<br/>derive fact_key = sha256(source_ref + statement)
    S->>H: context.ingest(type="knowledge", database, metadata)
    H-->>S: source id
    S->>H: context.status(ids=[id])
    Note over H: parse → chunk (sliding window,<br/>resolves pronouns) → embed →<br/>extract entities → link into graph
    H-->>S: indexing_status = completed
```

### Read path

```mermaid
sequenceDiagram
    participant F as Founder
    participant C as Chat agent
    participant S as KnowledgeStore
    participant H as HydraDB
    participant P as PostgreSQL

    F->>C: "what did we decide about pricing, and has it changed?"
    C->>S: search_memory(query, subject="pricing")
    S->>H: client.query(database, type="knowledge", metadata_filters)
    Note over H: exact-match metadata filter →<br/>semantic + keyword + graph expansion →<br/>rerank. Versioned temporal graph<br/>resolves what is currently true.
    H-->>S: chunks (date-prefixed statements + source_quote)
    S-->>C: summaries with citations
    Note over C: model reasons over dates in the<br/>returned text — no as-of query exists
    C->>P: query_tasks(...) for live state if needed
    C-->>F: answer citing meeting and verbatim quote
```

### Boundaries

| Concern | Owner | Rule |
|---|---|---|
| Task state, status, owners, approvals | PostgreSQL only | Rule 2 — never fuzzy retrieval |
| Decisions, facts, rationale, SOPs | HydraDB only | Does not expire; superseded, not stale |
| Which fact is currently true | HydraDB versioned temporal graph | Not rebuilt in Postgres |
| Tenant isolation | `database` per company | No cross-database aggregation |
| Source separation | `source_type` metadata | Never separate collections — fragments the graph |
| Provenance | `source_quote` + `speaker`, required at write | Rule 6 |
