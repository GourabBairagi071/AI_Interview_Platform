"""upgrade coding problems schema for large scale arena

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-10-03 19:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new metadata and editorial columns to coding_problems
    op.add_column('coding_problems', sa.Column('tags', sa.Text(), nullable=True))
    op.add_column('coding_problems', sa.Column('company_tags', sa.Text(), nullable=True))
    op.add_column('coding_problems', sa.Column('role_tags', sa.Text(), nullable=True))
    op.add_column('coding_problems', sa.Column('expected_time_complexity', sa.String(length=100), nullable=True))
    op.add_column('coding_problems', sa.Column('expected_space_complexity', sa.String(length=100), nullable=True))
    op.add_column('coding_problems', sa.Column('editorial', sa.Text(), nullable=True))
    op.add_column('coding_problems', sa.Column('hints', sa.Text(), nullable=True))

    # Add index for created_at for fast pagination
    op.create_index(op.f('ix_coding_problems_created_at'), 'coding_problems', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_coding_problems_created_at'), table_name='coding_problems')
    op.drop_column('coding_problems', 'hints')
    op.drop_column('coding_problems', 'editorial')
    op.drop_column('coding_problems', 'expected_space_complexity')
    op.drop_column('coding_problems', 'expected_time_complexity')
    op.drop_column('coding_problems', 'role_tags')
    op.drop_column('coding_problems', 'company_tags')
    op.drop_column('coding_problems', 'tags')
