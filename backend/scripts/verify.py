"""Verification for step 1: schema rules, tenant isolation, and auth.

Not a test suite — a runnable check that the guarantees this layer claims are real.
Creates two throwaway companies, asserts against them, and deletes them.

    python -m scripts.verify
"""

import sys
import uuid
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.core.security import create_access_token, hash_password
from app.database import SessionLocal
from app.main import app
from app.models import Company, Employee, Task, TaskStatus, User, UserRole
from app.repositories.employee import EmployeeRepository
from app.repositories.base import TenantScopedRepository

PASSED: list[str] = []
FAILED: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    (PASSED if condition else FAILED).append(label)
    mark = "PASS" if condition else "FAIL"
    print(f"  [{mark}] {label}" + (f" — {detail}" if detail and not condition else ""))


class TaskRepository(TenantScopedRepository[Task]):
    model = Task


def main() -> int:  # noqa: C901 - a linear script of assertions
    db = SessionLocal()
    company_a = company_b = None

    try:
        suffix = uuid.uuid4().hex[:8]
        company_a = Company(name=f"verify-a-{suffix}")
        company_b = Company(name=f"verify-b-{suffix}")
        db.add_all([company_a, company_b])
        db.flush()

        emp_a = Employee(company_id=company_a.id, name="Alice A")
        emp_b = Employee(company_id=company_b.id, name="Bob B")
        db.add_all([emp_a, emp_b])
        # Committed before the constraint checks below: an expected IntegrityError
        # rolls the transaction back, and uncommitted setup rows would go with it.
        db.commit()

        print("\nSchema rules")

        # Rule 1: pending_approval is a server default, not something a caller chooses.
        task_a = Task(
            company_id=company_a.id,
            title="Q4 forecast",
            idempotency_key=f"src-1:{suffix}",
            owner_employee_id=emp_a.id,
        )
        db.add(task_a)
        db.flush()
        db.refresh(task_a)
        check(
            "task with no explicit status defaults to pending_approval",
            task_a.status is TaskStatus.PENDING_APPROVAL,
            f"got {task_a.status}",
        )

        # Rule 3: idempotency key blocks a duplicate within a tenant...
        db.add(
            Task(company_id=company_a.id, title="Q4 forecast", idempotency_key=f"src-1:{suffix}")
        )
        duplicate_blocked = False
        try:
            db.flush()
        except IntegrityError:
            duplicate_blocked = True
            db.rollback()
        check("duplicate (company_id, idempotency_key) is rejected", duplicate_blocked)

        # ...but the same key under another tenant is a different task.
        db.add_all([company_a, company_b])
        db.merge(company_a)
        db.merge(company_b)
        emp_b = db.merge(emp_b)
        task_b = Task(
            company_id=company_b.id,
            title="Q4 forecast",
            idempotency_key=f"src-1:{suffix}",
            owner_employee_id=emp_b.id,
        )
        db.add(task_b)
        cross_tenant_ok = True
        try:
            db.flush()
        except IntegrityError:
            cross_tenant_ok = False
            db.rollback()
        check("same idempotency_key under a different company is allowed", cross_tenant_ok)

        db.commit()

        print("\nTenant isolation")

        repo_a = TaskRepository(db, company_a.id)
        repo_b = TaskRepository(db, company_b.id)

        a_ids = {t.id for t in repo_a.list()}
        check(
            "company A's repository returns none of company B's tasks",
            task_b.id not in a_ids and task_a.id in a_ids,
        )

        # The one that matters: a correct primary key is not enough.
        check(
            "fetching B's task by exact id through A's repository returns None",
            repo_a.get(task_b.id) is None,
        )
        check("B's own repository can still fetch it", repo_b.get(task_b.id) is not None)

        emp_repo_a = EmployeeRepository(db, company_a.id)
        check(
            "employee search does not cross tenants",
            len(emp_repo_a.search_by_name("Bob")) == 0
            and len(emp_repo_a.search_by_name("Alice")) == 1,
        )

        # create() must ignore an attacker-supplied company_id.
        forced = repo_a.create(
            title="forced", idempotency_key=f"forced:{suffix}", company_id=company_b.id
        )
        check(
            "repository.create() ignores a caller-supplied company_id",
            forced.company_id == company_a.id,
        )
        db.commit()

        print("\nAuth")

        password = "verify-pw-123"  # noqa: S105 - throwaway
        user_a = User(
            company_id=company_a.id,
            email=f"a-{suffix}@verify.test",
            password_hash=hash_password(password),
            role=UserRole.FOUNDER,
        )
        user_b = User(
            company_id=company_b.id,
            email=f"b-{suffix}@verify.test",
            password_hash=hash_password(password),
            role=UserRole.EMPLOYEE,
        )
        db.add_all([user_a, user_b])
        db.commit()

        client = TestClient(app, raise_server_exceptions=False)

        r = client.post(
            "/api/v1/auth/login", json={"email": user_a.email, "password": password}
        )
        check("login with valid credentials returns 200", r.status_code == 200, str(r.status_code))
        token = r.json().get("access_token", "") if r.status_code == 200 else ""

        from app.core.security import decode_access_token

        claims = decode_access_token(token) or {}
        check(
            "token carries the right company_id and role",
            claims.get("company_id") == str(company_a.id) and claims.get("role") == "founder",
        )

        r = client.post(
            "/api/v1/auth/login", json={"email": user_a.email, "password": "wrong"}
        )
        body = r.json()
        check("wrong password returns 401", r.status_code == 401, str(r.status_code))
        check(
            "wrong-password error does not reveal whether the account exists",
            body.get("code") == "INVALID_CREDENTIALS"
            and "password" in body.get("error", "").lower()
            and "email" in body.get("error", "").lower(),
        )

        r_unknown = client.post(
            "/api/v1/auth/login",
            json={"email": f"nobody-{suffix}@verify.test", "password": password},
        )
        check(
            "unknown email and wrong password are indistinguishable",
            r_unknown.status_code == r.status_code and r_unknown.json() == body,
        )

        r = client.get("/api/v1/auth/me")
        check("no token returns 401", r.status_code == 401, str(r.status_code))

        r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        check(
            "valid token resolves the right user and company",
            r.status_code == 200
            and r.json()["email"] == user_a.email
            and r.json()["company"]["id"] == str(company_a.id),
            str(r.status_code),
        )

        # A signed token for company B must see only company B.
        token_b = create_access_token(
            user_id=user_b.id, company_id=company_b.id, role=UserRole.EMPLOYEE
        )
        r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_b}"})
        check(
            "the token is the trust boundary — company follows the claim",
            r.status_code == 200 and r.json()["company"]["id"] == str(company_b.id),
        )

        # Right user, wrong company: the pairing is re-checked on every request.
        forged = create_access_token(
            user_id=user_a.id, company_id=company_b.id, role=UserRole.FOUNDER
        )
        r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {forged}"})
        check(
            "a token pairing a real user with another company is rejected",
            r.status_code == 401,
            str(r.status_code),
        )

        r = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}x"},
        )
        check("a tampered signature is rejected", r.status_code == 401, str(r.status_code))

        expired = create_access_token(
            user_id=user_a.id,
            company_id=company_a.id,
            role=UserRole.FOUNDER,
            expires_delta=timedelta(seconds=-10),
        )
        r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})
        check("an expired token is rejected", r.status_code == 401, str(r.status_code))

        user_a.is_active = False
        db.commit()
        r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        check("a deactivated user is rejected", r.status_code == 403, str(r.status_code))

    finally:
        # Cascade removes employees, tasks, and users.
        for company in (company_a, company_b):
            if company is not None:
                obj = db.get(Company, company.id)
                if obj is not None:
                    db.delete(obj)
        db.commit()
        db.close()

    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
    if FAILED:
        for name in FAILED:
            print(f"  FAILED: {name}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
