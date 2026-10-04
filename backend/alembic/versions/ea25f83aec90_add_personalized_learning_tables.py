"""add_personalized_learning_tables

Revision ID: ea25f83aec90
Revises: b8c9d0e1f2a3
Create Date: 2026-10-03 22:48:40.074759

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ea25f83aec90'
down_revision: Union[str, Sequence[str], None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. learning_resources
    op.create_table(
        'learning_resources',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('topic', sa.String(length=100), nullable=False),
        sa.Column('canonical_skill', sa.String(length=100), nullable=False),
        sa.Column('difficulty', sa.String(length=50), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=True),
        sa.Column('estimated_duration_mins', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('quality_rating', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_learning_resources_canonical_skill'), 'learning_resources', ['canonical_skill'], unique=False)
    op.create_index(op.f('ix_learning_resources_topic'), 'learning_resources', ['topic'], unique=False)

    # 2. learning_profiles
    op.create_table(
        'learning_profiles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('target_role', sa.String(length=255), nullable=False),
        sa.Column('target_level', sa.String(length=50), nullable=False),
        sa.Column('overall_readiness_score', sa.Float(), nullable=True),
        sa.Column('hours_per_week', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_learning_profiles_user_id'), 'learning_profiles', ['user_id'], unique=True)

    # 3. skill_performances
    op.create_table(
        'skill_performances',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('canonical_skill', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('interview_score', sa.Float(), nullable=True),
        sa.Column('interview_attempts', sa.Integer(), nullable=False),
        sa.Column('coding_score', sa.Float(), nullable=True),
        sa.Column('coding_attempts', sa.Integer(), nullable=False),
        sa.Column('combined_score', sa.Float(), nullable=True),
        sa.Column('total_attempts', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('confidence', sa.String(length=50), nullable=False),
        sa.Column('last_assessed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('score_history', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'canonical_skill', name='uq_user_canonical_skill')
    )
    op.create_index(op.f('ix_skill_performances_canonical_skill'), 'skill_performances', ['canonical_skill'], unique=False)
    op.create_index(op.f('ix_skill_performances_category'), 'skill_performances', ['category'], unique=False)
    op.create_index(op.f('ix_skill_performances_status'), 'skill_performances', ['status'], unique=False)
    op.create_index(op.f('ix_skill_performances_user_id'), 'skill_performances', ['user_id'], unique=False)

    # 4. learning_roadmaps
    op.create_table(
        'learning_roadmaps',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('target_role', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('progress_percentage', sa.Float(), nullable=False),
        sa.Column('weeks', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_learning_roadmaps_user_id'), 'learning_roadmaps', ['user_id'], unique=False)

    # 5. daily_practice_plans
    op.create_table(
        'daily_practice_plans',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('plan_date', sa.Date(), nullable=False),
        sa.Column('items', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_completed', sa.Boolean(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'plan_date', name='uq_user_plan_date')
    )
    op.create_index(op.f('ix_daily_practice_plans_plan_date'), 'daily_practice_plans', ['plan_date'], unique=False)
    op.create_index(op.f('ix_daily_practice_plans_user_id'), 'daily_practice_plans', ['user_id'], unique=False)

    # 6. weekly_goals
    op.create_table(
        'weekly_goals',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('week_start_date', sa.Date(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('goal_type', sa.String(length=50), nullable=False),
        sa.Column('target_count', sa.Integer(), nullable=False),
        sa.Column('completed_count', sa.Integer(), nullable=False),
        sa.Column('deadline', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_weekly_goals_user_id'), 'weekly_goals', ['user_id'], unique=False)
    op.create_index(op.f('ix_weekly_goals_week_start_date'), 'weekly_goals', ['week_start_date'], unique=False)

    # 7. learning_recommendations
    op.create_table(
        'learning_recommendations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('recommendation_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('topic', sa.String(length=100), nullable=False),
        sa.Column('priority', sa.String(length=50), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_dismissed', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_learning_recommendations_recommendation_type'), 'learning_recommendations', ['recommendation_type'], unique=False)
    op.create_index(op.f('ix_learning_recommendations_topic'), 'learning_recommendations', ['topic'], unique=False)
    op.create_index(op.f('ix_learning_recommendations_user_id'), 'learning_recommendations', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_table('learning_recommendations')
    op.drop_table('weekly_goals')
    op.drop_table('daily_practice_plans')
    op.drop_table('learning_roadmaps')
    op.drop_table('skill_performances')
    op.drop_table('learning_profiles')
    op.drop_table('learning_resources')
