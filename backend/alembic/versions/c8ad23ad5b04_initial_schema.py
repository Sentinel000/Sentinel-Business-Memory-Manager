"""initial schema

Revision ID: c8ad23ad5b04
Revises: 
Create Date: 2026-08-29 16:45:00.877914

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c8ad23ad5b04'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



# Enum types are created and dropped explicitly below. Autogenerate declares them
# inline on each column, which emits CREATE TYPE once per table - task_status is
# used by both tasks and status_updates - and never drops them on downgrade, so a
# downgrade/upgrade cycle fails with 'type already exists'.
task_status = postgresql.ENUM('pending_approval', 'approved', 'in_progress', 'blocked', 'done', 'rejected', 'overdue', name='task_status', create_type=False)
user_role = postgresql.ENUM('founder', 'employee', name='user_role', create_type=False)
approval_state = postgresql.ENUM('pending', 'approved', 'edited', 'rejected', name='approval_state', create_type=False)
reported_via = postgresql.ENUM('slack', 'dashboard', 'agent', name='reported_via', create_type=False)

ALL_ENUMS = (task_status, user_role, approval_state, reported_via)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in ALL_ENUMS:
        enum_type.create(bind, checkfirst=True)

    op.create_table('companies',
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('persona_config', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
    sa.Column('escalation_after_days', sa.Integer(), server_default='3', nullable=False),
    sa.Column('slack_bot_token', sa.Text(), nullable=True),
    sa.Column('slack_team_id', sa.String(length=64), nullable=True),
    sa.Column('hydra_tenant_id', sa.String(length=128), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('audit_log',
    sa.Column('agent', sa.String(length=64), nullable=True),
    sa.Column('tool', sa.String(length=128), nullable=False),
    sa.Column('input', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('status', sa.String(length=32), server_default='success', nullable=False),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('duration_ms', sa.Integer(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('company_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_log_agent'), 'audit_log', ['agent'], unique=False)
    op.create_index('ix_audit_log_company_created', 'audit_log', ['company_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_audit_log_company_id'), 'audit_log', ['company_id'], unique=False)
    op.create_index(op.f('ix_audit_log_tool'), 'audit_log', ['tool'], unique=False)
    op.create_table('employees',
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('role_title', sa.String(length=200), nullable=True),
    sa.Column('email', sa.String(length=320), nullable=True),
    sa.Column('slack_user_id', sa.String(length=64), nullable=True),
    sa.Column('manager_id', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('company_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['manager_id'], ['employees.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('company_id', 'slack_user_id', name='uq_employees_company_slack')
    )
    op.create_index(op.f('ix_employees_company_id'), 'employees', ['company_id'], unique=False)
    op.create_index(op.f('ix_employees_name'), 'employees', ['name'], unique=False)
    op.create_index(op.f('ix_employees_slack_user_id'), 'employees', ['slack_user_id'], unique=False)
    op.create_table('tasks',
    sa.Column('title', sa.String(length=500), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('owner_employee_id', sa.UUID(), nullable=True),
    sa.Column('deadline', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', task_status, server_default='pending_approval', nullable=False),
    sa.Column('source_quote', sa.Text(), nullable=True),
    sa.Column('source_ref', sa.String(length=500), nullable=True),
    sa.Column('source_id', sa.String(length=255), nullable=True),
    sa.Column('confidence', sa.Float(), nullable=True),
    sa.Column('created_by_agent', sa.String(length=64), nullable=True),
    sa.Column('idempotency_key', sa.String(length=255), nullable=False),
    sa.Column('delegated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_chased_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('escalated', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('company_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['owner_employee_id'], ['employees.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('company_id', 'idempotency_key', name='uq_tasks_company_idempotency')
    )
    op.create_index(op.f('ix_tasks_company_id'), 'tasks', ['company_id'], unique=False)
    op.create_index('ix_tasks_company_status_deadline', 'tasks', ['company_id', 'status', 'deadline'], unique=False)
    op.create_index(op.f('ix_tasks_status'), 'tasks', ['status'], unique=False)
    op.create_table('users',
    sa.Column('email', sa.String(length=320), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('full_name', sa.String(length=200), nullable=True),
    sa.Column('role', user_role, server_default='employee', nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('employee_id', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('company_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('company_id', 'email', name='uq_users_company_email')
    )
    op.create_index(op.f('ix_users_company_id'), 'users', ['company_id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)
    op.create_table('approvals',
    sa.Column('task_id', sa.UUID(), nullable=False),
    sa.Column('state', approval_state, server_default='pending', nullable=False),
    sa.Column('decided_by_user_id', sa.UUID(), nullable=True),
    sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('edited_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('rejection_reason', sa.Text(), nullable=True),
    sa.Column('thread_id', sa.String(length=255), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('company_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['decided_by_user_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('task_id')
    )
    op.create_index(op.f('ix_approvals_company_id'), 'approvals', ['company_id'], unique=False)
    op.create_index(op.f('ix_approvals_state'), 'approvals', ['state'], unique=False)
    op.create_index(op.f('ix_approvals_thread_id'), 'approvals', ['thread_id'], unique=False)
    op.create_table('status_updates',
    sa.Column('task_id', sa.UUID(), nullable=False),
    sa.Column('status', task_status, nullable=False),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('reported_by_employee_id', sa.UUID(), nullable=True),
    sa.Column('reported_via', reported_via, server_default='slack', nullable=False),
    sa.Column('idempotency_key', sa.String(length=255), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('company_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['reported_by_employee_id'], ['employees.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_status_updates_company_id'), 'status_updates', ['company_id'], unique=False)
    op.create_index('ix_status_updates_task_created', 'status_updates', ['task_id', 'created_at'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    op.drop_index('ix_status_updates_task_created', table_name='status_updates')
    op.drop_index(op.f('ix_status_updates_company_id'), table_name='status_updates')
    op.drop_table('status_updates')
    op.drop_index(op.f('ix_approvals_thread_id'), table_name='approvals')
    op.drop_index(op.f('ix_approvals_state'), table_name='approvals')
    op.drop_index(op.f('ix_approvals_company_id'), table_name='approvals')
    op.drop_table('approvals')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_company_id'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_tasks_status'), table_name='tasks')
    op.drop_index('ix_tasks_company_status_deadline', table_name='tasks')
    op.drop_index(op.f('ix_tasks_company_id'), table_name='tasks')
    op.drop_table('tasks')
    op.drop_index(op.f('ix_employees_slack_user_id'), table_name='employees')
    op.drop_index(op.f('ix_employees_name'), table_name='employees')
    op.drop_index(op.f('ix_employees_company_id'), table_name='employees')
    op.drop_table('employees')
    op.drop_index(op.f('ix_audit_log_tool'), table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_company_id'), table_name='audit_log')
    op.drop_index('ix_audit_log_company_created', table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_agent'), table_name='audit_log')
    op.drop_table('audit_log')
    op.drop_table('companies')

    bind = op.get_bind()
    for enum_type in ALL_ENUMS:
        enum_type.drop(bind, checkfirst=True)
