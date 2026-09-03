"""add chase tracking and reports table

Chasing moves from Slack DMs to in-product reminders, so a task needs to know how
many times it has been chased and the company needs to say when to stop. Reports
replace the discarded cron digest with a persisted, founder-readable record.

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-09-02 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b7c8d9e0f1a2'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # How many reminders before a task is handed back to the founder. The cadence
    # itself reuses the existing escalation_after_days rather than adding a second
    # interval that would have to agree with it.
    op.add_column(
        'companies',
        sa.Column('max_chases', sa.Integer(), server_default='2', nullable=False),
    )
    op.add_column(
        'tasks',
        sa.Column('chase_count', sa.Integer(), server_default='0', nullable=False),
    )

    op.create_table(
        'reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        # The day the report describes, distinct from when it was last built. A
        # founder regenerating at 2pm is reading today's report, not a second one.
        sa.Column('report_date', sa.Date(), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        # The computed sections. JSONB because the shape is presentational and will
        # change faster than a migration cadence allows; nothing queries into it.
        sa.Column('sections', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('counts', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        # Regenerating updates the day's row rather than appending a second one.
        sa.UniqueConstraint('company_id', 'report_date', name='uq_reports_company_date'),
    )
    op.create_index(op.f('ix_reports_company_id'), 'reports', ['company_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_reports_company_id'), table_name='reports')
    op.drop_table('reports')
    op.drop_column('tasks', 'chase_count')
    op.drop_column('companies', 'max_chases')
