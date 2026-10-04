"""add achievements tables

Revision ID: a1b2c3d4e5f6
Revises: f4a5b6c7d8e9
Create Date: 2026-10-01 21:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f4a5b6c7d8e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Achievement definitions table
    op.create_table(
        'achievement_definitions',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('icon', sa.String(length=50), nullable=False),
        sa.Column('rarity', sa.String(length=20), nullable=False, server_default='Common'),
        sa.Column('xp_reward', sa.Integer(), nullable=False, server_default='25'),
        sa.Column('target_value', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('requirement_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_achievement_definitions_category'), 'achievement_definitions', ['category'], unique=False)
    op.create_index(op.f('ix_achievement_definitions_rarity'), 'achievement_definitions', ['rarity'], unique=False)
    op.create_index(op.f('ix_achievement_definitions_sort_order'), 'achievement_definitions', ['sort_order'], unique=False)

    # 2. User achievements table
    op.create_table(
        'user_achievements',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('achievement_id', sa.String(length=64), sa.ForeignKey('achievement_definitions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('current_progress', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('target_progress', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('unlocked', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('unlocked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('claimed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('user_id', 'achievement_id', name='uq_user_achievement')
    )
    op.create_index(op.f('ix_user_achievements_user_id'), 'user_achievements', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_achievements_achievement_id'), 'user_achievements', ['achievement_id'], unique=False)
    op.create_index(op.f('ix_user_achievements_unlocked'), 'user_achievements', ['unlocked'], unique=False)


def downgrade() -> None:
    op.drop_table('user_achievements')
    op.drop_table('achievement_definitions')
