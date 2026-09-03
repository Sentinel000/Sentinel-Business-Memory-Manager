<div align="center">

<img src="frontend/public/sentinel-logo.png" alt="Sentinel logo" width="120" height="120" />

# Sentinel

### The AI business companion that remembers what was decided — and chases it until it's done.

Sentinel turns meetings, threads, and offhand promises into tracked tasks, routes them through
founder approval, assigns them to their owner, then chases on a schedule and collects status back
automatically. It can't make someone respond — it guarantees the founder knows who hasn't.

[![Status](https://img.shields.io/badge/status-active%20development-0891b2?style=flat-square)](#project-status)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776ab?style=flat-square&logo=python&logoColor=white)](#prerequisites)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](#tech-stack)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=flat-square&logo=next.js&logoColor=white)](#tech-stack)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178c6?style=flat-square&logo=typescript&logoColor=white)](#tech-stack)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-4169e1?style=flat-square&logo=postgresql&logoColor=white)](#tech-stack)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square)](#contributing)

**extract → approve → delegate → chase → collect → remember**

</div>

---

## Table of Contents

- [The problem](#the-problem)
- [What Sentinel does](#what-sentinel-does)
- [Key features](#key-features)
- [Two kinds of memory](#two-kinds-of-memory)
- [How it works](#how-it-works)
- [Tech stack](#tech-stack)
- [Getting started](#getting-started)
- [Using Sentinel](#using-sentinel)
- [API surface](#api-surface)
- [Project structure](#project-structure)
- [Configuration](#configuration)
- [Project status](#project-status)
- [Contributing](#contributing)
- [Documentation](#documentation)

---

## The problem

Every week a founder loses hours to the same loop: *remember who owes what, go ask them,
write it down, ask again.*

The tools we already use don't close that loop:

- **Meeting tools** (Fireflies, Otter, Granola) stop at *"here are your action items."*
- **Task tools** (Linear, Asana) wait for a human to type those items in — then someone still
  has to remember to chase.

Both leave the same gap. **Somebody has to remember, and somebody has to follow up.**
Nobody writes any of it down, and six months later the reasoning behind a decision is gone.

## What Sentinel does

Sentinel owns the missing middle. It captures commitments from the work people are *already*
doing, then runs one continuous loop:

```
input (meeting / thread / email / typed sentence)
  → extract commitments        (who owes what, by when, with the exact quote)
  → founder approves           (edit / approve / reject — one click)
  → delegate to the owner      (lands in the employee's own task view)
  → chase on a schedule        (daily cycle, short ladder, handed back on timeout)
  → collect status back        (Complete / In Progress / Blocked)
  → remember it                (a searchable record nobody had to author)
```

> **The chase-and-collect step is the product.** Extraction and task lists are table stakes —
> everyone has them. Closing the loop and remembering *why* is what compounds.

Run it for a few weeks and you get an operational record nobody wrote on purpose:

- **Follow-up stops costing hours** — the founder reads one briefing instead of chasing.
- **"Why did we do that?" becomes answerable** — the decision, the date, the reasoning, the meeting.
- **Accountability becomes a query, not an argument** — *"blocked for six days with no escalation."*

## Key features

| Feature | What it does |
|---|---|
| **AI extraction** | Turns a transcript, thread, or typed sentence into structured tasks with owner, deadline, and a verbatim source quote. |
| **Human-in-the-loop approval** | Every AI write lands in a `pending_approval` queue. Nothing is delegated without a founder's sign-off. |
| **Zero-friction delegation** | Approved tasks land in each owner's own task view — one tap to report status, no typing. |
| **Automated chasing** | A deterministic daily cycle reminds quiet owners, then hands a task back to the founder when the ladder runs out. |
| **On-demand briefings** | A founder report of what moved, what's blocked, and what's due — regenerated safely, without re-chasing anyone. |
| **Ask your business** | Read-only chat over live state and settled history — *"what's blocking the Q4 forecast?"* |
| **Multi-tenant by design** | A dedicated instance per client, with `company_id` row-level tenancy on every record. |
| **Full audit trail** | Every tool call logs actor, input, result, and timestamp. Idempotency keys make re-runs safe. |

## Two kinds of memory

Sentinel separates two systems that answer different questions. Keeping them apart is the
single most important architectural decision in the project.

| | **Operational memory** | **Knowledge memory** |
|---|---|---|
| **What** | Live state — who owes what, by when, current status | Settled context — decisions, rationale, SOPs |
| **Store** | PostgreSQL (Neon) | HydraDB |
| **Access** | Exact `SELECT ... WHERE` | Semantic retrieval |
| **Expires?** | Yes — a task rots if ignored | No — a decision is superseded, not stale |
| **Example** | *"What's overdue?"* | *"What did we decide about pricing in March?"* |

The test for where something belongs is one question: **does it expire?**

In a single line — **HydraDB stores the sentence Mark said; Postgres stores the task it became.**
The task row points back to its source.

> **Non-negotiable:** task state never lives in HydraDB. `WHERE status = 'overdue'` must be exact
> and transactional, never fuzzy retrieval. A confidently wrong answer to *"what's overdue?"* is
> worse than no answer at all.

## How it works

Two AI agents sit on top of a thin, deterministic tool layer, and chasing is a query — not a
model. There is no heavy orchestration graph: at roughly five tool calls and one branch, a state
graph would be pure overhead. **The agents own *what*, cron owns *when*, and "who has gone quiet"
is answered by SQL, never by an LLM.** Approval pauses are genuine interrupts, resumed by a human.

```mermaid
flowchart TB
    subgraph Agents["AI agents (tool-calling loops)"]
        X["Extractor<br/>text in → task (pending)"]
        C["Chat<br/>read-only answers"]
    end
    subgraph Tools["Deterministic tool layer"]
        T["create_task() → always pending_approval<br/>idempotency key on every write<br/>audit log: actor, input, result, time"]
    end
    Chase["Chase cycle — no model<br/>remind quiet owners → hand back on timeout"]
    subgraph Data["Data"]
        P[("PostgreSQL<br/>tasks · employees · approvals · audit<br/>system of record")]
        H[("HydraDB<br/>transcripts · SOPs · decisions<br/>memory / retrieval")]
    end
    E{{"Employee task view<br/>tap to report status"}}

    X --> T
    C --> T
    T --> P
    C -. read-only .-> H
    Chase --> P
    P --> E
    E --> P
    Cron["⏰ daily cron · 08:00 UTC"] --> Chase
```

### The rules that make it trustworthy

1. **`create_task()` can only ever produce `pending_approval`** — a schema default, never a model
   decision. The trust story can't rest on the LLM remembering to ask.
2. **Task state lives in Postgres only.** Never HydraDB.
3. **Idempotency key on every write**, derived from `(source_id, task_title)`. Re-running an agent
   must never duplicate a task or re-send a reminder.
4. **Tools return summaries by default, detail on request.** One fat return blows the context window.
5. **Every tool call is audit-logged.**
6. **Every task cites its source verbatim** — *"from Sales Standup, 10:04 — 'Mark, can you present this?'"*
7. **Employees answer with buttons, not free text.** One tap in their task view beats NLU and gets
   far higher response rates.
8. **The chase ladder is short and terminates.** Two reminders, then the task is handed back to the
   founder — unbounded chasing fills the briefing with tasks nobody will action. Blocked is never
   chased; it goes straight to the founder.

## Tech stack

**Languages** — Python 3.11+, TypeScript 5.7

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 15, React 19, Tailwind CSS, Zustand (state), Axios, lucide-react, d3-force (org chart) |
| **Backend** | FastAPI, Pydantic v2, SQLAlchemy 2, Alembic (migrations), APScheduler (daily cron) |
| **Agents / AI** | Two LangGraph + LangChain agents (Extractor, Chat); chasing is deterministic SQL, not a model |
| **LLM provider** | Qwen (Alibaba Cloud Model Studio) via an OpenAI-compatible endpoint — model-agnostic |
| **Transcription** | Qwen ASR Flash (audio → text with segments) |
| **Operational data** | PostgreSQL on Neon (serverless), psycopg 3, pgbouncer-aware pooling |
| **Knowledge data** | HydraDB (`hydradb-sdk`) for temporal retrieval — optional, degrades gracefully |
| **Employee channel** | In-product task view (`/me`) — Slack retired as a delivery channel in v0.14.0 |
| **Infrastructure** | Docker, VPS |

## Getting started

### Prerequisites

- **Python** 3.11 or newer
- **Node.js** 18 or newer
- **PostgreSQL** — a local server or a managed instance (Neon works out of the box)
- **A Qwen API key** — required for the agent layer and meeting transcription

### 1. Clone and configure

```bash
git clone https://github.com/your-org/Sentinel-Business-Memory-Manager.git
cd Sentinel-Business-Memory-Manager

# The app reads .env from the repo root.
cp backend/.env.example .env
```

Open `.env` and fill in the two values that matter most:

```dotenv
DATABASE_CONNECTION_STRING=postgresql+psycopg://user:password@ep-xxx.region.aws.neon.tech/dbname?sslmode=require
QWEN_API_KEY=your-key-here
```

> Generate a strong JWT secret with:
> `python -c "import secrets; print(secrets.token_urlsafe(48))"`

### 2. Run the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

alembic upgrade head             # create the schema
python -m scripts.seed           # load the demo tenant + a pending task
uvicorn app.main:app --reload    # start the API on http://localhost:8000
```

Check it's alive:

- **Health:** `GET http://localhost:8000/health`
- **Interactive API docs:** `http://localhost:8000/docs` *(disabled in production)*

### 3. Run the frontend

```bash
cd frontend
npm install
npm run dev                      # http://localhost:3000
```

If the browser blocks API calls, make sure `CORS_ORIGINS` in `.env` includes
`http://localhost:3000`.

### 4. Log in with the demo account

The seed script creates a ready-to-explore tenant:

| Field | Value |
|---|---|
| **Company** | Northwind SaaS |
| **Email** | `sarah@northwind.example` |
| **Password** | `sentinel-demo-2026` |

You'll land in the founder dashboard with one task already waiting in the approval queue.

## Using Sentinel

**As a founder (in the dashboard):**

1. **Capture** — upload meeting audio, paste a transcript, or type a commitment by hand.
2. **Approve** — open the approval queue, review each extracted task and its source quote, then
   approve, edit, or reject.
3. **Ask** — use chat to query live state and history: *"what's overdue?"*, *"what did we decide
   about pricing in March?"*
4. **Read the briefing** — an on-demand report of what moved, what's blocked, and what's due.
5. **Configure** — set the assistant persona, escalation window, and auto-approve threshold in settings.

**As an employee (in your own task view):**

1. See the commitments assigned to you.
2. Tap a button: **Complete / In Progress / Flag Blocker**.
3. A blocker goes straight to the founder.

> There is no push notification — a reminder lives in the dashboard, so an unread nudge looks just
> like an employee who hasn't logged in. Sentinel can't force a reply, but a task that goes quiet
> is chased and then handed back to the founder, so nothing rots silently.

## API surface

All endpoints are mounted under `/api/v1`.

| Router | Purpose |
|---|---|
| `auth` | Founder/employee signup, login, JWT issuance |
| `tasks` | Create, list, update tasks; append-only status timeline |
| `approvals` | Approve, edit, reject, bulk-approve extracted tasks |
| `employees` | Manage the org chart and task ownership |
| `company` | Tenant configuration and settings |
| `onboarding` | Bulk employee import and readiness checks |
| `me` | Employee-facing task list and status updates |
| `meetings` | Audio/text ingestion, transcription, extraction |
| `chat` | Read-only Q&A over Postgres and HydraDB |
| `knowledge` | Knowledge-layer queries and provisioning |
| `reports` | Chase tracking and generated reports |
| `admin` | Trigger a chase cycle on demand (`POST /admin/run-chase`) |

## Project structure

```
Sentinel-Business-Memory-Manager/
├── backend/
│   ├── app/
│   │   ├── agentic_ai/      # Extractor + Chat agents, deterministic tools, prompts
│   │   ├── api/v1/          # FastAPI routers (auth, tasks, approvals, chat, ...)
│   │   ├── core/            # Scheduler (daily cron) + security (JWT, hashing)
│   │   ├── knowledge/       # HydraDB store + provisioning
│   │   ├── models/          # SQLAlchemy ORM (system of record)
│   │   ├── repositories/    # Data access, tenant-scoped
│   │   ├── schemas/         # Pydantic request/response models
│   │   └── services/        # Business logic (tasks, meetings, approvals, chase, reports)
│   ├── alembic/             # Database migrations
│   └── scripts/             # Seed + verification scripts
├── frontend/
│   └── src/
│       ├── app/             # Next.js routes (dashboard, employee, auth)
│       ├── components/      # React UI
│       ├── stores/          # Zustand state
│       └── lib/             # Axios client + helpers
└── docs/                    # Design, rules, and feature playbooks
```

## Configuration

All settings load from the root `.env` (see [`backend/.env.example`](backend/.env.example)).

| Variable | Required | Description |
|---|---|---|
| `DATABASE_CONNECTION_STRING` | ✅ | Postgres URL. `postgres://` is auto-normalised to `postgresql+psycopg://`. |
| `QWEN_API_KEY` | ✅ | Key for the OpenAI-compatible LLM endpoint. Agents and ASR fail without it. |
| `JWT_SECRET_KEY` | ✅ | Signs tokens — this is the tenancy boundary (`company_id` is a signed claim). |
| `QWEN_API_BASE` | — | Base URL for the model endpoint. |
| `AGENT_MODEL` | — | Model name used by the agents (default `qwen3.6-plus`). |
| `AUTO_APPROVE_THRESHOLD_DEFAULT` | — | Confidence at/above which a task auto-approves. `1.0` disables auto-approval. |
| `HYDRA_DB_API_KEY` | — | Enables the knowledge layer. Empty disables it without breaking startup. |
| `CORS_ORIGINS` | — | Comma-separated allowed origins (default `http://localhost:3000`). |
| `ENVIRONMENT` | — | `development` or `production` (disables Swagger docs in production). |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | — | Token lifetime (default `480`). |

## Project status

The core loop is **built and runnable**: schema + multi-tenancy, auth, manual and AI task
creation, the approval gate, meetings + transcription, deterministic chasing, briefings, and chat
are all implemented end to end.

| Area | State |
|---|---|
| Schema, tenancy, auth | ✅ Implemented |
| Task lifecycle + approval gate | ✅ Implemented |
| Meetings + transcription (Qwen ASR) | ✅ Implemented |
| Extractor + Chat agents | ✅ Implemented |
| Deterministic chase cycle + escalation | ✅ Implemented |
| Briefings / reports (on demand) | ✅ Implemented |
| Founder dashboard + employee task view | ✅ Implemented |
| HydraDB knowledge layer | 🟡 Optional — degrades gracefully when unconfigured |
| Slack as a delivery channel | ⛔ Retired in v0.14.0 — chasing moved in-product |

## Contributing

Contributions are welcome. To keep things smooth:

1. **Fork** the repository and create a feature branch from `main`.
2. **Follow the house rules** in [`docs/rules/`](docs/rules/) — coding conventions, security,
   and error handling are enforced across the codebase.
3. **Update the changelog.** Every code change adds an entry — see
   [`docs/rules/change-log.md`](docs/rules/change-log.md).
4. **Keep the loop deterministic.** New writes go through the tool layer, land in
   `pending_approval` by default, and carry an idempotency key.
5. **Open a pull request** with a clear description of the problem and the approach.

Please read [`AGENTS.md`](AGENTS.md) and the [feature playbooks](docs/features/) before starting
significant work — they explain the *why* behind the architecture.

## Documentation

- [User stories](docs/context/user_stories.md)
- [Design system](docs/context/design.md)
- [Backend folder structure](docs/context/backend_folder_structure.md)
- [Feature playbooks](docs/features/) — architecture, plans, and tasks per feature
- Rules: [Coding conventions](docs/rules/coding-conventions.md) · [Security](docs/rules/security.md) · [Error handling](docs/rules/error-handling.md) · [Changelog](docs/rules/change-log.md)

---

<div align="center">

**Sentinel — extract, approve, delegate, chase, collect, remember.**
Your system of record stays in *your* Postgres, on *your* infrastructure.

</div>
