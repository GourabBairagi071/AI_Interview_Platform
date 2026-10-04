"""add practice questions table

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-10-01 20:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'f4a5b6c7d8e9'
down_revision: Union[str, Sequence[str], None] = 'e3f4a5b6c7d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'practice_questions',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('technology', sa.String(length=100), nullable=False),
        sa.Column('technology_slug', sa.String(length=100), nullable=False),
        sa.Column('topic', sa.String(length=100), nullable=False),
        sa.Column('topic_slug', sa.String(length=100), nullable=False),
        sa.Column('subtopic', sa.String(length=100), nullable=False, server_default='General'),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('difficulty', sa.String(length=20), nullable=False),
        sa.Column('question_type', sa.String(length=50), nullable=False, server_default='Technical'),
        sa.Column('role', sa.String(length=100), nullable=True),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='canonical'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_practice_questions_technology'), 'practice_questions', ['technology'], unique=False)
    op.create_index(op.f('ix_practice_questions_technology_slug'), 'practice_questions', ['technology_slug'], unique=False)
    op.create_index(op.f('ix_practice_questions_topic'), 'practice_questions', ['topic'], unique=False)
    op.create_index(op.f('ix_practice_questions_topic_slug'), 'practice_questions', ['topic_slug'], unique=False)
    op.create_index(op.f('ix_practice_questions_difficulty'), 'practice_questions', ['difficulty'], unique=False)
    op.create_index('ix_practice_questions_tech_topic', 'practice_questions', ['technology_slug', 'topic_slug'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_practice_questions_tech_topic', table_name='practice_questions')
    op.drop_index(op.f('ix_practice_questions_difficulty'), table_name='practice_questions')
    op.drop_index(op.f('ix_practice_questions_topic_slug'), table_name='practice_questions')
    op.drop_index(op.f('ix_practice_questions_topic'), table_name='practice_questions')
    op.drop_index(op.f('ix_practice_questions_technology_slug'), table_name='practice_questions')
    op.drop_index(op.f('ix_practice_questions_technology'), table_name='practice_questions')
    op.drop_table('practice_questions')
