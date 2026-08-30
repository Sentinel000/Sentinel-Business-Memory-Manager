# Changelog

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
