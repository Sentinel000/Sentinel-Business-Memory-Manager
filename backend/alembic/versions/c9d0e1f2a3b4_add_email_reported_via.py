"""add email to reported_via

Revision ID: c9d0e1f2a3b4
Revises: b7c8d9e0f1a2
Create Date: 2026-10-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, None] = 'b7c8d9e0f1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # A status update that arrived through a one-tap email link. ADD VALUE runs
    # outside the migration's transaction: a new enum label cannot be used by the
    # transaction that created it, and older Postgres refuses it in one entirely.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE reported_via ADD VALUE IF NOT EXISTS 'email'")


def downgrade() -> None:
    # Postgres cannot drop a label from an enum. Remap the rows that use it, so the
    # history still reads correctly, and leave the label itself in place.
    op.execute("UPDATE status_updates SET reported_via = 'dashboard' WHERE reported_via = 'email'")
