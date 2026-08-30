## Architecture: Employees, Approvals, Company & Onboarding endpoints

Two things this diagram exists to show: **every write passes the tenant guard in
`TenantService`**, and **the approval row is the single gate between a drafted task and
a delegated one**.

```mermaid
graph TD
    Founder["Founder<br/>Bearer &lt;jwt&gt;"]

    subgraph Deps["dependencies.py — the trust boundary"]
        CU["get_current_user<br/>decode, load, re-check company"]
        RF["require_founder<br/>every route below"]
        CID["get_company_id<br/>company_id from the signed claim"]
    end

    subgraph Routes["api/v1 — thin: validate, delegate, return"]
        REmp["employees.py<br/>list · create · detail<br/>patch · delete · /tasks"]
        RApp["approvals.py<br/>queue · detail · approve<br/>edit · reject · bulk"]
        RCo["company.py<br/>get · patch"]
        ROn["onboarding.py<br/>employees/bulk · status"]
        RTask["tasks.py<br/>existing"]
    end

    subgraph Services["services — the rules live here"]
        Base["TenantService<br/><b>require_own_employee()</b><br/>an id in a body is resolved<br/>through a scoped repository"]
        SEmp["EmployeeService<br/>· reject manager cycles<br/>· block delete while<br/>&nbsp;&nbsp;open tasks exist"]
        SApp["ApprovalService<br/>· decided states are final<br/>· edit ≠ decide<br/>· strip status from edits"]
        SOn["OnboardingService<br/>· pass 1 create<br/>· pass 2 link managers<br/>&nbsp;&nbsp;by name"]
        STask["TaskService<br/>create_manual → approved<br/><b>create_pending → waits</b>"]
    end

    subgraph Repos["repositories — WHERE company_id = :tenant"]
        RepoBase["TenantScopedRepository"]
        RepoEmp["EmployeeRepository"]
        RepoApp["ApprovalRepository<br/>UNDECIDED = pending + edited"]
        RepoTask["TaskRepository"]
        RepoCo["CompanyRepository"]
    end

    subgraph DB["PostgreSQL"]
        Companies[("companies<br/>persona_config<br/>slack_bot_token 🔒")]
        Employees[("employees<br/>manager_id self-FK<br/>slack_user_id")]
        Tasks[("tasks<br/>DEFAULT pending_approval")]
        Approvals[("approvals<br/>state · decided_by<br/>edited_payload · thread_id")]
        Updates[("status_updates")]
    end

    Founder --> CU --> RF --> CID
    CID --> REmp & RApp & RCo & ROn & RTask

    REmp --> SEmp
    RApp --> SApp
    ROn --> SOn
    REmp -.->|"/{id}/tasks"| STask
    RTask --> STask
    RCo --> RepoCo

    SEmp & SApp & SOn & STask --> Base

    SEmp --> RepoEmp
    SEmp --> RepoTask
    SApp --> RepoApp
    SApp --> RepoTask
    SOn --> RepoEmp
    STask --> RepoTask

    RepoEmp & RepoApp & RepoTask --> RepoBase
    RepoEmp --> Employees
    RepoApp --> Approvals
    RepoTask --> Tasks
    RepoTask --> Updates
    RepoCo --> Companies

    Companies -->|"company_id CASCADE"| Employees & Tasks & Approvals & Updates
    Employees -->|"owner_employee_id"| Tasks
    Employees -->|"manager_id"| Employees
    Tasks -->|"1:1"| Approvals
```

### The approval gate

Every task carries an approval row. Which one it gets is decided at creation, and that
is the whole of rule 1 — the state is never a model judgement.

```mermaid
stateDiagram-v2
    [*] --> approved_at_creation: create_manual()<br/>founder typed it
    [*] --> pending: create_pending()<br/>agent drafted it

    approved_at_creation: approved<br/><i>approval row names the founder</i>

    pending --> edited: POST /edit<br/>fix owner or deadline
    edited --> edited: further edits
    pending --> approved: POST /approve
    edited --> approved: POST /approve
    pending --> rejected: POST /reject
    edited --> rejected: POST /reject

    approved --> [*]: released for delegation
    rejected --> [*]: nobody is contacted

    note right of edited
        Still in the queue.
        Editing is not deciding —
        filtering the queue on
        pending alone would hide it.
    end note

    note right of approved
        Final. Deciding again is a 409:
        re-deciding rewrites history.
        thread_id resumes the paused
        LangGraph run once the
        extractor exists.
    end note
```
