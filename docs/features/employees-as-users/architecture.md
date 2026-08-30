## Architecture: Employees as Users

The request paths and access boundaries for founder-managed employee accounts and employee-facing task reporting.

```mermaid
graph TD
    Client["Client<br/>Authorization: Bearer &lt;jwt&gt;"]

    subgraph AuthLayer["Auth & Role Dependencies — app/dependencies.py"]
        CurrentUser["get_current_user<br/>verifies JWT & active user"]
        FounderGuard["FounderUser<br/>role == FOUNDER"]
        EmployeeGuard["EmployeeUser<br/>role == EMPLOYEE & employee_id != None"]
        EmployeeIdDep["CurrentEmployeeId<br/>extracts employee_id from token"]
    end

    subgraph FounderEndpoints["Founder API — app/api/v1/employees.py"]
        CreateLogin["POST /employees/{id}/login"]
        UpdateLogin["PATCH /employees/{id}/login"]
        DeleteLogin["DELETE /employees/{id}/login"]
        DeleteEmp["DELETE /employees/{id}"]
    end

    subgraph EmployeeEndpoints["Employee API — app/api/v1/me.py"]
        MyTasks["GET /me/tasks"]
        MyTaskDetail["GET /me/tasks/{task_id}"]
        MyStatusUpdate["POST /me/tasks/{task_id}/status"]
    end

    subgraph Services["Service Layer"]
        EmpSvc["EmployeeService<br/>create_login, update_login, delete_login<br/>delete (cleans up linked User)"]
        TaskSvc["TaskService<br/>get_owned_or_404(task_id, employee_id)<br/>record_status(task_id, payload)"]
    end

    subgraph Database["PostgreSQL (Neon)"]
        Users[("users table<br/>uq_users_email (global)<br/>uq_users_employee_id (1:1)<br/>@validates('email') lower+strip")]
        Employees[("employees table")]
        Tasks[("tasks table")]
        Updates[("status_updates table")]
    end

    Client --> CurrentUser
    CurrentUser --> FounderGuard
    CurrentUser --> EmployeeGuard
    EmployeeGuard --> EmployeeIdDep

    FounderGuard --> CreateLogin
    FounderGuard --> UpdateLogin
    FounderGuard --> DeleteLogin
    FounderGuard --> DeleteEmp

    EmployeeGuard --> MyTasks
    EmployeeGuard --> MyTaskDetail
    EmployeeGuard --> MyStatusUpdate
    EmployeeIdDep --> MyTasks
    EmployeeIdDep --> MyTaskDetail
    EmployeeIdDep --> MyStatusUpdate

    CreateLogin --> EmpSvc
    UpdateLogin --> EmpSvc
    DeleteLogin --> EmpSvc
    DeleteEmp --> EmpSvc

    MyTasks --> TaskSvc
    MyTaskDetail --> TaskSvc
    MyStatusUpdate --> TaskSvc

    EmpSvc --> Users
    EmpSvc --> Employees
    TaskSvc --> Tasks
    TaskSvc --> Updates

    Users -.->|"employee_id (1:1)"| Employees
    Employees -.->|"owner_employee_id"| Tasks
```

### Access Control & Security Invariants
1. **Deterministic Login:** `users.email` is globally unique and normalized to lowercase on model validation, ensuring single-tenant resolution during authentication.
2. **Founder Privilege:** Only `FounderUser` can provision, update, or delete employee logins.
3. **Employee Ownership Isolation:** `GET /me/tasks/{task_id}` and `POST /me/tasks/{task_id}/status` enforce ownership via `TaskService.get_owned_or_404`. Any attempt to access another employee's task returns `404 Task not found.` rather than confirming existence with a 403.
4. **Status Update Pinning:** `POST /me/tasks/{task_id}/status` automatically pins `reported_by_employee_id` to the token's `employee_id` and `reported_via` to `DASHBOARD`, preventing status attribution spoofing.
