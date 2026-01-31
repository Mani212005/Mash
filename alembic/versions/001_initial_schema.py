"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2026-01-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create calls table
    op.create_table(
        'calls',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('twilio_call_sid', sa.String(64), nullable=False),
        sa.Column('direction', sa.String(16), nullable=False),
        sa.Column('from_number', sa.String(32), nullable=False),
        sa.Column('to_number', sa.String(32), nullable=False),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('answered_at', sa.DateTime(), nullable=True),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('current_agent_id', sa.String(64), nullable=True),
        sa.Column('agent_history', postgresql.JSON(), nullable=False),
        sa.Column('metadata', postgresql.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('twilio_call_sid'),
    )
    op.create_index('ix_calls_twilio_call_sid', 'calls', ['twilio_call_sid'])
    op.create_index('ix_calls_status_started', 'calls', ['status', 'started_at'])

    # Create call_events table
    op.create_table(
        'call_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('call_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(64), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('data', postgresql.JSON(), nullable=False),
        sa.Column('latency_ms', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['call_id'], ['calls.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_call_events_call_id', 'call_events', ['call_id'])
    op.create_index('ix_call_events_timestamp', 'call_events', ['timestamp'])
    op.create_index('ix_call_events_call_type', 'call_events', ['call_id', 'event_type'])

    # Create transcripts table
    op.create_table(
        'transcripts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('call_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('speaker', sa.String(16), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('is_final', sa.Boolean(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('start_time_ms', sa.Float(), nullable=True),
        sa.Column('end_time_ms', sa.Float(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['call_id'], ['calls.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_transcripts_call_id', 'transcripts', ['call_id'])

    # Create agents table
    op.create_table(
        'agents',
        sa.Column('id', sa.String(64), nullable=False),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('agent_type', sa.String(32), nullable=False),
        sa.Column('system_prompt', sa.Text(), nullable=False),
        sa.Column('tools', postgresql.JSON(), nullable=False),
        sa.Column('transfer_rules', postgresql.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('config', postgresql.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create tool_invocations table
    op.create_table(
        'tool_invocations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('call_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tool_name', sa.String(64), nullable=False),
        sa.Column('agent_id', sa.String(64), nullable=False),
        sa.Column('parameters', postgresql.JSON(), nullable=False),
        sa.Column('result', postgresql.JSON(), nullable=True),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_ms', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['call_id'], ['calls.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_tool_invocations_call_id', 'tool_invocations', ['call_id'])


def downgrade() -> None:
    op.drop_table('tool_invocations')
    op.drop_table('agents')
    op.drop_table('transcripts')
    op.drop_table('call_events')
    op.drop_table('calls')
