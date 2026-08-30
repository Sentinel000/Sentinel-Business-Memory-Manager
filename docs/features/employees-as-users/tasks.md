# Tasks: Employees as Users

- [x] Replace `uq_users_company_email` constraint with `uq_users_email` and `uq_users_employee_id` in `app/models/user.py`
- [x] Add `@validates("email")` normalizer (`value.lower().strip()`) on `User` model in `app/models/user.py`
- [x] Update docstrings and query in `find_user_for_login` in `app/repositories/user.py`
- [x] Create Alembic migration `e3f4a5b6c7d8_users_global_email_unique.py` with pre-flight collision checks
- [x] Add `EmployeeLoginCreate`, `EmployeeLoginUpdate`, and `EmployeeLoginRead` schemas in `app/schemas/employee.py`
- [x] Add `EmployeeStatusUpdateCreate` schema in `app/schemas/task.py`
- [x] Add `require_employee`, `get_current_employee_id`, `EmployeeUser`, and `CurrentEmployeeId` dependencies in `app/dependencies.py`
- [x] Add `get_owned_or_404` helper method in `app/services/task_service.py`
- [x] Add `create_login`, `update_login`, and `delete_login` methods and update `delete` in `app/services/employee_service.py`
- [x] Add `POST`, `PATCH`, and `DELETE` `/{employee_id}/login` endpoints in `app/api/v1/employees.py`
- [x] Create `/me` router with `GET /me/tasks`, `GET /me/tasks/{task_id}`, and `POST /me/tasks/{task_id}/status` in `app/api/v1/me.py`
- [x] Mount `me.router` in `app/api/router.py`
- [x] Run Alembic migration `alembic upgrade head`
- [x] Extend `scripts/verify.py` with 12 employee verification checks and run full suite green
- [x] Add `CHANGELOG.md` entry
