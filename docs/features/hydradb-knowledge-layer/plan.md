# HydraDB Knowledge Layer — Plan

## Context

Sentinel's promise is **extract → approve → delegate → chase → collect → remember**. Every
step but the last is built. `companies.hydra_tenant_id` exists in the schema and initial
migration, and `knowledge_connected` is derived from it in the company API — but nothing
writes to or reads from HydraDB. This feature makes the "remember" step real.

The two-memory split is already settled in `README.md` and is not reopened here:

| | Operational memory | Knowledge memory |
|---|---|---|
| **What** | Live state — who owes what, by when, status | Settled context — decisions, rationale, SOPs |
| **Store** | PostgreSQL | HydraDB |
| **Access** | Exact `SELECT ... WHERE` | Retrieval |
| **Expires?** | Yes — a task rots if ignored | No — a decision is superseded, not stale |

The test for where something belongs: **does it expire?** HydraDB stores the sentence Mark
said; Postgres stores the task it became.

## Verified integration facts

Confirmed against the live HydraDB v2 documentation before planning. These are the facts
the design rests on, and the reasons for each decision below.

- **Python SDK exists.** `pip install "hydradb-sdk>=2,<3"`, `from hydra_db import HydraDB`,
  `HydraDB(token=os.environ["HYDRA_DB_API_KEY"])`. Matches our FastAPI/Python stack and the
  secrets rule in `docs/rules/security.md`.
- **Tenant isolation is a first-class primitive.** `client.databases.create(database=...)`
  gives one isolated workspace per company: *"strict database isolation. No cross-database
  aggregation, ever."* Maps directly onto the existing `hydra_tenant_id` column — v2 renamed
  the `tenant_id` parameter to `database`, so the column name is legacy but the value is
  correct. **No migration needed.**
- **Write path:** `client.context.ingest(type="knowledge", database=..., metadata=...)`.
- **Read path:** `client.query(database=..., type=..., query=...)` returning `data.chunks`.
- **Ingestion is asynchronous.** Content is not queryable until `context.status` reports
  `indexing_status == "completed"`.
- **Metadata filters are exact-equality only.** Verbatim from the v2 docs: *"Range, contains,
  or fuzzy matching belong in the query, query mode, or downstream reranking — not here."*
- **Filterable fields must be pre-declared** with `enable_match: true`, and *"if a field is
  not declared and match-enabled, HydraDB ignores that filter"* — silently.
- **Collections are retrieval-isolating.** *"Data written under one sub-tenant should not be
  expected to appear when recalled under another"* and *"a recall call uses the scope you
  provide. If your application needs data from multiple scopes, make multiple calls and merge
  the results yourself."*
- **Temporal reasoning is internal to recall**, not a queryable API. HydraDB maintains a
  git-style versioned temporal graph and self-reports 90.97% on temporal reasoning and 97.43%
  on knowledge updates (LongMemEval-s). Vendor-reported, accuracy only.
- **Latency is undocumented.** No p50/p95/p99 published. The risk entry in `README.md` stands.

## Decisions

### 1. One collection per company. Never split by source type.

Because collections are retrieval-isolating, splitting meetings / Slack / SOPs into separate
collections would turn *"what did we decide about pricing?"* into multiple API calls whose
relevance scores are not comparable, merged by hand — and would fragment the context graph,
which is the primary reason for using HydraDB at all. A decision made in a meeting, reaffirmed
in Slack, and written into an SOP must link as one entity.

Separation is by `source_type` **metadata**, not by collection. `sub_tenant_id` is omitted
entirely; writes land in the default sub-tenant.

### 2. No Postgres fact ledger. HydraDB is the knowledge graph.

An earlier draft proposed mirroring facts into a Postgres `knowledge_facts` table to hold
`valid_from` / `valid_to` / `supersedes_id`, on the reasoning that point-in-time queries need
range filters HydraDB does not have.

**This was rejected, and the reasoning is recorded because it is easy to re-derive.** A
point-in-time question does not need a range filter if each fact carries its date *in the
indexed text* and recall returns multiple versions of a subject — the chat model then reasons
*"in March it was $49, now it's $79"* over the returned chunks. That is precisely the
capability HydraDB benchmarks as temporal reasoning. The ledger would have rebuilt, at
significant cost, something the vendor already provides.

Postgres remains tasks-only. Its tools are already integrated and are not touched.

### 3. Supersession is HydraDB's job, not ours.

No supersession approval queue, no `superseded_by` links, no metadata patching in this phase.
We rely on the versioned temporal graph to resolve what is currently true. If retrieval proves
this wrong in practice, revisit — do not pre-build around it.

### 4. The write tool makes misuse structurally impossible.

The single largest long-term risk is an agent storing **its own inferences** as facts and
later reading them back as truth — a self-poisoning loop that is invisible until the graph is
already degraded.

This is prevented in the tool signature rather than the prompt: `source_quote` and `speaker`
are **required** parameters. The agent cannot record something no person said. This is Rule 6
("every task cites its source verbatim") applied to knowledge, and mirrors how the existing
`create_extracted_task` already forces a verbatim quote.

**Agent tool output is never ingested.** Only human-authored sources — transcripts today,
Slack threads and documents later.

### 5. The date goes in the indexed text, not only in metadata.

Since metadata cannot be range-filtered, temporal reasoning happens entirely through the model
reading dates on retrieved chunks. A fact stored as `"$49"` retrieves badly and reasons worse.
Facts are written as self-contained, date-prefixed sentences:

```
2026-08-14 — Starter tier pricing set to $49/month, down from $79, to undercut
Acme on entry price. (Alex Rivers, Sales Standup)
```

### 6. Scope: transcript writes, founder reads.

| Entry | Tool | Direction | `fact_type` values |
|---|---|---|---|
| `transcript` | `remember_fact` | write | `decision`, `fact`, `context` |
| founder `chat` | `search_memory` | read | — |

Employee chat, cron, and every existing Postgres tool are unchanged. Employee knowledge still
reaches the graph when they speak in a meeting — the extractor captures it with `speaker`
attribution — but there is no direct employee write path.

Founder chat is read-only. A founder write tool (*"remember that we decided X"*) is one line
in `_tools_for` if wanted later; it is not a design change.

## Metadata schema

### Match-enabled (declared at `databases.create()`, exact-match filterable)

| Field | Type | Example | Purpose |
|---|---|---|---|
| `subject` | VARCHAR | `pricing` | Scope a query to one topic |
| `fact_type` | VARCHAR | `decision` | Filter decisions from general context |
| `speaker` | VARCHAR | `Mark Chen` | Attribution; "what has Mark committed to?" |
| `source_ref` | VARCHAR | `meeting_8f3a2c` | Cite the meeting; join back to Postgres |
| `fact_key` | VARCHAR | `sha256(source_ref+statement)` | Dedup on re-extraction (Rule 3) |

`company_id` is deliberately **excluded**. The `database` is already the tenant boundary and
the docs are unambiguous about isolation; a second boundary that can silently no-op is worse
than one real one.

Fields **can** be added after creation via `PATCH /databases/{database}/metadata-schema`
(*"when you need to add filterable metadata fields after database creation"*). What is
undocumented is whether a field added later applies **retroactively to already-ingested
content** — the docs' guidance to *"plan filterable fields before ingestion"* suggests it does
not. Plan the list up front and assume older facts will not be filterable by fields added
afterwards.

### additional_metadata (free-form, returned but not filterable)

`source_quote` · `occurred_at` · `meeting_title` · `confidence`

## Tool contracts

```python
remember_fact(
    statement: str,      # self-contained, date-prefixed, pronouns resolved
    source_quote: str,   # verbatim — REQUIRED
    speaker: str,        # who said it — REQUIRED
    subject: str,        # "pricing", "hiring", "q4_forecast"
    fact_type: str,      # decision | fact | context
) -> dict

search_memory(
    query: str,
    subject: str | None = None,
) -> list[dict]
```

Both follow the established pattern in `app/agentic_ai/tools/employee_tools.py`: a factory
function closing over `company_id`, `record_audit` on both success and failure paths, and
summary-shaped returns rather than fat payloads (Rule 4). `search_memory` returns statements
with their `source_ref` and `source_quote` so every answer can cite its origin.

## Prompting

Trigger rules matter more than tool descriptions. Both prompts already compose from
`render_base_prompt`, so these slot in without restructuring.

**Extractor** — a transcript yields two things: commitments and knowledge. Call
`create_extracted_task` for anything someone owes. Call `remember_fact` for decisions reached,
numbers agreed, policies stated, or rationale given — things that remain true after the task is
done. *"We're going with $49 and Mark updates the page by Friday"* is both: one fact, one task.

**Founder chat** — call `search_memory` before answering any question about why something was
decided, what a term means, or what was agreed previously. Use `query_tasks` for live state.
Never answer from conversational memory when a tool can confirm it.

**Negative rule, both** — never call `remember_fact` on your own analysis, summaries, or
inferences. Only on something a person actually said, quoted verbatim.

## Failure modes

- **HydraDB unreachable** → chat degrades to Postgres-only and says knowledge recall is
  unavailable. It must never 500. A read-only assistant that half-answers beats one that errors.
- **Silently ignored filter** → assert the declared metadata schema at provisioning and fail
  loudly, rather than returning unfiltered results that look scoped.
- **Not yet indexed** → ingestion is async, so a fact written during a meeting is not
  immediately searchable. Ingest before demoing that path.
- **Duplicate facts on re-extraction** → `fact_key` is the intended guard (Rule 3), but
  HydraDB's dedup behaviour is undocumented. **Open question — verify against the live API
  before claiming idempotency.**

## Constraints

- No changes to Postgres schema, task tools, approvals, or the cron path.
- `HYDRA_DB_API_KEY` lives in `.env`, never in code (`docs/rules/security.md`).
- Every tool call is audit-logged (Rule 5).
- Tools return summaries by default (Rule 4).
- A `KnowledgeStore` seam keeps the vendor swappable — the README already commits to a pgvector
  fallback if latency proves unworkable.
- `CHANGELOG.md` entry is required on completion.

## Out of scope

Postgres fact ledger · supersession approval UI · employee write access · extractor reading
memory · Slack/email ingestion · pgvector fallback implementation · founder chat writes

## Open questions

> Resolved during implementation — see the `[0.10.0]` entry in `CHANGELOG.md` for the
> verified findings. Dedup is handled by the document `id` acting as an upsert key;
> recall latency measured at ~1.6s plain and ~3.6–6.2s with `temporal_now`; indexing
> takes ~3 minutes to reach `completed`. Schema retroactivity remains unverified.


1. **Latency.** Time `client.query` against a realistic corpus. Under 2s → request path;
   over 5s → background enrichment. This decides whether `search_memory` is a live tool call.
2. **Dedup.** Does `fact_key` in metadata actually prevent duplicate ingestion, or must we
   check via `context.list` first?
3. **Metadata schema retroactivity.** Does a field added via `PATCH .../metadata-schema`
   become filterable on content ingested before it was declared?
4. **Docs version drift.** The documentation mixes v1 (`tenant_id`, `tenant_metadata_schema`,
   `client.recall.full_recall()`) and v2 (`database`, `database_metadata_schema`,
   `client.query()`). Build against v2; the `fullRecall()` named in `README.md` is the v1 name.
