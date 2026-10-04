"""add rag question vectors table

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-10-03 21:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, Sequence[str], None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Only attempt CREATE EXTENSION if vector is present in pg_available_extensions
    conn = op.get_bind()
    has_vector_ext = conn.execute(
        sa.text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")
    ).scalar()
    if has_vector_ext:
        conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector;"))

    op.create_table(
        'interview_question_vectors',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('question_id', sa.String(length=64), nullable=False, unique=True),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('question_type', sa.String(length=50), nullable=False, server_default='Technical'),
        sa.Column('role', sa.String(length=100), nullable=True),
        sa.Column('difficulty', sa.String(length=20), nullable=False),
        sa.Column('skills', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('topic', sa.String(length=100), nullable=False),
        sa.Column('company', sa.String(length=100), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='practice_bank'),
        sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    op.create_index(op.f('ix_interview_question_vectors_question_id'), 'interview_question_vectors', ['question_id'], unique=True)
    op.create_index(op.f('ix_interview_question_vectors_role'), 'interview_question_vectors', ['role'], unique=False)
    op.create_index(op.f('ix_interview_question_vectors_difficulty'), 'interview_question_vectors', ['difficulty'], unique=False)
    op.create_index(op.f('ix_interview_question_vectors_topic'), 'interview_question_vectors', ['topic'], unique=False)
    op.create_index(op.f('ix_interview_question_vectors_question_type'), 'interview_question_vectors', ['question_type'], unique=False)
    op.create_index(op.f('ix_interview_question_vectors_company'), 'interview_question_vectors', ['company'], unique=False)
    op.create_index('ix_interview_question_vectors_topic_diff', 'interview_question_vectors', ['topic', 'difficulty'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_interview_question_vectors_topic_diff', table_name='interview_question_vectors')
    op.drop_index(op.f('ix_interview_question_vectors_company'), table_name='interview_question_vectors')
    op.drop_index(op.f('ix_interview_question_vectors_question_type'), table_name='interview_question_vectors')
    op.drop_index(op.f('ix_interview_question_vectors_topic'), table_name='interview_question_vectors')
    op.drop_index(op.f('ix_interview_question_vectors_difficulty'), table_name='interview_question_vectors')
    op.drop_index(op.f('ix_interview_question_vectors_role'), table_name='interview_question_vectors')
    op.drop_index(op.f('ix_interview_question_vectors_question_id'), table_name='interview_question_vectors')
    op.drop_table('interview_question_vectors')
