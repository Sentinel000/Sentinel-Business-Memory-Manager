"""add company industry

Revision ID: d1f89a2b5e01
Revises: c8ad23ad5b04
Create Date: 2026-08-30 16:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd1f89a2b5e01'
down_revision: Union[str, None] = 'c8ad23ad5b04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('companies', sa.Column('industry', sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column('companies', 'industry')
