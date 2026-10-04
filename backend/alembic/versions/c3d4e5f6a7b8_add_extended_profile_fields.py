"""add extended profile fields

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-10-01 21:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user_profiles', sa.Column('headline', sa.String(length=255), nullable=True))
    op.add_column('user_profiles', sa.Column('avatar_url', sa.String(length=500), nullable=True))
    op.add_column('user_profiles', sa.Column('location', sa.String(length=255), nullable=True))
    op.add_column('user_profiles', sa.Column('college', sa.String(length=255), nullable=True))
    op.add_column('user_profiles', sa.Column('degree', sa.String(length=255), nullable=True))
    op.add_column('user_profiles', sa.Column('graduation_year', sa.Integer(), nullable=True))
    op.add_column('user_profiles', sa.Column('target_role', sa.String(length=100), nullable=True))
    op.add_column('user_profiles', sa.Column('experience_level', sa.String(length=50), nullable=True))
    op.add_column('user_profiles', sa.Column('github_url', sa.String(length=500), nullable=True))
    op.add_column('user_profiles', sa.Column('linkedin_url', sa.String(length=500), nullable=True))
    op.add_column('user_profiles', sa.Column('portfolio_url', sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column('user_profiles', 'portfolio_url')
    op.drop_column('user_profiles', 'linkedin_url')
    op.drop_column('user_profiles', 'github_url')
    op.drop_column('user_profiles', 'experience_level')
    op.drop_column('user_profiles', 'target_role')
    op.drop_column('user_profiles', 'graduation_year')
    op.drop_column('user_profiles', 'degree')
    op.drop_column('user_profiles', 'college')
    op.drop_column('user_profiles', 'location')
    op.drop_column('user_profiles', 'avatar_url')
    op.drop_column('user_profiles', 'headline')
