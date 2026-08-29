# Sentinel

**The operational layer for a business.** Captures what was decided, tracks who owes
what, and chases until it's done.

---

## What it is

Sentinel is a task manager that chases on its own, and remembers why.

Meeting tools (Fireflies, Otter, Granola) stop at "here are your action items." Task
tools (Linear, Asana) need a human to type them in. Both leave the same gap: someone
still has to remember who owes what and go ask them.

Sentinel closes that gap. One loop:

```
input (meeting / Slack / manual)
  → extract commitments
  → founder approves
  → delegate in Slack
  → chase on a schedule
  → collect status back
  → remember it
```

**The chase-and-collect step is the product.** Everything else is table stakes.

## Two kinds of memory

These are separate systems answering different questions. Keeping them separate is the
core architectural decision.

| | **Operational memory** | **Knowledge memory** |
|---|---|---|
| **What** | Live state — who owes what, by when, status | Settled context — decisions, rationale, SOPs |
| **Store** | PostgreSQL | HydraDB |
| **Access** | Exact `SELECT ... WHERE` | Retrieval |
| **Expires?** | Yes — a task rots if ignored | No — a decision gets superseded, not stale |
| **Example** | "What's overdue?" | "What did we decide about pricing in March?" |

The test for where something belongs: **does it expire?**

The split in one line — **HydraDB stores the sentence Mark said. Postgres stores the
task it became.** The task row points back to the source.

### Non-negotiable

Task state never lives in HydraDB. `WHERE status='overdue'` must be exact and
transactional, never fuzzy retrieval. A confidently wrong answer to "what's overdue" is
worse than no answer.

## Why this is worth building

**Nobody writes any of it down, and it's all still there in six months.**

The history is exhaust from work people were already doing. Run the loop for a few weeks
and you have an operational record nobody authored:

- **Follow-up stops costing hours.** The founder reads one morning digest instead of
  remembering who owes what.
- **"Why did we do that?" becomes answerable** — the decision, the date, the reasoning,
  and the meeting it came from.
- **Accountability is a record, not an argument.** "Blocked for six days with no
  escalation" is a query.

Extraction is commodity and will be free within a year. What compounds is the history —
and you only get history if the loop actually runs and people actually respond.

## Two users

**Founder** — approves extracted tasks, queries history in chat, reads the daily digest.
Lives in the dashboard.

**Employee** — receives tasks as Slack DMs, taps a status button, flags blockers. Never
opens the dashboard. Their entire experience is Slack.

## Architecture

Three tool-calling agents. No orchestration graph — at ~5 tool calls and one branch, a
state graph is pure overhead.

```
┌─ Agents (DeepAgents, tool-calling loops) ────────────┐
│  Extractor  — text in → create_task() [pending]      │
│  Follow-up  — invoked daily by cron                  │
│  Chat       — read-only: query_tasks + search_memory │
└──────────────────────────────────────────────────────┘
                    ↓ all writes pass through
┌─ Thin deterministic tool layer ──────────────────────┐
│  create_task() ALWAYS → status=pending_approval      │
│  idempotency key on every write                      │
│  audit log: agent, input, result, timestamp          │
└──────────────────────────────────────────────────────┘
        ↓                                    ↓
┌─ PostgreSQL ───────────┐   ┌─ HydraDB ──────────────┐
│ tasks, status, owner   │   │ transcripts, SOPs      │
│ employees, managers    │   │ decisions + rationale  │
│ approval queue         │   │ temporal reasoning     │
│ audit log              │   │ tenant per company     │
│ → system of record     │   │ → memory / retrieval   │
└────────────────────────┘   └────────────────────────┘
        ↑
   cron (daily wake-up)
```

Cron owns **when**. The agent owns **what**. Approval pauses are genuine interrupts,
resumed by a human action.

### Rules

1. `create_task()` can only produce `pending_approval` — a schema default, never a model
   decision. The trust story can't rest on the LLM remembering to ask.
2. Task state lives in Postgres only. Never HydraDB.
3. Idempotency key on every write, derived from `(source_id, task_title)`. Re-running an
   agent must never duplicate a task or re-send a DM.
4. Tools return summaries by default, detail on request. One fat tool return blows the
   context even on a short loop.
5. Every tool call is audit-logged.
6. Every task cites its source verbatim — *"from Sales Standup, 10:04 — 'Mark, can you
   present this?'"*
7. Employees answer with Block Kit buttons (`Done / In Progress / Blocked / Need more
   time`), not free text. One tap beats NLU and gets far higher response rates.
8. Digest, not drip. One morning summary; immediate ping only for blockers. A bot that
   pings on every update gets muted in week two.

## Build order

The principle: **build the deterministic loop first, add AI as an input to it.** Build
the agents first and you'll spend the whole time debugging prompts with nothing to write
to.

| # | Step | Notes |
|---|---|---|
| 1 | Schema + row-level tenancy | Company → employees → tasks → status updates. `company_id` on every row. No AI yet. |
| 2 | **Slack, early** | OAuth, member-list → `slack_user_id` mapping, DM send, interactivity endpoint. Riskiest external dependency — do it before it's fun. |
| 3 | Manual task creation | A form. Boring on purpose — this is demo insurance. |
| 4 | **The loop** | approve → DM → button → status writeback. **A working product stops here**, with no LLM involved. |
| 5 | Extraction | Transcript → pre-filled tasks with source quotes, into the same queue from step 4. The AI is just a faster way to fill the form. |
| 6 | Chasing + digest | Daily cron, escalation on timeout, one morning digest. Plus a "run follow-up now" button for a time-compressed demo. |
| 7 | Chat | `query_tasks` (Postgres) first. `search_memory` (HydraDB) added last. |

Steps 1–4 are a working product. 5–6 are the demo. 7 is what makes it feel like memory
rather than a task tracker.

The knowledge layer is **additive** — nothing in the core loop breaks if retrieval
disappears.

## Stack

**Frontend** — Next.js 16, TypeScript, Tailwind, Zustand, Axios
**Backend** — FastAPI, Pydantic, Alembic
**Agents** — DeepAgents (OSS, self-hosted), LangGraph runtime + `PostgresSaver`, APScheduler
**Data** — PostgreSQL (Neon) as system of record, HydraDB for temporal knowledge
**Integrations** — Slack (Bolt, Block Kit), WhisperX for transcription
**Infra** — Docker, VPS

## Status

Planning and architecture settled. **No application code yet** — `backend/` and
`frontend/` are empty. Target is a hackathon demo.

## Positioning

Do not claim "nothing leaves your servers." Every extraction and chat answer calls an LLM
provider. The defensible version:

> Your system of record — tasks, employees, documents — stays in your Postgres on your
> infrastructure. LLM inference runs under a zero-retention agreement. Self-hosted and
> air-gapped deployments available on request.

We're model-agnostic, so local open-weights is a real answer for air-gapped buyers.

## Known risks

| Risk | Mitigation |
|---|---|
| Interrupt resume with edit/reject may be buggy (issue #554 — reported for subagents; we don't use them) | Spike one approval-gated tool with all three modes before building on it |
| HydraDB latency is undocumented | Time `fullRecall()` early. Under 2s → request path. Over 5s → background enrichment, fall back to pgvector |
| Slack interactivity needs a public HTTPS endpoint | Tunnel + one button round-trip on day one, not demo morning |
| Extraction is ~70% accurate on messy real meetings | Exactly why approval is structural and every task cites its source |

## Docs

- [User stories](docs/context/user_stories.md)
- [Backend folder structure](docs/context/backend_folder_structure.md)
- [Coding conventions](docs/rules/coding-conventions.md) · [Security](docs/rules/security.md) · [Error handling](docs/rules/error-handling.md) · [Changelog rules](docs/rules/change-log.md)
