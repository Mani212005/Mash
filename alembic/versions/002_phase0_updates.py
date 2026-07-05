"""Phase 0 Updates: Rename twilio_call_sid and Add conversation_states

Revision ID: 002
Revises: 001
Create Date: 2026-07-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Rename twilio_call_sid column to channel_session_id
    op.alter_column('calls', 'twilio_call_sid', new_column_name='channel_session_id')
    
    # 2. Re-create index with the new column name
    op.drop_index('ix_calls_twilio_call_sid', table_name='calls')
    op.create_index('ix_calls_channel_session_id', 'calls', ['channel_session_id'], unique=True)

    # 3. Create conversation_states table
    op.create_table(
        'conversation_states',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chat_id', sa.String(length=64), nullable=False),
        sa.Column('channel', sa.String(length=32), nullable=True),
        sa.Column('namespace', sa.String(length=32), nullable=False),
        sa.Column('current_agent', sa.String(length=64), nullable=True),
        sa.Column('slots', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('history', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_conversation_states_chat_id', 'conversation_states', ['chat_id'], unique=False)
    op.create_index('ix_conversation_states_channel', 'conversation_states', ['channel'], unique=False)
    op.create_index('ix_conversation_states_namespace', 'conversation_states', ['namespace'], unique=False)
    op.create_index('ix_conversation_states_chat_namespace', 'conversation_states', ['chat_id', 'namespace'], unique=True)


def downgrade() -> None:
    # 1. Drop conversation_states table and its indexes
    op.drop_index('ix_conversation_states_chat_namespace', table_name='conversation_states')
    op.drop_index('ix_conversation_states_namespace', table_name='conversation_states')
    op.drop_index('ix_conversation_states_channel', table_name='conversation_states')
    op.drop_index('ix_conversation_states_chat_id', table_name='conversation_states')
    op.drop_table('conversation_states')

    # 2. Revert column rename and recreate original index
    op.drop_index('ix_calls_channel_session_id', table_name='calls')
    op.alter_column('calls', 'channel_session_id', new_column_name='twilio_call_sid')
    op.create_index('ix_calls_twilio_call_sid', 'calls', ['twilio_call_sid'])
