# Changelog

## [0.11.0] - 2026-09-01

### Added
- **Typed tool results in chat.** A tool now tags its own return with a `kind` on its success path (`task_list`, `task_created`, `task_updated`, `task_approved`, `task_rejected`, `task_detail`), and the chat UI maps that tag to a component. `query_tasks` renders as task rows with owner, due date, days-late, and a status chip instead of a JSON blob.
- `ToolExecution` carries `kind` and `data` (`backend/app/schemas/chat.py`). Without the schema fields Pydantic drops them silently on the way out, so both were added before anything else.
- `frontend/src/components/ToolResultRenderers.tsx` — the `kind` → component registry, plus `isOutcome`/`rendererFor`. Unknown or absent `kind` falls through to the previous raw JSON `<pre>`, so renderers can be added one at a time without breaking anything in between.
- `slice_current_turn()` in `app/agentic_ai/serialization.py`.

### Changed
- **`POST /chat` returns only the current turn's tool executions.** The agent runs on a checkpointer, so `invoke` returns the entire accumulated thread; `extract_tool_executions` was flattening all of it onto the newest message. The third reply in a conversation claimed "7 sources consulted" when the agent had called one tool — and a refresh showed it correctly, because `GET /conversations/{id}` distributes per-turn. Two renderings of the same conversation, which is the exact invariant this module exists to prevent.
- **Serialization parses the untruncated content.** `_truncate` cuts at 600 chars for the agent's context budget (Rule 4); the browser has no such constraint. `result` keeps the cut string for the raw view, `data` carries the full parsed payload. Parsing the truncated value would have failed on every result over the cap, since a string sliced mid-JSON is not valid JSON.
- **Writes and reads render differently.** A write is the answer — it renders as an open card above the reply. A read is evidence — it stays a collapsed row under "sources consulted". Previously a `create_task` that mutated Postgres looked identical to a `query_tasks` that read it.
- `query_tasks` returns `{kind, count, items}` rather than a bare list; its error path returns `{"error": ...}` rather than `[{"error": ...}]`.

### Notes
- **Renderers key on `kind`, never on `ok`.** These tools catch their own exceptions and return `{"error": ...}`, so a failed call still arrives with LangChain `status == "success"` and shows a ✓. The error path carries no `kind`, falls to the raw view, and shows the error — which is the behavior wanted, but `ok` is not a trustworthy signal here.
- Only `create_founder_task_tools` was tagged. `list_employees` is shared by the chat, cron, and transcript entry points and `search_memory` has a degraded-path shape; neither has a renderer in this slice and both already fall through to raw JSON.
- "View in tasks" links to `/tasks`, not `/tasks/{id}` — no per-task route exists.

### Known issues — surfaced by this work, not addressed here
- **Founder chat is not read-only.** `create_founder_task_tools` returns `create_task`, `update_task`, `approve_task`, and `reject_task`. `create_task` calls `create_manual`, producing an **approved** task, while Architecture Rule 1 says every AI-produced task lands in `pending_approval`. The chat composer footer meanwhile tells the founder "Sentinel reads your data but never writes without approval." Either the tool set, the rule, or the footer is wrong; left as a product decision.

## [0.10.0] - 2026-09-01

### Added
- **HydraDB knowledge layer** — the "remember" step of extract → approve → delegate → chase → collect → remember. `app/knowledge/store.py` wraps the HydraDB v2 SDK behind a `KnowledgeStore` protocol, so the vendor stays swappable (the README keeps pgvector as a latency fallback).
- **`remember_fact`** (transcript entry only) — the extractor now records decisions, facts, and context alongside the tasks it already creates. `source_quote` and `speaker` are **required parameters**: an agent cannot record its own inference as a company fact without a person's words to point at. Rule 6 applied to knowledge.
- **`search_memory`** (founder chat only) — read-only recall over settled history, with optional `subject` scoping and `as_of` for point-in-time questions. Returns statements with speaker, verbatim quote, and source meeting so answers cite rather than assert (Rule 4 summaries).
- Per-company HydraDB database provisioning, persisted to the existing `companies.hydra_tenant_id`. Runs at signup **and lazily on the write path**, so companies created before this feature pick up memory on their next meeting without re-onboarding.
- Meeting title and date now flow from `meeting_service` through the extractor into each stored fact, which is what makes temporal questions answerable.
- `recorded_at` accepted on `POST /meetings/text` and threaded to the `Meeting` row. Without it a transcript uploaded weeks after the meeting stamps every extracted fact with the *upload* date — and since temporal recall reasons over exactly those dates, back-dated uploads would answer "what did we decide in March" wrongly. Defaults to now when omitted.
- `hydradb-sdk>=2,<3` dependency; `HYDRA_DB_API_KEY` and `HYDRA_TIMEOUT_SECONDS` settings (**still to be documented in `backend/.env.example`** — that file is outside write permissions here). An unset key disables the knowledge tools rather than failing startup — the system runs without memory, just with thinner answers.

### Changed
- Extractor and founder chat prompts carry explicit trigger rules, including the negative ones: never record your own analysis or summaries, and never fill a gap with a guess when recall returns nothing.
- Employee chat, cron, and every existing Postgres task tool are unchanged. Verified by asserting the tool set per entry point.

### Notes — verified against the live API, not the documentation
These cost real debugging time and are recorded so they are not rediscovered:
- **`source_type` is reserved.** Rejected as a custom schema property *and* as an `additional_metadata` key. The source category is carried as `origin` instead.
- **`app_knowledge` stores the serialized item as the chunk body**, so recall hands the agent raw JSON. Facts are ingested through the `documents` path, which indexes the prose itself.
- **`collection` is required on `context.status`.** Omitting it reports `FILE_NOT_FOUND` for sources that exist and are indexing normally — which reads as a failed ingest when it is nothing of the kind.
- **Indexing takes ~3 minutes** to reach `completed` (it passes through a `graph_creation` stage). A fact is not searchable immediately after a meeting is processed. Demos must pre-ingest.
- **Metadata filters genuinely work** — a filter on an unmatched value returns zero results rather than silently ignoring the constraint.
- **Recall latency: ~1.6s plain, ~2.5s filtered, ~3.6–6.2s with `temporal_now`.** Acceptable on the request path next to an LLM turn; the README's >5s background-enrichment threshold is only crossed by temporal queries.
- **Idempotency (Rule 3) is handled by the API**: the document `id` is the upsert key, so re-running extraction on the same meeting overwrites instead of duplicating.
- The SDK exposes `temporal_now`, `temporal_reasoning`, and `recency_bias` on `query`, and returns temporal facts with `event_start`/`event_end`/`status` — none of which appear in the prose docs. This is why no Postgres fact ledger was built.


## [0.9.0] - 2026-08-31

### Fixed
- **Signup returned 400.** The frontend posted `{company_name, founder_name, email, password}` while `SignupRequest` requires `{company_name, industry, company_description, founder_email, founder_password, founder_full_name}`. Because `RequestValidationError` is mapped to 400 (not 422), this surfaced as a bare "Registration failed" with no cause. Payload corrected and the two missing required fields added to the form.
- **Login stored a null user.** `useAuthStore.login` destructured `user` from `TokenResponse`, which carries only a token — leaving `isAuthenticated: true` with `user === null`. Both login and signup now store the token and load the user from `/auth/me`; signup consumes the token it is already issued instead of a second login round trip.
- **Role and task-status casing mismatched the API.** The frontend compared `'FOUNDER'`/`'EMPLOYEE'` and `'COMPLETED'` against the API's `founder`/`employee` and `done`, so role routing and every status branch silently failed. Types and all comparison sites realigned to the wire values.
- **List endpoints crashed their pages.** Approvals, tasks, my-tasks, and employees were assigned `res.data` directly, but those routes answer with an `{items, total}` envelope — producing `approvals.map is not a function`. All four now read `.items`.
- **Agent replies never rendered.** The chat store read `res.data.response`; the field is `reply`. Messages arrived and were discarded.
- **Employee logins could not be created.** `provisionLogin` sent only `{email}` while `EmployeeLoginCreate` also requires a password (min 8). A password field was added to the provisioning form.
- **Employee title and bulk import were silently dropped.** The roster sent `title` and `{title, manager_name}` where the contracts are `role_title` and `{role_title, manager}`; the values were discarded without error. The manager column read a `manager_name` field the API never returns, and is now resolved from `manager_id` against the loaded roster.
- Hardcoded "ACME Corp" in the header replaced with the tenant's real company name.
- Errors are surfaced from the API's `{error, code}` envelope instead of a fixed guess ("Email may already be registered") that hid the real cause.

### Added
- **Multi-session chat.** `GET /conversations` was already present but unused; the UI now lists threads, starts new ones, switches between them, and deletes them via a new `DELETE /conversations/{id}` (owner-scoped — another user's thread reads as absent, not forbidden).
- **Tool executions on the wire.** `ChatResponse` and the rehydration endpoint now carry `tool_executions` (`id`, `tool`, `args`, `result`, `ok`, `truncated`), paired by `tool_call_id` in `app/agentic_ai/serialization.py`. Args pass through the audit layer's redaction, and results are truncated server-side per Rule 4.
- `GET /conversations/{id}` gained a response model and returns turns in the same shape as a live reply, so a reloaded thread renders identically — tool cards included.
- **`ToolExecutionPanel`** — collapsible per-turn cards showing each tool, its arguments, and its pretty-printed result, so an answer can be verified rather than trusted.
- **Dedicated `/chat` page** replacing the side drawer: a ChatGPT-style layout with a thread list, suggested prompts, Enter-to-send, and streaming-style thinking state. `ChatDrawer` removed.
- `has_login` added to `EmployeeSummary` so the roster can render credential state without a per-row detail fetch.
- **`BrandMark`** — an outlined shield-and-pulse mark replacing the generic `Sparkles` star across the header, auth pages, and empty states, per the design system's Cyan Signal icon-stroke role.
- `tailwindcss-animate` wired into the Tailwind config: `animate-in` classes were already used in several components but generated no CSS.

### Changed
- **Mobile responsive throughout.** The sidebar is an off-canvas drawer with a scrim below `md` and a sticky column above it, and its nav scrolls independently so a long list never pushes the cron card out of view. The header collapses progressively, the chat thread list becomes an overlay below `lg`, and page padding, the task filter row, the roster forms, the task modal, and the employee portal all adapt down to 375px. Verified with no horizontal overflow at mobile width.


## [0.7.0] - 2026-08-30
### Added
- Sentinel Agent Layer in `app/agentic_ai/` powered by DeepAgents (`create_deep_agent` / LangGraph ReAct runtime) and configured for Qwen 3.7 (`qwen3.7-max` on Alibaba Cloud MaaS compatible-mode endpoint).
- Modular on-demand persona prompt rendering per invocation type: Founder Chat, Employee Chat, Cron Follow-up, and Transcript Extractor.
- Role-scoped dynamic tool dispatch with strict function closure isolation and concurrency-safe `SessionLocal()` instances.
- Conversation thread persistence with `PostgresSaver` checkpointer and thread tenant/user isolation (`GET /api/v1/conversations/{id}`).
- Chat endpoint (`POST /api/v1/chat`) supporting conversational memory, tool calling, and role scoping.
- Meeting transcript extraction endpoint (`POST /api/v1/knowledge/transcripts`) with automated action item extraction, confidence scoring, and auto-approve threshold gate.
- Cron follow-up runner and admin endpoint (`POST /api/v1/admin/run-followup`) with daily APScheduler lifecycle.
- Isolated audit logging layer writing tool invocations to `AuditLog` with token redaction.
- `auto_approve_threshold` column on `Company` model (`Float`, nullable=False, server_default="1.0") and Alembic migration.
- Comprehensive end-to-end verification suite in `scripts/verify.py` covering tool isolation, transcript extraction, injection defense, role-based chat, admin follow-up, and audit trails (117/117 checks passing).

### Added
- Employee user accounts and login management endpoints (`POST`, `PATCH`, `DELETE` on `/employees/{id}/login`).
- Employee task surface (`GET /me/tasks`, `GET /me/tasks/{task_id}`, `POST /me/tasks/{task_id}/status`).
- `require_employee`, `EmployeeUser`, and `CurrentEmployeeId` FastAPI dependencies in `app.dependencies`.
- `EmployeeStatusUpdateCreate`, `EmployeeLoginCreate`, `EmployeeLoginUpdate`, and `EmployeeLoginRead` Pydantic schemas.
- `TaskService.get_owned_or_404` helper for task ownership verification.
### Changed
- `users.email` constraint updated to globally unique (`uq_users_email`), replacing `uq_users_company_email`.
- `users.employee_id` unique constraint added (`uq_users_employee_id`) enforcing a 1:1 link with `Employee`.
- Automatic email normalization on write (`value.lower().strip()`) via `@validates("email")` on `User`.
- `EmployeeService.delete` updated to delete associated employee `User` rows (and block deletion of founder-linked employees).

## [0.5.0] - 2026-08-30
### Added
- `POST /auth/signup` endpoint to allow founders to self-provision a company tenant and founder account.
- `industry` column on `Company` model (`String(200)`, nullable) and Alembic migration `d1f89a2b5e01_add_company_industry.py`.
- Exposed `industry` on `CompanyRead`, `CompanyUpdate`, and `CompanySummary` schemas.
- `SignupRequest` schema in `app.schemas.auth` with `company_description` mapped to `persona_config.company_context`.

## [0.4.0] - 2026-08-29
### Added
- Employee endpoints (org chart, Slack id mapping, "what is Mark working on"), the approval queue with approve/edit/reject/bulk-approve, company persona config, and structured bulk onboarding. 24 routes total.
- `TaskService.create_pending()` — the extractor's write path. No promotion, so the task falls to the `pending_approval` default and waits. Use this for anything an agent creates; `create_manual` is founder-only.
- `TenantService` base class holding the "an id in a request body must be resolved through a tenant-scoped repository" guard. Inherit it rather than re-implementing the check.
### Notes
- Editing an approval does **not** approve it — state becomes `edited` and the task stays in the queue. The queue therefore filters on undecided (`pending` + `edited`), not on `pending` alone. Getting this wrong makes edited tasks silently vanish from the founder's inbox.
- Deleting an employee who owns open tasks is a 409 listing them. The FK would set the owner to NULL, and an owner-less task can never be chased, so it would drop out of the loop unnoticed.
- `GET /company` never returns `slack_bot_token` — only a `slack_connected` boolean. Keep it that way when the OAuth flow lands.
- `verify.py` is at 74 checks, all green. Run it after touching the repository or service layers.

## [0.3.0] - 2026-08-29
### Added
- Task endpoints: create, list with filters, detail, patch, status update, delete. Lists return thin summaries and only the detail route returns everything — the agent tools wrap these same shapes later, where a fat return blows the context.
- `TaskService` and a new `services/` layer. Business rules live there; routes only validate and delegate.
### Fixed
- The seeded founder could never log in: `email-validator` rejects `.test` as a reserved domain, so login failed validation before reaching the password check. Demo accounts now use `.example`. Watch for this in any new seed data.
- `scripts/verify.py` now passes — 41 checks covering schema rules, tenant isolation, auth, and task endpoints. Run it after touching the repository layer.
### Notes
- A founder-created task is approved on creation but still writes a real approval row naming the decider, so rule 1 holds and the audit trail says who decided. The extractor will skip that promotion and fall to the `pending_approval` default.
- `owner_employee_id` is validated through the tenant-scoped employee repository — the FK alone only checks the employee exists, not that it is yours.

## [0.2.0] - 2026-08-29
### Added
- Backend foundation: seven models, Alembic migration, tenant-scoped repositories, and JWT auth (`/auth/login`, `/auth/me`). Tenancy is enforced in `TenantScopedRepository`, not per query — never write a query outside a repository, or the `company_id` filter is lost.
- `.gitignore` — the repo had none and `.env` holds the live Neon string, so it was one `git add .` from being published.
### Changed
- The initial migration was hand-fixed after autogenerate: enum types are now created and dropped explicitly, and enums store lowercase values so `tasks.status` actually matches its `pending_approval` default. Re-autogenerating will reintroduce both bugs — hand-check enums in any future migration.
### Known issues
- `backend/scripts/verify.py` is unfinished and does not pass: the expected `IntegrityError` rolls back its own setup rows, so it needs a savepoint. The migration cycle, seed, and Neon connection were all verified manually and are good.

## [0.1.0] - 2026-08-29
### Added
- README.md — full project framing: the operational/knowledge memory split, build order, rules, and known risks. Read this before proposing architecture changes; the Postgres-vs-HydraDB boundary is load-bearing, not a preference.
### Changed
- Deleted the `test` branch (local + remote) after cherry-picking its CLAUDE.md link fix onto `main`. Work now happens on `database-setup`.
