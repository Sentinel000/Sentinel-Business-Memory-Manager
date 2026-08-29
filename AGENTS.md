# Sentinel — AI Business Companion

## Project Overview

Operational memory and follow-up engine for founders. Captures commitments from
meetings, Slack, email, and manual entry; routes them through founder approval;
delegates them in Slack; then chases owners on a schedule and collects status back
automatically — turning a founder's follow-up overhead from hours per week to a
single morning digest. Deployed as a dedicated instance per client.

Competitors stop at "here are your action items." Sentinel closes the loop:
**extract → approve → delegate → chase → collect → remember.**

## Data Hierarchy

```
Company (tenant)
  └── Employees
        └── Tasks
              └── Status Updates
                    └── Escalations
  └── Knowledge Sources (transcripts, SOPs, decisions, threads)
```

## Two Users

**Founder** — approves extracted tasks, queries business history in chat, reads the
daily digest, configures the persona. Lives in the dashboard.

**Employee** — receives tasks as Slack DMs, taps a status button, flags blockers.
Never opens the dashboard. Their entire experience is Slack.

## What the AI Does

Three tool-calling agents, no orchestration graph:

- **Extractor** — turns raw text (transcript, thread, email, typed sentence) into
  structured tasks with owner, deadline, and a verbatim source quote.
- **Follow-up** — woken daily by cron. Reviews open tasks, decides who needs chasing,
  sends reminders, escalates to managers on timeout.
- **Chat** — read-only. Answers "what's blocking the Q4 forecast?" over Postgres
  (structured state) and HydraDB (temporal knowledge).

The founder only touches the approve/edit/reject step. Every write the AI makes lands
in `pending_approval` by schema default — never by model judgment.

## Tech Stack

**Frontend:** Next.js 16, TypeScript, Tailwind CSS, Zustand for state management,
minimal smooth Tailwind animations, Axios for API handling

**Backend:** FastAPI, Pydantic, Alembic

**Agents Layer:** DeepAgents (OSS, self-hosted), LangGraph runtime + `PostgresSaver`
checkpointer, APScheduler for the daily wake-up

**Data:** PostgreSQL (Neon) as system of record, HydraDB as temporal knowledge and
retrieval layer

**Integrations:** Slack (Bolt — read and write, Block Kit interactive buttons),
WhisperX for transcription

**Infra:** Docker, VPS

## User Stories
See [@docs/context/user_stories.md](docs/context/user_stories.md)


## Rules

- [Code conventions](@docs/rules/coding-conventions.md)
- [Security](@docs/rules/security.md)
- [Error Handling](@docs/rules/error-handling.md)
- [ChangeLog][@docs/rules/error-handling.md] **Must add after each change in code**
- [Features](@docs/rules/feature-rules.md) **Keep this always in mind**

## Design System

Use for consistent UI across whole project frontend. See (Design File Here)[@docs/context/design.md]