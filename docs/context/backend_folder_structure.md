```
app/
├── __init__.py
├── main.py                      # FastAPI app, router mounting, startup/shutdown
├── config.py                    # Pydantic Settings — env vars, secrets
├── database.py                  # SQLAlchemy engine, session factory, Base
├── dependencies.py              # DI: get_db, get_current_user, get_tenant
├── exceptions.py                # Domain exceptions + handlers
├── middleware.py                # Tenant resolution, request ID, timing, CORS
│
├── api/                         # HTTP layer — thin. Validate, delegate, return.
│   ├── __init__.py
│   ├── router.py                # Aggregates all v1 routers
│   └── v1/
│       ├── __init__.py
│       ├── auth.py              # Login, session
│       ├── onboarding.py        # Company setup, paste-paragraph parse, persona
│       ├── employees.py         # CRUD, Slack ID mapping
│       ├── tasks.py             # List, create, detail, update
│       ├── approvals.py         # Queue, approve/edit/reject → resumes interrupt
│       ├── chat.py              # SSE stream to chat agent
│       ├── knowledge.py         # Document upload, search
│       ├── digest.py            # Daily digest, "run follow-up now" (demo button)
│       └── webhooks/
│           ├── __init__.py
│           └── slack.py         # Events + interactivity (button clicks)
│
├── core/                        # Cross-cutting, no business logic
│   ├── __init__.py
│   ├── security.py              # JWT, password hashing, Slack sig verification
│   ├── logging.py               # Structured logging
│   ├── audit.py                 # Audit-log writer — every tool call
│   ├── idempotency.py           # Key generation + upsert helper
│   └── scheduler.py             # APScheduler — daily wake-up (DeepAgents has no cron)
│
├── models/                      # SQLAlchemy ORM — the system of record
│   ├── __init__.py
│   ├── base.py                  # TimestampMixin, TenantMixin (company_id)
│   ├── company.py               # Tenant + persona config + hydra_tenant_id
│   ├── employee.py              # name, role, slack_user_id, manager_id
│   ├── task.py                  # status, owner, deadline, source_quote, confidence
│   ├── status_update.py         # Timeline: who said what, when
│   ├── approval.py              # Queue + LangGraph thread_id for resume
│   ├── knowledge_source.py      # Transcript/doc metadata (content in HydraDB)
│   └── audit_log.py             # agent, tool, input, result, timestamp
│
├── schemas/                     # Pydantic — API contracts + LLM output shapes
│   ├── __init__.py
│   ├── company.py
│   ├── employee.py
│   ├── task.py                  # TaskCreate, TaskRead, TaskSummary (for tools)
│   ├── extraction.py            # ExtractedTask — the LLM's structured output
│   ├── approval.py
│   ├── chat.py
│   └── slack.py                 # Block Kit payloads, interaction events
│
├── repositories/                # Data access only. No business rules.
│   ├── __init__.py
│   ├── base.py                  # Generic CRUD, tenant-scoped by default
│   ├── company.py
│   ├── employee.py              # find_by_name() for owner resolution
│   ├── task.py                  # list_stale(), list_pending_approval(), upsert()
│   ├── status_update.py
│   ├── approval.py
│   └── audit_log.py
│
├── services/                    # Business logic. Orchestrates repositories.
│   ├── __init__.py
│   ├── onboarding_service.py    # Paragraph → employee table, tenant.create()
│   ├── task_service.py          # ⚠ create() ALWAYS status=pending_approval
│   ├── approval_service.py      # Approve/edit/reject → resume checkpointed run
│   ├── owner_resolver.py        # Name → employee + confidence score
│   ├── digest_service.py        # Morning digest assembly
│   ├── slack_service.py         # Bolt client, DM send, Block Kit builders
│   ├── hydra_service.py         # HydraDB SDK wrapper (upload, fullRecall)
│   └── transcription_service.py # WhisperX
│
└── agentic_AI/                  # DeepAgents. Loops only — no business logic.
    ├── __init__.py
    ├── config.py                # Model, temperature, interrupt config
    ├── checkpointer.py          # PostgresSaver — survives approval pauses
    ├── agents/
    │   ├── __init__.py
    │   ├── extractor.py         # text → create_task() [pending]
    │   ├── followup.py          # invoked daily by core/scheduler.py
    │   └── chat.py              # read-only: query_tasks + search_memory
    ├── tools/                   # Thin wrappers over services. Enforce rules 1–5.
    │   ├── __init__.py
    │   ├── task_tools.py        # create_task, query_tasks, get_task_detail
    │   ├── employee_tools.py    # get_person, resolve_owner
    │   ├── memory_tools.py      # search_memory → HydraDB fullRecall
    │   └── slack_tools.py       # send_slack_dm, escalate_to_manager  ⚠ interrupt
    ├── interrupts.py            # Predicates: which tool calls need approval
    └── prompts/
        ├── __init__.py
        ├── extractor.py
        ├── followup.py
        └── chat.py
```