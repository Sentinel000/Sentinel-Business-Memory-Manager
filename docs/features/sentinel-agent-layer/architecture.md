# Sentinel Agent Layer — Architecture

## Overview
The Sentinel Agent Layer implements the operational companion and follow-up engine for founders and employees. Sentinel maintains a single identity per company (configured via persona_config), invoked across three entry points with on-demand prompts and role-scoped dynamic tool binding:
1. **Chat**: Interactive conversational assistance from the dashboard (founder or employee role).
2. **Cron**: Daily follow-up and escalation engine running autonomously.
3. **Transcript Extractor**: Meeting recording / notes processing extracting structured tasks into the approval queue.

## LLM Configuration
- **Model**: qwen3.7-max (via Alibaba Cloud MaaS compatible-mode endpoint).
- **Runtime**: DeepAgents (create_deep_agent / LangGraph ReAct runtime) + PostgresSaver checkpointer.

## Dynamic Tool Scoping & Role Isolation
Tool closures bind company_id, ctor_id, and employee_id in function scope, completely removing authorization burden from model judgment:
- **Founder Chat**: create_task, query_tasks, get_task_detail, patch_task, pprove_task, list_employees, get_employee_detail.
- **Employee Chat**: query_my_tasks, get_my_task_detail, eport_my_status (restricted to owned tasks only; cannot query org-wide data or mutate others' tasks).
- **Cron Follow-up**: query_tasks, list_stale_tasks, send_reminder, escalate_task, list_employees.
- **Transcript Extractor**: create_extracted_task (confidence approval gate with uto_approve_threshold), list_employees.

## Thread Isolation & Checkpointing
- Thread persistence uses Conversation model (id, company_id, user_id, 	itle, created_at, updated_at).
- Checkpoints are stored in PostgreSQL using PostgresSaver.
- GET /api/v1/conversations/{id} strictly enforces tenant and user isolation.

## Audit Logging
- All tool executions are logged to udit_logs table via isolated database transactions, recording actor, agent, tool name, input arguments, response summary, duration (ms), and status with sensitive token redaction.
