# Employees as Users Plan

## Context

Previously, `Employee` (an org-chart row) and `User` (a login) were separate tables, and only founders had logins. Employees had no way to sign into the system directly — the original design assumed their entire experience was Slack DMs and buttons.

This feature enables employees to sign in, view their own assigned tasks, and report status via the web dashboard without Slack being a hard dependency. It establishes employee login management, global user email uniqueness, role-based dependency guards (`EmployeeUser`, `CurrentEmployeeId`), and the `/api/v1/me/tasks` dashboard surface.

## Architectural & Locked Decisions

- **Founder-provisioned credentials:** The founder sets the initial password for an employee account directly (min_length=8). Invite links are deferred.
- **Global Email Uniqueness:** `users.email` is globally unique (`uq_users_email`), replacing the previous per-company constraint (`uq_users_company_email`). This makes cross-tenant login deterministic without `.limit(1)` ambiguity.
- **1:1 User-Employee Link:** `users.employee_id` is constrained by a unique constraint (`uq_users_employee_id`), enforcing a 1:1 relationship between `User` and `Employee` (founders have `employee_id = None`).
- **Write-side Normalization:** Model-level `@validates("email")` on `User` normalizes all emails (`value.lower().strip()`) across ORM write paths.
- **Role Scoping & Restrictions:**
  - Employees cannot create tasks. They can only read and status-update tasks assigned to them (`owner_employee_id == current_user.employee_id`).
  - Employees can only update status to `IN_PROGRESS`, `BLOCKED`, or `DONE`.
  - Task ownership mismatch returns `404 Task not found.` (not 403) to prevent confirming the existence of other employees' tasks.
- **Account Deletion Safeguards:**
  - `DELETE /employees/{id}/login` hard-deletes the associated `User` row, freeing the email address.
  - `DELETE /employees/{id}` cleans up the associated `User` account, but refuses with `409 Conflict` if the employee is linked to a founder account or still owns open tasks.

## Implementation Detail

### 1. Database & Model Constraints
- `backend/app/models/user.py`: Replaced `uq_users_company_email` with `uq_users_email` and `uq_users_employee_id`. Added `@validates("email")` decorator.
- `backend/app/repositories/user.py`: Updated `find_by_email` and `find_user_for_login` queries and docstrings, removing `.limit(1)`.

### 2. Alembic Migration
- `backend/alembic/versions/e3f4a5b6c7d8_users_global_email_unique.py` (`down_revision = 'd1f89a2b5e01'`):
  - Normalizes existing email casing in DB via `UPDATE users SET email = lower(btrim(email))`.
  - Performs pre-flight checks for duplicate emails and duplicate non-null `employee_id` values, raising `RuntimeError` if collisions are found.
  - Drops `uq_users_company_email` and creates `uq_users_email` and `uq_users_employee_id`.

### 3. Schemas
- `backend/app/schemas/employee.py`: Added `EmployeeLoginCreate`, `EmployeeLoginUpdate`, and `EmployeeLoginRead`.
- `backend/app/schemas/task.py`: Added `EmployeeStatusUpdateCreate` with `status: Literal[TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED, TaskStatus.DONE]`.

### 4. Dependencies & Services
- `backend/app/dependencies.py`: Added `require_employee`, `get_current_employee_id`, `EmployeeUser`, and `CurrentEmployeeId`.
- `backend/app/services/task_service.py`: Added `get_owned_or_404(task_id, employee_id)` helper.
- `backend/app/services/employee_service.py`: Added `create_login`, `update_login`, `delete_login`, and updated `delete` to handle linked `User` cleanup and founder account protection.

### 5. API Layer
- `backend/app/api/v1/employees.py`: Added `POST /{employee_id}/login`, `PATCH /{employee_id}/login`, `DELETE /{employee_id}/login` (`FounderUser` protected).
- `backend/app/api/v1/me.py`: Created new router prefix `/me` with `GET /me/tasks`, `GET /me/tasks/{task_id}`, and `POST /me/tasks/{task_id}/status` (`EmployeeUser` protected).
- `backend/app/api/router.py`: Mounted `me.router`.

## Verification Plan

1. **Alembic Migration Verification:**
   - Test `alembic upgrade head` -> `alembic downgrade -1` -> `alembic upgrade head` against PostgreSQL (Neon).
2. **Comprehensive Integration Suite (`scripts/verify.py`):**
   - Verify login creation (201), duplicate login prevention (409), taken email rejection (409).
   - Verify direct ORM duplicate email prevention across tenants (`IntegrityError`).
   - Verify uppercase email login normalization (`200 OK`, `role=employee`).
   - Verify `/me/tasks` list and detail endpoints return only the caller's assigned tasks.
   - Verify accessing another employee's task returns `404 Task not found.`.
   - Verify employee status update pin (`reported_by_employee_id` set to caller, `reported_via` set to `DASHBOARD`).
   - Verify role guards (`EmployeeUser` on `/tasks` returns 403; `FounderUser` on `/me/tasks` returns 403).
   - Verify account deactivation (`is_active=False` returns 403 on subsequent requests).
   - Verify hard deletion of login (`DELETE .../login` returns 204 and frees email).
   - Verify employee deletion removes linked `User` row and blocks deletion of founder-linked employees (`409 Conflict`).
