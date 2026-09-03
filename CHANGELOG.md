# Changelog

## [0.15.1] - 2026-09-03

### Changed
- Rewrote the README to reflect the shipped product (two agents — Extractor + Chat — plus a deterministic chase cycle and an in-product employee task view); the old copy still described Slack DMs and a follow-up cron agent removed in v0.14.0, and wrongly claimed no application code existed.

## [0.15.0] - 2026-09-02

### Added
- Replaced flat signup form with a 4-step onboarding wizard featuring step validation, industry chips, guided templates, and animated deployment feedback.
- Split Settings into dedicated Sentinel Persona and Employee Roster tabs, with a centered showcase hero, Business Companion badge, and realistic 3D shaded animated Sentinel bot.
- Redesigned Briefings UI into an interactive card grid that opens a full-detail inspection modal with metrics and all 4 analytical sections.
- Integrated Variation 3 (Continuous Memory 'S' Loop) as the official brandmark across application headers, auth flows, and browser metadata.

### Changed
- Reorganized frontend components into domain folders with barrel exports (`ui`, `layout`, `approvals`, `tasks`, `meetings`, `chat`, `knowledge`, `settings`, `employee`) to improve modularity and avoid flat folder sprawl.

### Removed
- Removed legacy Slack mapping column from employee roster table and deleted Daily Wakeup Cron status card from dashboard sidebar.

## [0.14.1] - 2026-09-02

### Fixed
- **The settings form was saving nothing.** `PersonaConfigForm` PATCHed `persona_instructions`, `escalation_window_hours`, and `auto_approve_threshold` — none of which exist in `CompanyUpdate`. Pydantic ignored them, so the escalation window and approval threshold controls had silently done nothing since they were built, and the page header advertised "escalation parameters" that could not be set. Field names corrected, and the form now seeds from the server rather than rendering its own defaults over the founder's real configuration.
- `auto_approve_threshold` and `max_chases` are now in `CompanyRead` and `CompanyUpdate`. Bounded server-side: `max_chases` 1–5, threshold 0.5–1.0, cadence 1–30.

### Added
- **Follow-up controls in settings**, with an `InfoTip` on each — cadence, chase limit, and auto-approve threshold. Tips explain the behaviour, not the field: why the limit is low, what happens at 100% threshold, that an overdue task is chased regardless of cadence.
- **The settings restated as behaviour.** Two numbers mean little alone, so the card renders "Sentinel will send up to 2 reminders, 3 days apart, then hand the task back to you", plus the derived worst case — how long a commitment can sit unanswered before it reaches the founder. This is the only place in the product where the ladder is explained.
- `InfoTip` is toggled on click as well as hover and is keyboard-focusable, wired via `aria-describedby` — a tooltip that only opens on hover is invisible to half the people who need it.

### Notes
- **Lowering the chase limit now reconciles.** `escalated` is normally set inside the chase cycle at the moment budget runs out; lowering the limit exhausts tasks retroactively, and they would match neither the chase query nor the briefing's decision section — stranded in Quiet, never chased and never surfaced. A single `UPDATE` on save hands them back. Raising the limit deliberately does not un-escalate: the founder has already been asked to decide.
- No reset-to-defaults control. The defaults stand on their own, and it is one more thing to explain.
- `scripts/verify_settings.py` — 17 checks, including that the settings persist (they did not before), bounds are enforced, and employees are refused.

## [0.14.0] - 2026-09-02

### Changed — Slack is no longer the delivery channel
- **Chasing moved into the product.** Reminders land on the employee's own `/me` page instead of a Slack DM. The consequence is stated rather than hidden: there is no push, so an unread reminder is indistinguishable from an employee who has not logged in. Sentinel no longer promises to make someone respond — it guarantees the founder knows who has not.
- **The cron agent is gone.** `agents/followup.py`, the `cron` factory entry, and its Slack tools are removed, so nothing in the codebase can send a DM. `POST /admin/run-followup` becomes `POST /admin/run-chase`.
- **`escalated` is repurposed, not replaced.** It meant "the manager was DM'd"; it now means "handed back to the founder", who is the only escalation path left.

### Added — the chase ladder
- `companies.max_chases` (default 2) and `tasks.chase_count`. The cadence reuses the existing `escalation_after_days` rather than adding a second interval that would have to be kept in agreement with it.
- **Silence is the clock; a deadline only brings it forward.** One SQL clause covers dated and undated tasks — undated commitments are precisely the ones that rot unnoticed, and a trigger that required a deadline would never chase them.
- **Blocked is never chased.** The owner already answered, and the answer was "I am stuck". Nudging them is what trains people to ignore the tool, so a blocker goes straight to the founder. Unowned tasks are never chased either — there is nobody to chase.
- **The ladder terminates.** Two reminders, then chasing stops and the task is handed back. The cap exists to protect the briefing: unbounded chasing means unbounded stale tasks, which is how a daily report stops being read.
- **Only a founder action grants a fresh budget** — unblocking, reassigning, or moving the deadline, and only when the value actually changed, so fixing a typo does not restart the ladder. An employee response clears `escalated` but never mints new chases, so "mark blocked to buy time" cannot game the counter.

### Added — founder briefings
- **`/briefings` tab and `GET`/`POST`/`DELETE /api/v1/reports`.** Replaces the cron digest, which was generated daily and *discarded* — `daily_wake_up_job` called `run_cron_followup()` without assigning its return value, so the "one morning digest" user story had no implementation despite the agent doing the work every morning.
- **No model.** Every figure is computed in SQL. "What is overdue" is a query, not a retrieval (Rule 2), and a briefing that miscounts is worse than no briefing.
- **Four sections, five items each**, ordered by what a founder can act on: needs-decision, slipping, moved, quiet. The cap is the design — a briefing that fits one screen gets read and one that does not, does not.
- **Movement is the point.** The `moved` section is measured against the *previous* briefing, so nothing is counted twice and nothing falls through the gap between runs. Agent-written reminders are excluded: our own nudges are not news.
- **Every item cites its source quote** (Rule 6), so a claim can be checked rather than trusted.
- **Empty states are explicit text, never a blank box.** "Nothing slipped" is a real, reassuring answer; an empty section reads as a broken feature.
- **On demand, never scheduled.** Generation is idempotent on `(company_id, report_date)` — regenerating updates the day's row, so clicking twice gives one briefing rather than two versions of the same morning with no way to tell which is current. `generated_at` is kept separate from `report_date` so the UI can say "Today · built 2:14pm".

### Fixed
- **The scheduler shared one `SessionLocal()` across every tenant.** A failed transaction in the first company left the session unusable and silently disabled every tenant after it — noise when the job only sent messages, a correctness bug now that it writes to `tasks`. Session per company.
- **Reports are deliberately not wired into the scheduler.** That separation is the whole reason the regenerate button is safe: a button that also re-chased the team could not be pressed twice.

### Notes
- **Caught during verification:** the chase trigger's overdue branch originally bypassed the cadence, so an overdue task matched on *every* run and burned its entire budget in one afternoon — the deadline stays passed, so the clause never stopped being true. The rate limit now applies to both paths.
- `TaskStatus.OVERDUE` is confirmed dead — nothing writes it, and overdue is derived from `deadline < now()` so it cannot go stale. Left dormant rather than removed.
- `scripts/verify_chase.py` (25 checks), `scripts/verify_report.py` (24), `scripts/verify_reports_api.py` (22) — all passing against the live database.

### Known issues — surfaced, not fixed
- `BackgroundScheduler` is in-process, so each uvicorn worker starts its own and the job fires once per worker. Safe at one worker; needs a lock or external trigger before scaling out.
- The daily job still runs for every company, including ~12 test rows (`Test Acme Co`, `Acme QA`, `verify-a-*`) left by earlier scripts. Real work for tenants that were never meant to exist.
- `backend/.env.example` documents `HYDRA_API_KEY`, but config reads `HYDRA_DB_API_KEY`. Anyone following the example silently gets knowledge memory disabled.
- `slack_tools.py` and `prompts/cron.py` remain on disk, exported but unreachable. Kept in case Slack returns; dead exports invite accidental re-wiring.

## [0.13.0] - 2026-09-01

### Added
- **Knowledge Panel — the company knowledge graph, visualised.** New founder-only tab (`/knowledge`) rendering the entities HydraDB extracted from meetings and the relations between them, as a `d3-force` layout. Closes the "see the knowledge graph grow over time" user story, which had no implementation.
  - `GET /api/v1/knowledge/graph` (`app/api/v1/knowledge.py`). Founder-scoped, matching `create_knowledge_read_tools` — employees live in Slack and get a 403.
  - `HydraKnowledgeStore.graph_relations()` and `corpus_size()`, both added to the `KnowledgeStore` Protocol. The route speaks only in our own dataclasses; the vendor client stays behind the seam, as the store's docstring requires.
  - `d3-force` runs the simulation only — it mutates `{x,y,vx,vy}` and draws nothing. The SVG, pan/zoom, and node drag are hand-rolled against pointer events rather than pulling in `d3-drag` and `d3-zoom`. Nodes are cloned before the simulation touches them, since the originals belong to the Zustand store.

### Notes — shaped by what the live graph actually contains
- **Parallel evidence is collapsed into one edge.** The API returns a triplet group per evidencing chunk, so the same pair arrives repeatedly (one pair appeared twice). Drawing each separately renders a denser graph than the data supports. Deduplicated by `(source, target, predicate)`, with every evidence entry kept and shown in the detail panel — Rule 6 applied to the graph: an edge you can check, not one to take on trust.
- **`confidence` is deliberately not encoded.** Every edge on live data scored exactly `0.80`. It is a placeholder, and mapping a constant to stroke weight or opacity would draw a signal that does not exist.
- **Provenance edges are flagged and hidden by default.** `build_statement_text` appends "(speaker, meeting title)" so a chunk read cold carries its attribution — and the graph builder reads that parenthetical as authorship. On live data these `authored` edges were 4 of 10, turning the graph into an org chart of who spoke rather than a map of what the company knows. Flagged server-side (`is_provenance`), hidden behind a "Show who said it" toggle. Hiding them also drops entities they were the only reason to draw, so no orphan nodes are left behind.
- **`is_truncated` is surfaced in the UI.** A partial force layout is visually indistinguishable from a complete one, which is the worst failure this panel could have.
- **Entity types arrive UPPERCASE** (`PERSON`, `ORGANIZATION`, `CONCEPT`, `DOCUMENT`) despite the SDK documenting lowercase. Normalised once in the store; otherwise every node silently falls to the default colour.
- **`canonical_predicate` is not canonical.** `set price for` and `has pricing` are the same relation under two labels, and `raw_predicate` never differed from `canonical_predicate` on any edge — normalisation is effectively a pass-through. Predicates are treated as display-only; there is no predicate filter.
- **Unavailable and empty are different answers.** Unconfigured or unreachable memory returns `available: false` with a note; an empty graph returns `available: true` with `fact_count`, which distinguishes "nothing recorded" from "recorded, graph still building" (~4 minutes). Neither is an error, and neither 500s.

### Added — tooling
- `scripts/probe_knowledge.py`: read-only inspection of a live HydraDB account — infra status, row counts, **metadata schema drift**, per-source indexing status, and the graph both database-wide and scoped to one fact.

### Known issues — surfaced, not fixed
- **`sentinel_smoke_test` has a broken metadata schema in the live account**: it declares only `subject`, missing `fact_type`, `speaker`, and `source_ref`. An undeclared match field does not error — the filter is silently ignored and returns unscoped results that look scoped. The two real company databases are correct. The "startup assertion that the declared metadata schema matches expectations" task remains open, and this is evidence it should not stay deferred.
- `indexing_state()` is still never called on the read path, so a founder querying just after upload is told "nothing recorded yet" when the truth is "not indexed yet". The Knowledge Panel works around this with `fact_count`; `search_memory` does not.
- `relations(id=...)` takes a `fact_<sha>` id, not a meeting id, so a per-meeting graph view needs fan-out and merge. Not attempted; the panel is database-wide.

## [0.12.0] - 2026-09-01

### Fixed
- **Extracted tasks never reached the approval queue.** `create_extracted_task` constructed a `Task` row directly and committed it. The approval queue reads from the `approvals` table, so a task sitting at `pending_approval` with no approval row was invisible to the founder it was waiting on — the extract → **approve** → delegate loop was broken at step two. Now routed through `TaskService.create_pending()`, which writes both rows. The auto-approve path above the confidence threshold promotes the approval row to `approved` with a null decider, representing a decision the founder made in advance by setting the threshold, rather than a task that appears pre-blessed.
  - `create_pending()` flushes but does not commit; the tool now commits explicitly. Without it the session block exits, the transaction rolls back, and the tool reports success on a task that does not exist.
  - `source_quote` is now **required** rather than silently optional. Rule 6 applies to anything the AI produces; the tool rejects the call with instructions, the way it already rejects a name in `owner_employee_id`.
  - Idempotency key is now derived from `source_ref` + title instead of a fresh `uuid4`, so re-running extraction over a meeting returns the existing task instead of duplicating it — which is what `create_pending`'s contract already promised (Rule 3).
- **Markdown in chat replies rendered as literal asterisks.** `MarkdownText` renders `**bold**`, `*italic*`, `` `code` ``, bullets, and numbered lists as React elements — never `dangerouslySetInnerHTML`, since the input is model output. Unrecognised syntax falls through as text.

### Changed
- **Chat shows one source per turn, not all of them.** A turn that queries three times to narrow an answer produced one answer; three near-identical rows read as noise. Writes are deliberately exempt from the collapse: a model that verifies with a read *after* creating something would otherwise hide the mutation behind the trailing query. Every write renders; only the last read does, with a count of what was hidden.

### Added
- **Meeting deletion, cascading to HydraDB.** `DELETE /meetings/{id}` removes the meeting and every fact extracted from it. `GET /meetings/{id}/delete-preview` reports the counts first, so the confirmation dialog asks about the real consequence rather than "delete this meeting?".
  - `HydraKnowledgeStore.source_fact_ids()` (paginated, read-only) and `forget_source()`.
  - **`forget_source` raises instead of degrading**, unlike every other method in the class. Recall is enrichment over Postgres truth so a failed read can return nothing safely; a failed delete cannot, because the caller is about to remove the Postgres row. Facts go first, meeting second — an aborted delete leaves both.
  - Extracted **tasks are not deleted**. They may be live commitments assigned to real people; their `source_ref` is left dangling, which is visible, rather than removing work as a side effect. The dialog says so.

### Notes
- **A meeting's facts are addressed by title, not id** (`source_ref = f"Meeting: {title}"`), so two meetings sharing a title share one knowledge address and deleting either would wipe both. Delete refuses with a 409 when the title is not unique, and the dialog explains why. The underlying title-based linkage is unchanged — `get_meeting_tasks` matches the same way — and is worth revisiting.
- `fact_count` is `null`, not `0`, when the knowledge store cannot be reached, so the founder never confirms a permanent delete against a count that was really a failed lookup.
- Meetings already had their own dashboard tab, list page, and detail page; only deletion was missing.

### Notes — verified against the live HydraDB API, not the documentation
- **A refused delete returns HTTP 200 with a success envelope.** The refusal is in the payload: `deleted_count: 0`, `success: false`, and a per-id `error`. The first implementation of `forget_source` treated "no exception raised" as success and reported 3 facts deleted when all 3 were still present — the precise silent failure the method was written to prevent. It now reads `results[].deleted` and raises when any id failed.
- **A fact still indexing cannot be deleted**: `"Source is still processing; retry deletion after ingestion completes"`. Measured at ~225s (~4 minutes) from ingest to `completed` status, passing through a `graph_creation` stage. So a meeting deleted shortly after processing will refuse — `delete_meeting` translates this to a 409 telling the founder to retry, and leaves the meeting row intact rather than stranding facts with no handle to find them by.
- Newly ingested facts are briefly invisible to `context.list` (seconds) before appearing with status `graph_creation`.
- The metadata filter on `source_ref` is exact and complete — filtered counts matched an unfiltered listing of the whole database (1 + 3 = 4).

### Known issues — surfaced, not fixed
- **Four of the six founder chat task tools cannot succeed.** `TaskService` has no `patch`, `approve_pending`, or `reject_pending` (it has `update`), and `create_manual` is called as `create_manual(payload, user_id=...)` against a signature of `(payload, *, created_by: User, ...)` that returns a tuple. All four raise, are swallowed by the tool's `except`, and return `{"error": ...}` — while rendering a green ✓, because these tools catch their own exceptions and LangChain still reports `status == "success"`. The `task_created`/`task_updated`/`task_approved`/`task_rejected` renderers are therefore unreachable from chat today.
- Founder chat writes at all, and `create_manual` produces an **approved** task, while Architecture Rule 1 says every AI-produced task lands in `pending_approval` — and the chat footer promises the founder it "never writes without approval."

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
