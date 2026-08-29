## Architecture: Database, Tenancy & Auth

The request path. `company_id` enters as a signed JWT claim, is resolved once by
`get_current_user`, and is injected into every query by the repository base class —
never read from a request body.

```mermaid
graph TD
    Client["Client<br/>Authorization: Bearer &lt;jwt&gt;"]

    subgraph API["FastAPI"]
        MW["RequestContextMiddleware<br/>request id, timing"]
        CORS["CORSMiddleware"]
        Login["POST /api/v1/auth/login"]
        Me["GET /api/v1/auth/me"]
        EH["exceptions.py<br/>structured error handlers"]
    end

    subgraph Deps["Dependencies — the trust boundary"]
        Bearer["oauth2_scheme<br/>extract token"]
        CU["get_current_user<br/>decode, load, re-check company"]
        CID["get_company_id<br/>company_id from claim"]
        RF["require_founder<br/>role check"]
    end

    subgraph Core["core/security.py"]
        JWT["create / decode_access_token<br/>claims: sub, company_id, role, exp"]
        PW["hash / verify_password<br/>passlib + bcrypt"]
    end

    subgraph Repos["repositories — tenant scoping"]
        BaseRepo["TenantScopedRepository<br/>WHERE company_id = :company_id<br/>create() discards caller company_id"]
        UserRepo["UserRepository"]
        EmpRepo["EmployeeRepository"]
        CoRepo["CompanyRepository<br/>tenant root, unscoped by id"]
        Unscoped["find_user_for_login<br/>the one deliberate exception"]
    end

    subgraph DB["PostgreSQL — Neon"]
        Companies[("companies<br/>persona_config jsonb<br/>escalation_after_days")]
        Users[("users<br/>role, password_hash<br/>employee_id nullable")]
        Employees[("employees<br/>slack_user_id<br/>manager_id self-FK")]
        Tasks[("tasks<br/>status DEFAULT pending_approval<br/>UNIQUE company_id, idempotency_key")]
        Updates[("status_updates")]
        Approvals[("approvals<br/>thread_id")]
        Audit[("audit_log")]
    end

    Client --> MW --> CORS
    CORS --> Login
    CORS --> Me
    Login -.->|"401 / 403 / 409"| EH
    Me -.-> EH
    EH --> Client

    Login --> Unscoped
    Login --> PW
    Login --> JWT
    JWT -->|token| Client

    Me --> Bearer --> CU
    CU --> JWT
    CU --> CID
    CID --> RF
    CID -->|"company_id"| BaseRepo

    UserRepo --> BaseRepo
    EmpRepo --> BaseRepo
    BaseRepo --> Users
    BaseRepo --> Employees
    BaseRepo --> Tasks
    BaseRepo --> Updates
    BaseRepo --> Approvals
    BaseRepo --> Audit
    Unscoped --> Users
    CoRepo --> Companies

    Companies -->|"company_id, CASCADE"| Users
    Companies --> Employees
    Companies --> Tasks
    Companies --> Updates
    Companies --> Approvals
    Companies --> Audit

    Users -.->|"employee_id, the only FK<br/>between them"| Employees
    Employees -->|"owner_employee_id"| Tasks
    Employees -->|"manager_id"| Employees
    Tasks --> Updates
    Tasks --> Approvals
```

### The two things this diagram exists to show

**`company_id` has exactly one source.** It travels from the signed token through
`get_current_user` into the repository constructor. No route reads it from a body, query
param, or header, and `create()` discards it if a caller supplies one. The single
unscoped query, `find_user_for_login`, is unscoped because resolving the tenant is its
whole purpose — everything downstream uses the `company_id` it returns.

**`users` and `employees` are separate, linked one way.** Onboarding writes `employees`
before anyone has a login. The FK lives only on `users.employee_id`, so the two tables
cannot disagree about who is linked to whom.
