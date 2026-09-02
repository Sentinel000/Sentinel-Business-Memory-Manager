## Architecture: Scheduling and Briefings

Two paths that never touch. The scheduler writes (chasing); the founder's button only
reads (briefings). Keeping them apart is what makes regeneration safe to press twice.

```mermaid
graph TD
    subgraph Triggers
        CRON["APScheduler<br/>daily 08:00 UTC"]
        ADMIN["POST /admin/run-chase<br/>founder, on demand"]
        GENBTN["POST /reports/generate<br/>founder, on demand"]
    end

    subgraph ChasePath["Chase path — WRITES"]
        JOB["daily_wake_up_job<br/>session per tenant"]
        DUE["due_for_chase()<br/>silence OR deadline,<br/>rate-limited per cadence"]
        CYCLE["run_chase_cycle()<br/>chase_count += 1<br/>escalated at the limit"]
    end

    subgraph ReportPath["Briefing path — READ ONLY"]
        GEN["generate_report()<br/>idempotent on<br/>company_id + report_date"]
        S1["Needs your decision<br/>escalated / blocked / approvals"]
        S2["Slipping<br/>overdue or due in 48h"]
        S3["Moved<br/>delta since previous briefing"]
        S4["Quiet<br/>chased, still silent"]
        COUNTS["counts<br/>computed in SQL"]
    end

    subgraph Postgres["PostgreSQL — system of record"]
        TASKS[("tasks<br/>chase_count, escalated,<br/>last_chased_at, deadline")]
        SU[("status_updates<br/>reported_via:<br/>agent = reminder<br/>dashboard = reply")]
        REPORTS[("reports<br/>sections JSONB<br/>unique per company/day")]
        COMPANY[("companies<br/>max_chases,<br/>escalation_after_days")]
        APPROVALS[("approvals")]
    end

    subgraph UI
        BRIEF["/briefings<br/>founder"]
        ME["/me<br/>employee"]
        BANNER["ReminderBanner<br/>unanswered only"]
        STATUS["Status buttons<br/>done / in progress / blocked"]
    end

    CRON --> JOB
    ADMIN --> CYCLE
    JOB --> CYCLE
    CYCLE --> DUE
    DUE -.reads.-> TASKS
    DUE -.reads.-> COMPANY
    CYCLE -->|"updates"| TASKS
    CYCLE -->|"writes reminder"| SU

    GENBTN --> GEN
    GEN --> S1 & S2 & S3 & S4 & COUNTS
    S1 -.reads.-> TASKS
    S1 -.reads.-> APPROVALS
    S2 -.reads.-> TASKS
    S3 -.reads.-> SU
    S4 -.reads.-> TASKS
    S4 -.reads.-> SU
    GEN -->|"upsert"| REPORTS

    REPORTS --> BRIEF
    SU --> BANNER
    BANNER --> ME
    STATUS --> ME
    STATUS -->|"record_status()"| SU
    STATUS -->|"clears escalated"| TASKS

    classDef write fill:#fde68a,stroke:#b45309,color:#1c1917
    classDef read fill:#bfdbfe,stroke:#1d4ed8,color:#1c1917
    classDef store fill:#e7e5e4,stroke:#78716c,color:#1c1917
    class JOB,DUE,CYCLE write
    class GEN,S1,S2,S3,S4,COUNTS read
    class TASKS,SU,REPORTS,COMPANY,APPROVALS store
```

### Chase ladder state machine

```mermaid
stateDiagram-v2
    [*] --> Live: approved or in_progress

    Live --> Live: silent < cadence<br/>(no action)
    Live --> Chased1: deadline passed OR<br/>silent >= cadence
    Chased1 --> Chased2: another cadence of silence
    Chased2 --> HandedBack: chase_count == max_chases

    Live --> HandedBack: employee reports blocked
    Chased1 --> HandedBack: employee reports blocked

    Chased1 --> Live: employee responds<br/>(escalated cleared,<br/>budget NOT reset)
    Chased2 --> Live: employee responds

    HandedBack --> Live: founder unblocks / reassigns /<br/>moves deadline<br/>(chase_count = 0)

    Live --> [*]: done
    HandedBack --> [*]: closed by founder

    note right of HandedBack
        Appears in the briefing's
        "Needs your decision".
        The founder is the only
        escalation path now.
    end note

    note right of Chased2
        Never chased again.
        The cap protects the
        briefing from filling
        with tasks nobody will
        ever action.
    end note
```
