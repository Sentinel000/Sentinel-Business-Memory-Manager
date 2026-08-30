"""add meetings and transcript_segments tables

Revision ID: a1b2c3d4e5f6
Revises: f4a5b6c7d8e9
Create Date: 2026-08-30 21:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f4a5b6c7d8e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create meetingstatus enum
    meetingstatus_enum = postgresql.ENUM(
        'pending', 'transcribing', 'extracting', 'completed', 'failed',
        name='meetingstatus',
        create_type=False
    )
    meetingstatus_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create meetings table
    op.create_table(
        'meetings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('audio_filename', sa.String(length=255), nullable=True),
        sa.Column('audio_format', sa.String(length=50), nullable=True),
        sa.Column('raw_transcript', sa.Text(), nullable=True),
        sa.Column(
            'status',
            postgresql.ENUM('pending', 'transcribing', 'extracting', 'completed', 'failed', name='meetingstatus', create_type=False),
            nullable=False,
            server_default='pending'
        ),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_meetings_company_id'), 'meetings', ['company_id'], unique=False)

    # 3. Create transcript_segments table
    op.create_table(
        'transcript_segments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('meeting_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('speaker_label', sa.String(length=100), nullable=False, server_default='Speaker 1'),
        sa.Column('speaker_employee_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('start_time', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('end_time', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['meeting_id'], ['meetings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['speaker_employee_id'], ['employees.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transcript_segments_company_id'), 'transcript_segments', ['company_id'], unique=False)
    op.create_index(op.f('ix_transcript_segments_meeting_id'), 'transcript_segments', ['meeting_id'], unique=False)
    op.create_index(op.f('ix_transcript_segments_speaker_employee_id'), 'transcript_segments', ['speaker_employee_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_transcript_segments_speaker_employee_id'), table_name='transcript_segments')
    op.drop_index(op.f('ix_transcript_segments_meeting_id'), table_name='transcript_segments')
    op.drop_index(op.f('ix_transcript_segments_company_id'), table_name='transcript_segments')
    op.drop_table('transcript_segments')
    op.drop_index(op.f('ix_meetings_company_id'), table_name='meetings')
    op.drop_table('meetings')
    sa.Enum(name='meetingstatus').drop(op.get_bind(), checkfirst=True)
