"""add coding interview tables

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-10-02 18:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'coding_problems',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('difficulty', sa.String(length=50), nullable=False),
        sa.Column('topic', sa.String(length=100), nullable=False),
        sa.Column('constraints', sa.Text(), nullable=True),
        sa.Column('input_format', sa.Text(), nullable=True),
        sa.Column('output_format', sa.Text(), nullable=True),
        sa.Column('examples', sa.Text(), nullable=True),
        sa.Column('starter_code', sa.Text(), nullable=True),
        sa.Column('supported_languages', sa.Text(), nullable=True),
        sa.Column('test_cases', sa.Text(), nullable=True),
        sa.Column('hidden_test_cases', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index(op.f('ix_coding_problems_slug'), 'coding_problems', ['slug'], unique=True)
    op.create_index(op.f('ix_coding_problems_difficulty'), 'coding_problems', ['difficulty'], unique=False)
    op.create_index(op.f('ix_coding_problems_topic'), 'coding_problems', ['topic'], unique=False)

    op.create_table(
        'coding_submissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('problem_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('interview_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('language', sa.String(length=50), nullable=False),
        sa.Column('source_code', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('score', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('passed_tests', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_tests', sa.Integer(), server_default='0', nullable=False),
        sa.Column('execution_time', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('memory_usage', sa.Float(), nullable=True),
        sa.Column('compile_error', sa.Text(), nullable=True),
        sa.Column('runtime_error', sa.Text(), nullable=True),
        sa.Column('test_results', sa.Text(), nullable=True),
        sa.Column('complexity_time', sa.String(length=100), nullable=True),
        sa.Column('complexity_space', sa.String(length=100), nullable=True),
        sa.Column('ai_review', sa.Text(), nullable=True),
        sa.Column('optimization_suggestions', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['problem_id'], ['coding_problems.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['interview_id'], ['interviews.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_coding_submissions_user_id'), 'coding_submissions', ['user_id'], unique=False)
    op.create_index(op.f('ix_coding_submissions_problem_id'), 'coding_submissions', ['problem_id'], unique=False)
    op.create_index(op.f('ix_coding_submissions_interview_id'), 'coding_submissions', ['interview_id'], unique=False)
    op.create_index(op.f('ix_coding_submissions_status'), 'coding_submissions', ['status'], unique=False)
    op.create_index(op.f('ix_coding_submissions_language'), 'coding_submissions', ['language'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_coding_submissions_language'), table_name='coding_submissions')
    op.drop_index(op.f('ix_coding_submissions_status'), table_name='coding_submissions')
    op.drop_index(op.f('ix_coding_submissions_interview_id'), table_name='coding_submissions')
    op.drop_index(op.f('ix_coding_submissions_problem_id'), table_name='coding_submissions')
    op.drop_index(op.f('ix_coding_submissions_user_id'), table_name='coding_submissions')
    op.drop_table('coding_submissions')

    op.drop_index(op.f('ix_coding_problems_topic'), table_name='coding_problems')
    op.drop_index(op.f('ix_coding_problems_difficulty'), table_name='coding_problems')
    op.drop_index(op.f('ix_coding_problems_slug'), table_name='coding_problems')
    op.drop_table('coding_problems')
