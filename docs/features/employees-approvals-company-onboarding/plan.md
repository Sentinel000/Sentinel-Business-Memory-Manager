# Employees, Approvals, Company & Onboarding endpoints

## Context

Auth, tenancy, and task endpoints are done — `ed4b4c3` on `tasks-and-slack`, with
`scripts/verify.py` green at 41 checks. What is missing is everything *around* a task.

Three concrete gaps:

1. **No employee endpoints.** The task-creation UI has no owner dropdown, and Slack's
   member-list pull in the next step has nowhere to write `slack_user_id`.
2. **No approval endpoints.** Nothing can move a task out of `pending_approval`. The
   moment the extractor lands, every task it writes is stuck — and the approve/edit/
   reject beat is the demo's whole trust story.
3. **No company/persona endpoints.** `persona_config` and `escalation_after_days` are
   columns nobody can read or change.

**Out of scope, explicitly:** digest and knowledge endpoints. Also no Slack, no OAuth,
no agents — the LLM half of onboarding (paste-a-paragraph) comes later; only the
structured half is built here.

**Outcome:** a founder can manage their org chart, work the approval queue, and
configure the assistant. After this, the only thing between here and the demo loop is
Slack.

---

## Decisions

**Every task gets an approval row.** Previously only founder-created tasks did. Making
it universal means the queue is one query against `approvals`, the audit trail is
uniform, and `GET /approvals` does not have to union two different notions of "waiting".
Manual creation writes `state=approved`; the extractor writes `state=pending`.

**Edit saves without approving.** `POST /approvals/{id}/edit` applies changes and leaves
the task undecided — the decision stays a separate, explicit act. `approve` is its own
call. The original values are captured in `approvals.edited_payload` as a before/after
pair, so the audit trail shows what the AI proposed *and* what the founder changed it
to. That record is also the signal for whether extraction is improving over time.

**The queue filters on undecided, not on pending.** Because editing sets
`state=edited`, a queue filtered on `pending` alone would make an edited task silently
vanish from the founder's inbox. `UNDECIDED_STATES = (PENDING, EDITED)` is the default
filter.

**Deleting an employee who owns open tasks is blocked** — 409, listing the tasks.
The FK is `ON DELETE SET NULL`, so deleting would leave the tasks alive with no owner,
and an owner-less task cannot be chased — it drops out of the loop unnoticed. Reassign
or close first. Employees with no open tasks delete normally.

**`thread_id` stays unused.** The column exists for LangGraph interrupt resume.
Approving today just writes state; when the extractor arrives, approve will also resume
the paused run. Nothing here should make that harder.

---

## Endpoints

All founder-only (`require_founder`), all tenant-scoped through repositories.

### Employees — `app/api/v1/employees.py`

```
GET    /employees            list; filters: q, unmapped (no slack_user_id), manager_id
POST   /employees            create
GET    /employees/{id}       detail + manager + direct reports
PATCH  /employees/{id}       edit, incl. manager_id and slack_user_id
DELETE /employees/{id}       409 if they own open tasks
GET    /employees/{id}/tasks task summaries — "what is Mark working on"
```

`GET /employees` returns **all** matches for a name query, never a best guess.
`EmployeeRepository.find_by_name()` returns a sequence deliberately — two people called
Mark is the exact case that must surface as ambiguous rather than resolve silently.

### Approvals — `app/api/v1/approvals.py`

```
GET   /approvals                   queue; filter by state, default undecided
GET   /approvals/{id}              one, with the full task incl. source quote
POST  /approvals/{id}/approve      → task.status = approved
POST  /approvals/{id}/edit         apply changes, stay undecided
POST  /approvals/{id}/reject       → task.status = rejected, reason recorded
POST  /approvals/bulk-approve      body: {approval_ids: [...]}
```

Every decision sets `decided_by_user_id` and `decided_at`. Deciding an already-decided
approval is a 409, not a silent re-approve. Bulk approve reports unknown or
already-decided ids in `skipped` rather than failing the batch.

### Company — `app/api/v1/company.py`

```
GET   /company    name, persona_config, escalation_after_days, slack connection status
PATCH /company    update the above
```

`slack_bot_token` is **never returned** — a `slack_connected` boolean instead. A bot
token in a JSON response is a credential sitting in a browser's memory.

`persona_config` gets a real Pydantic model rather than a free `dict`:
`assistant_name`, `tone`, `company_context`, `glossary`. **`company_context` is capped
at 4000 chars.** It is founder-supplied text bound for a system prompt; capping it and
treating it as data is what keeps it a bounded input rather than an open channel into
the model. It must never be able to relax the `pending_approval` gate.

### Onboarding — `app/api/v1/onboarding.py`

Structured half only.

```
POST /onboarding/employees/bulk   accept a list, resolve manager names to ids
GET  /onboarding/status           what is still unconfigured
```

`bulk` takes manager references **by name** (`{"name": "Mark", "manager": "Sarah"}`),
because that is the shape the LLM will emit in the paste-a-paragraph step. Two passes:
create everyone, then resolve managers — a paragraph naming Mark before Sarah must
still work. Unresolvable or ambiguous names come back as warnings rather than failing
the import; one typo should not cost the other twenty-four rows. An existing name is
skipped, not duplicated, so re-running an import is safe.

`status` reports: employee count, employees with/without a `slack_user_id`, Slack
connected, persona configured, has tasks. It is what the dashboard's setup checklist
renders. `employees_without_slack` is the operationally important one — those people
cannot be delegated to.

---

## Files

New:

```
backend/app/api/v1/employees.py   approvals.py   company.py   onboarding.py
backend/app/repositories/approval.py
backend/app/schemas/employee.py   approval.py   company.py   onboarding.py
backend/app/services/base.py      employee_service.py
                                  approval_service.py   onboarding_service.py
```

Modified:

```
backend/app/api/router.py              mount four routers
backend/app/dependencies.py            providers for the new services
backend/app/exceptions.py              add ConflictError (409) with a details payload
backend/app/services/task_service.py   create_pending() for the extractor path
backend/scripts/verify.py              extend
backend/scripts/seed.py                seed a pending task so the queue is not empty
```

---

## Reuse — do not rewrite

- **`TenantScopedRepository`** (`app/repositories/base.py`) — `ApprovalRepository`
  subclasses it. Build every query from `self._scoped()`.
- **`EmployeeRepository`** (`app/repositories/employee.py`) — already has
  `find_by_name`, `search_by_name`, `list_unmapped`, `get_many`,
  `find_by_slack_user_id`. The endpoints are thin wrappers; do not add duplicate query
  methods.
- **`TenantService`** (`app/services/base.py`) — holds `require_own_employee()`, the
  guard that an id arriving in a request body must be resolved through a tenant-scoped
  repository. `TaskService` was refactored onto it; every new service inherits it.
- **`TaskRepository.list_filtered()`** — reused for `/employees/{id}/tasks` with
  `owner_employee_id` set.
- **Exceptions** (`app/exceptions.py`) — raise `NotFoundError`, `ValidationError`,
  `ConflictError`. Never construct `HTTPException` directly.
- **Schema patterns** (`app/schemas/task.py`) — summary/detail split,
  `from_attributes`, `computed_field`. Mirrored in the new schemas.

---

## Security

**Every id in a request body must be validated through a tenant-scoped repository**,
because a foreign key only proves a row exists, not that it belongs to the caller:

- `manager_id` on employee create/patch
- `owner_employee_id` on approval edit
- `approval_id` — reached via the repository, so a foreign one is a 404, not a 403.
  403 would confirm the row exists.

**Manager cycles:** `manager_id` is a self-FK. Reject self-management, and walk the
manager chain before saving to reject a longer cycle. An escalation that loops would
recurse forever in the follow-up agent.

**Editing cannot smuggle in a decision** — `status` is stripped from an edit payload.

---

## Verification

`scripts/verify.py` — extended from 41 to 74 checks, all green.

**Employees**
- Create, patch, set a manager; detail returns manager and direct reports.
- `manager_id` from another company → 400.
- Self-management → 400; A→B→A → 400.
- `unmapped=true` returns only employees with no `slack_user_id`.
- A name query matching two people returns **both**, not one.
- Company B sees none of company A's employees.
- Delete an employee owning an open task → 409 with the task listed. Close the task,
  delete succeeds.

**Approvals**
- An agent-created task lands `pending_approval` and appears in the queue.
- Approved tasks do not sit in the queue.
- Detail carries the verbatim source quote.
- Approve → `task.status=approved`, `decided_by_user_id` and `decided_at` set.
- Edit → changes applied, task **still undecided**, before/after in `edited_payload`,
  and it stays in the queue.
- Reject → `task.status=rejected`, reason stored.
- Approving twice → 409.
- Another company's approval id → 404, not 403.
- Bulk approve moves the good ones and reports the bad.

**Company**
- `PATCH` updates persona and escalation days.
- `GET` never contains `slack_bot_token`; `slack_connected` reflects it.
- `company_context` over the cap → 400.

**Onboarding**
- Bulk import creates employees and links a manager named *later* in the list.
- An unresolvable manager name lands in warnings, and the rest still import.
- Re-importing an existing name skips rather than duplicates.
- `status` reflects what is configured.

**Manual smoke** — `uvicorn app.main:app --reload`, log in at `/docs` as
`sarah@northwind.example` / `sentinel-demo-2026`, walk the org chart and the queue:
seeded pending task → read its source quote → approve → task goes `approved`, queue
drops to zero.
