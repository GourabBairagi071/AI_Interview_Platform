"""add contest tables for competitive coding arena

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-10-03 20:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Contests Table
    op.create_table(
        'contests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False, server_default='90'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='UPCOMING'),
        sa.Column('max_participants', sa.Integer(), nullable=True),
        sa.Column('is_proctored', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('scoring_type', sa.String(length=50), nullable=False, server_default='ICPC'),
        sa.Column('penalty_per_wrong_attempt_mins', sa.Integer(), nullable=False, server_default='20'),
        sa.Column('rules', sa.Text(), nullable=True),
        sa.Column('allowed_languages', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(op.f('ix_contests_slug'), 'contests', ['slug'], unique=True)
    op.create_index(op.f('ix_contests_status'), 'contests', ['status'], unique=False)
    op.create_index(op.f('ix_contests_start_time'), 'contests', ['start_time'], unique=False)
    op.create_index(op.f('ix_contests_end_time'), 'contests', ['end_time'], unique=False)

    # 2. Contest Problems Table
    op.create_table(
        'contest_problems',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('contest_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('contests.id', ondelete='CASCADE'), nullable=False),
        sa.Column('problem_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('coding_problems.id', ondelete='CASCADE'), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('label', sa.String(length=10), nullable=False, server_default='A'),
        sa.Column('points', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('penalty_mins', sa.Integer(), nullable=False, server_default='20'),
        sa.Column('time_limit_seconds', sa.Float(), nullable=False, server_default='3.0'),
        sa.UniqueConstraint('contest_id', 'problem_id', name='uq_contest_problem'),
        sa.UniqueConstraint('contest_id', 'order_index', name='uq_contest_order'),
    )
    op.create_index(op.f('ix_contest_problems_contest_id'), 'contest_problems', ['contest_id'], unique=False)
    op.create_index(op.f('ix_contest_problems_problem_id'), 'contest_problems', ['problem_id'], unique=False)
    op.create_index(op.f('ix_contest_problems_order_index'), 'contest_problems', ['order_index'], unique=False)

    # 3. Contest Registrations Table
    op.create_table(
        'contest_registrations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('contest_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('contests.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('registered_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='REGISTERED'),
        sa.UniqueConstraint('contest_id', 'user_id', name='uq_contest_user_reg'),
    )
    op.create_index(op.f('ix_contest_registrations_contest_id'), 'contest_registrations', ['contest_id'], unique=False)
    op.create_index(op.f('ix_contest_registrations_user_id'), 'contest_registrations', ['user_id'], unique=False)

    # 4. Contest Submissions Table
    op.create_table(
        'contest_submissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('contest_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('contests.id', ondelete='CASCADE'), nullable=False),
        sa.Column('problem_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('coding_problems.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('coding_submission_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('coding_submissions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('language', sa.String(length=50), nullable=False),
        sa.Column('source_code', sa.Text(), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('execution_time', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('passed_tests', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_tests', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('penalty_minutes', sa.Integer(), nullable=False, server_default='0'),
    )
    op.create_index(op.f('ix_contest_submissions_contest_id'), 'contest_submissions', ['contest_id'], unique=False)
    op.create_index(op.f('ix_contest_submissions_problem_id'), 'contest_submissions', ['problem_id'], unique=False)
    op.create_index(op.f('ix_contest_submissions_user_id'), 'contest_submissions', ['user_id'], unique=False)
    op.create_index(op.f('ix_contest_submissions_submitted_at'), 'contest_submissions', ['submitted_at'], unique=False)
    op.create_index(op.f('ix_contest_submissions_status'), 'contest_submissions', ['status'], unique=False)

    # 5. Contest Participant Stats Table
    op.create_table(
        'contest_participant_stats',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('contest_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('contests.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('solved_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('penalty_minutes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rank', sa.Integer(), nullable=True),
        sa.Column('last_submission_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('problems_data', sa.Text(), nullable=True),
        sa.UniqueConstraint('contest_id', 'user_id', name='uq_contest_user_stats'),
    )
    op.create_index(op.f('ix_contest_participant_stats_contest_id'), 'contest_participant_stats', ['contest_id'], unique=False)
    op.create_index(op.f('ix_contest_participant_stats_user_id'), 'contest_participant_stats', ['user_id'], unique=False)
    op.create_index(op.f('ix_contest_participant_stats_rank'), 'contest_participant_stats', ['rank'], unique=False)


def downgrade() -> None:
    op.drop_table('contest_participant_stats')
    op.drop_table('contest_submissions')
    op.drop_table('contest_registrations')
    op.drop_table('contest_problems')
    op.drop_table('contests')
