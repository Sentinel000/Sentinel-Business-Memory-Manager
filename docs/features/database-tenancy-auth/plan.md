# Step 1 — Database, Tenancy & Auth

## Context

Sentinel is the operational layer for a business: it captures what was decided, tracks
who owes what, and chases until it's done. The core loop is
`extract → approve → delegate → chase → collect → remember`.

The repo currently has **zero application code** — `backend/` and `frontend/` are empty
directories. Architecture, rules, and a full backend folder structure are documented,
but nothing is built.

This plan covers **build-order step 1**: the foundation everything else sits on. It is
deliberately the least glamorous step, and it is the one that is miserable to retrofit.
Two things must be right on day one:

1. **`company_id` on every row, scoped automatically.** Adding tenant filters to queries
   that already exist is error-prone and leaks data when one is missed.
2. **`users` and `employees` are separate tables.** Onboarding creates Mark from a pasted
   paragraph *before* Mark has a login — possibly before he ever gets one. Merging these
   into one table is the mistake that forces a rewrite in step 7.

**Outcome:** a founder can log in, receive a JWT carrying `company_id`, and every
subsequent query is automatically scoped to their company. No AI, no Slack, no LLM.

**Branch:** `database-setup`.

---

## Data model

Seven tables. All except `companies` carry `company_id`.

```
companies        id, name, persona_config jsonb, slack_bot_token,
                 hydra_tenant_id, escalation_after_days, timestamps

users            company_id, email, password_hash,
                 role enum(founder|employee), employee_id (nullable FK), is_active
                 → UNIQUE (company_id, email)

employees        company_id, name, role_title, slack_user_id,
                 manager_id (self-FK, nullable)

tasks            company_id, title, description, owner_employee_id, deadline,
                 status enum, source_quote, source_ref, confidence,
                 idempotency_key, created_by_agent
                 → UNIQUE (company_id, idempotency_key)

status_updates   company_id, task_id, status, note, reported_by_employee_id,
                 reported_via enum(slack|dashboard|agent), created_at

approvals        company_id, task_id, state enum(pending|approved|edited|rejected),
                 decided_by_user_id, decided_at, thread_id, edited_payload jsonb

audit_log        company_id, agent, tool, input jsonb, result jsonb,
                 status, created_at
```

### The `users` / `employees` split

- **Founder** = a `user` with `role=founder`, usually **no** `employee` row.
- **Employee** = an `employee` row that **may** later get a `user`.
- The link is nullable and populated when an employee signs up.

`employees` is the org chart and the task target. `users` is login identity only.

**Decision:** the FK lives only on `users.employee_id`. A second FK on
`employees.user_id` would create a circular dependency between the two tables and allow
the two halves to disagree about who is linked to whom. The reverse direction is a
SQLAlchemy relationship, not a column.

### Enums

Python `enum.Enum` + native Postgres enum types.

- `UserRole` — `founder`, `employee`
- `TaskStatus` — `pending_approval`, `approved`, `in_progress`, `blocked`, `done`,
  `rejected`, `overdue`
- `ApprovalState` — `pending`, `approved`, `edited`, `rejected`
- `ReportedVia` — `slack`, `dashboard`, `agent`

**Decision:** enums persist the member *value*, not the Python *name*, via a shared
`pg_enum()` helper using `values_callable`. SQLAlchemy's default stores `.name`
(`'PENDING_APPROVAL'`), which would not match a server default written as
`'pending_approval'` — every insert relying on the default would fail.

### Rules encoded in the schema, not in code

- `tasks.status` **server default is `pending_approval`.** Non-negotiable rule #1 — the
  trust story cannot depend on the LLM remembering to ask.
- `UNIQUE (company_id, idempotency_key)` on `tasks` — rule #3, enables upsert so a
  re-run never duplicates.
- `tasks.source_quote` carries the verbatim citation — rule #6. Nullable overall so
  manual creation still works; the tool layer enforces it for agent writes.

### `persona_config` (JSONB on `companies`)

```json
{
  "assistant_name": "Sentinel",
  "tone": "direct",
  "company_context": "25-person B2B SaaS...",
  "glossary": { "ACV": "annual contract value" }
}
```

`assistant_name` + `tone` shape Slack DM copy; `company_context` + `glossary` go into
the extractor prompt (they resolve "Mark" and "ACV"). Rendered into the system prompt at
agent construction, not per tool call.

**`escalation_after_days` is a real column, not a persona key.** Timing is read by
`list_stale_tasks()` as an argument — cron owns *when*, the agent owns *what*. It must
never be a vibe word the model interprets.

**Security note:** `company_context` is founder-supplied free text destined for a system
prompt. Cap its length at the Pydantic layer and treat it as data. It must never be able
to relax the `pending_approval` gate.

---

## Files

Follows the documented tree in `docs/context/backend_folder_structure.md`. Only the
subset step 1 needs — no empty modules scaffolded for later steps.

```
backend/
├── requirements.txt
├── .env.example
├── alembic.ini
├── alembic/
│   ├── env.py                # reads the URL from app.config
│   └── versions/…_initial_schema.py
├── scripts/
│   ├── seed.py               # demo tenant
│   └── verify.py             # runnable guarantee checks
└── app/
    ├── main.py  config.py  database.py  dependencies.py
    ├── exceptions.py  middleware.py
    ├── api/router.py  api/v1/auth.py
    ├── core/security.py
    ├── models/  base.py enums.py company.py employee.py user.py
    │             task.py status_update.py approval.py audit_log.py
    ├── schemas/auth.py
    └── repositories/  base.py user.py employee.py company.py
```

---

## Tenancy — the load-bearing part

**Enforce in the repository layer, not Postgres RLS.** RLS is stronger (a forgotten
filter cannot leak) but adds setup and fights connection pooling. For this timeline,
repository-layer scoping in a base class is the right trade — because it is in the base
class, nobody *can* forget it.

Three pieces:

1. **`TenantMixin`** (`app/models/base.py`) — declarative mixin providing an indexed,
   non-null `company_id` FK. Every model except `Company` inherits it.
2. **`TenantScopedRepository`** (`app/repositories/base.py`) — generic CRUD constructed
   with `(session, company_id)`. Every read injects `WHERE company_id = :company_id`;
   every write sets it and **discards a caller-supplied `company_id`**. Subclasses add
   domain queries and inherit scoping for free.
3. **`get_current_user`** (`app/dependencies.py`) — decodes the JWT and loads the user,
   re-checking them against the token's `company_id`. Routes receive an already-scoped
   repository.

> The one rule: a route handler never constructs a query without going through a
> tenant-scoped repository.

**Exception:** `find_user_for_login()` is the single deliberately unscoped query. It
cannot be tenant-scoped because resolving the tenant is its purpose.

### On "instance per company"

Build **row-level, single deploy**. Per-instance is a *deploy-time* decision — a
different `DATABASE_CONNECTION_STRING` and a `companies` table with one row. The code is
identical either way, so the isolated-deployment sales story stays true without
operating N stacks.

---

## Auth

**Custom JWT.** Neon is just Postgres and has no opinion about auth. Neon Auth /
Stack Auth would add a third party to issue tokens for essentially one user per tenant,
and puts an external dependency in the path of the "runs on your infrastructure" claim.
Revisit only if Google/Slack SSO becomes a day-one requirement.

- `core/security.py` — `hash_password` / `verify_password` (passlib + bcrypt, **pinned
  `bcrypt==4.0.1`**; passlib 1.7.4 reads `bcrypt.__about__`, removed in 4.1),
  `create_access_token`, `decode_access_token`.
- Claims: `{ sub, company_id, role, exp, iat }`. `company_id` in the token is the
  tenancy boundary — this is why it must be signed, never supplied.
- `POST /api/v1/auth/login` → email + password → token. The same error is returned for
  an unknown email and a wrong password, so the endpoint cannot enumerate accounts.
- `GET /api/v1/auth/me` → current user + company.
- `require_founder` dependency — a simple role check. **No RBAC tables**: two roles and
  roughly four differing actions.

**Employee logins are supported by the schema but no employee-facing routes are built in
this step.** Slack remains their entire experience for v1. If employees later get chat,
`knowledge_sources` needs a `visibility` column (`founder_only | all_employees`) so
`search_memory` can filter — otherwise an employee can ask "what did we decide about
headcount." That is a step-7 addition to a table that does not exist yet.

---

## Connection handling

Neon-specific, discovered during implementation:

- Neon hands out `postgresql://` URLs; SQLAlchemy reads that as psycopg2, which is not
  installed. `settings.sqlalchemy_url` normalises the prefix to `postgresql+psycopg://`
  rather than relying on whoever pastes the URL.
- The `-pooler` endpoint is pgbouncer in transaction mode, which cannot keep server-side
  prepared statements. `prepare_threshold=None` is passed when the URL is a pooled one.

---

## Project rules to honour

From `docs/rules/`:

- Python type hints on every route and function; `snake_case` for Python.
- All request/response models are Pydantic. All schema changes via Alembic — never
  mutate directly.
- Structured errors `{ "error": ..., "code": ... }` with correct status codes, registered
  once in `exceptions.py` so the shape is structural rather than repeated per route.
- No secrets committed; every env var documented in `.env.example`. A `.gitignore`
  covering `.env` is a prerequisite — the repo had none.
- Never log passwords or tokens.
- Add a `CHANGELOG.md` entry when done.

---

## Verification

**Migration**
- `alembic upgrade head` succeeds; `downgrade base` then `upgrade head` succeeds again.
  This is what catches the autogenerate enum bug — inline `sa.Enum` emits `CREATE TYPE`
  once per table (`task_status` is used by two) and never drops the types on downgrade.
- Every table except `companies` has a non-null indexed `company_id`.

**Schema rules**
- A task inserted with no explicit status comes back `pending_approval`.
- Two tasks with the same `(company_id, idempotency_key)` → `IntegrityError`.
- The same key under a *different* `company_id` → succeeds.

**Tenancy — the critical test**
- Two seeded companies, each with employees and tasks.
- A repository for company A returns zero of company B's rows on every list method.
- Fetching a company-B row **by its exact primary key** through a company-A repository
  returns `None`.
- `repository.create()` ignores a caller-supplied `company_id`.

**Auth**
- Valid login → 200; decoded claims carry the right `company_id` and `role`.
- Wrong password → 401, and the body is byte-identical to the unknown-email response.
- No token → 401. Tampered signature → 401. Expired token → 401.
- A token pairing a real user with another company → 401.
- A deactivated user → 403.
- Founder-only route with an employee-role token → 403.

**Manual smoke**
- `uvicorn app.main:app --reload`, log in via `/docs`, call `/auth/me`.
