"""make users email globally unique and enforce 1:1 user employee constraint

Revision ID: e3f4a5b6c7d8
Revises: d1f89a2b5e01
Create Date: 2026-08-30 18:30:00.000000

Note: Downgrade restores the original per-company constraint shape but cannot
restore original email casing prior to lowercasing normalization.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e3f4a5b6c7d8'
down_revision: Union[str, None] = 'd1f89a2b5e01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    
    # 1. Normalize existing email casing in DB first to prevent opaque 23505 errors
    op.execute("UPDATE users SET email = lower(btrim(email))")
    
    # 2. Pre-flight duplicate email check
    email_collisions = bind.execute(
        sa.text("SELECT email, count(*) FROM users GROUP BY email HAVING count(*) > 1")
    ).fetchall()
    if email_collisions:
        raise RuntimeError(f"Migration aborted: duplicate user emails exist: {email_collisions}")

    # 3. Pre-flight duplicate non-null employee_id check
    emp_collisions = bind.execute(
        sa.text("SELECT employee_id, count(*) FROM users WHERE employee_id IS NOT NULL GROUP BY employee_id HAVING count(*) > 1")
    ).fetchall()
    if emp_collisions:
        raise RuntimeError(f"Migration aborted: duplicate employee_ids exist in users: {emp_collisions}")

    # 4. Swap constraints
    op.drop_constraint("uq_users_company_email", "users", type_="unique")
    op.create_unique_constraint("uq_users_email", "users", ["email"])
    op.create_unique_constraint("uq_users_employee_id", "users", ["employee_id"])


def downgrade() -> None:
    op.drop_constraint("uq_users_employee_id", "users", type_="unique")
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.create_unique_constraint("uq_users_company_email", "users", ["company_id", "email"])
