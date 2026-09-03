# Scheduling and Briefings

Replaces Slack delegation with an in-product chase ladder, and replaces the discarded
cron digest with a persisted, on-demand founder briefing.

## Context

Two things were wrong before this feature.

**The digest was built and thrown away.** `daily_wake_up_job` called
`run_cron_followup(db, company)` without assigning the return value. The cron agent
produced a morning digest every day at 08:00 UTC — step 4 of its prompt — and nothing
caught it. There was no `digests` table, no endpoint, no UI. The founder user story
*"one morning digest rather than a notification per update"* had no implementation
despite the agent doing the work daily.

**Slack is being removed.** It was the delivery channel for delegation, chasing, and
status collection. Removing it breaks the collect half of the loop
(extract → approve → delegate → chase → collect → remember), which means the digest
would inherit a hole: `status_updates` had only ever been written by Slack Block Kit
buttons.

## Scope

Chasing moves into the product. Reporting becomes a separate, on-demand path. The
existing scheduling machinery (APScheduler) is kept; what it *does* changes.

Out of scope: email or any other push channel; per-meeting knowledge-graph views;
removing `slack_tools.py` from disk.

## The central decision: chasing and reporting must be separate paths

They have opposite safety profiles.

| | Chasing | Briefing |
|---|---|---|
| Audience | Employee | Founder |
| Effect | Writes outward | Pure read |
| Timing | Scheduled — chasing needs a clock | On demand |
| Re-running | Dangerous, double-notifies | Free, just recompute |

Concretely: as one agent, a "Regenerate briefing" button would also re-chase the whole
team. You cannot give a founder a refresh button on something that notifies people.
That single fact forces the split — it is not a stylistic preference.

Consequence: **the scheduler does chasing only.** Reports are never generated on a
schedule.

## Approach

### Chasing

**Silence is the clock; a deadline only brings it forward.** A task with no deadline
is still a commitment, and undated tasks are precisely the ones that rot unnoticed. A
deadline-based trigger would never chase them. One SQL clause covers both:

```
status IN (approved, in_progress)
AND owner_employee_id IS NOT NULL
AND escalated = false
AND chase_count < company.max_chases
AND (deadline < now() OR coalesce(last_chased_at, delegated_at, created_at) < now() - cadence)
AND (last_chased_at IS NULL OR last_chased_at < now() - cadence)
```

The second rate-limit clause applies to *both* paths. Without it an overdue task
matches on every run — the deadline stays passed, so the first clause never stops
being true — and burns its entire budget in one afternoon.

**Who is never chased:**
- `blocked` — the owner already answered, and the answer was "I am stuck". Nudging
  them is what trains people to ignore the tool. Goes straight to the founder.
- unowned — nobody to chase.
- `done` / `rejected` — finished.
- `pending_approval` — nobody has been asked yet.

`TaskStatus.OVERDUE` is absent because nothing in the codebase writes it; overdue is
derived from `deadline < now()` so it cannot go stale.

**The ladder terminates.** Two reminders, then chasing stops and `escalated = true`
hands the task to the founder. The cap exists to protect the briefing: unbounded
chasing means unbounded stale tasks, which is how a daily report stops being read.

**Reset semantics** — only a founder action grants a fresh budget:

| Event | `chase_count` | `escalated` |
|---|---|---|
| Employee marks blocked | unchanged | → true |
| Employee marks in progress / done | unchanged | → false |
| Founder unblocks / reassigns / moves deadline | → 0 | → false |
| Chase limit reached | frozen at max | → true |

The founder took an action that changed the situation, so the owner should not inherit
a spent budget for a blocker that was legitimate. The employee cannot reset their own
counter, so "mark blocked to buy time" does not work. Founder resets fire only when
the field's *value* actually changed — fixing a typo must not restart the ladder.

### Briefings

**No model.** Every figure is computed in SQL. "What is overdue" is a query, not a
retrieval (Architecture Rule 2), and a briefing that miscounts is worse than none.

Four sections, five items each, ordered by what a founder can act on:

1. **Needs your decision** — escalated or blocked, plus pending approvals. The only
   action list; everything below is context.
2. **Slipping** — overdue, or due within 48 hours.
3. **Moved** — status changes since the *previous* briefing, so nothing is counted
   twice and nothing falls through the gap between runs. Agent-written reminders are
   excluded: our own nudges are not news.
4. **Quiet** — chased, still live, owner has said nothing back.

The five-item cap is the design, not a limitation. A briefing that fits one screen
gets read; one that does not, does not.

Every item carries `source_quote` (Rule 6) so a claim can be checked rather than
trusted. Empty states are explicit sentences — "Nothing slipped" is a real, reassuring
answer, while a blank box reads as a broken feature.

Generation is idempotent on `(company_id, report_date)`. Regenerating updates the
day's row, so clicking twice yields one briefing rather than two versions of the same
morning with no way to tell which is current. `generated_at` is separate from
`report_date` so the UI can say "Today · built 2:14pm".

### The honest promise

With no push channel, an unread reminder is indistinguishable from an employee who has
not logged in. So the product promise changes and is stated rather than hidden:

> Sentinel cannot make someone respond. It guarantees the founder knows who has not.

This is why `escalated` is repurposed rather than replaced. It meant "the manager was
DM'd"; it now means "handed back to the founder", who is the only escalation path left.

## Schema

- `companies.max_chases` — integer, default 2
- `tasks.chase_count` — integer, default 0
- `reports` — `report_date`, `generated_at`, `sections` (JSONB), `counts` (JSONB),
  unique on `(company_id, report_date)`

The cadence reuses the existing `escalation_after_days` rather than adding a second
interval that would then have to be kept in agreement with it. Two founder settings
total; a setting nobody changes is a tax on everyone.

## Constraints and known issues

- `BackgroundScheduler` is in-process, so each uvicorn worker starts its own and the
  job fires once per worker. Safe at one worker; needs a lock or external trigger
  before scaling out.
- The daily job runs for every company, including ~12 test rows left by earlier
  scripts.
- `slack_tools.py` and `prompts/cron.py` remain on disk, exported but unreachable.
  Dead exports invite accidental re-wiring.
- Without in-app status updates the briefing only mirrors what the founder typed. The
  `/me` reminder surface plus the existing one-click status buttons are what make the
  report have real input.
