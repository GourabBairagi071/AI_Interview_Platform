"""Add admin candidate control tables and columns

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3
Create Date: 2026-10-04 18:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f9a0b1c2d3e4"
down_revision: Union[str, Sequence[str], None] = "e8f9a0b1c2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. New Table: interview_configurations
    op.create_table(
        "interview_configurations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("category", sa.String(50), nullable=False, server_default="Technical"),
        sa.Column("target_role", sa.String(100), nullable=False),
        sa.Column("company_name", sa.String(100), nullable=True),
        sa.Column("difficulty", sa.String(50), nullable=False, server_default="Medium"),
        sa.Column("question_count", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("skill_coverage", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("question_selection_mode", sa.String(50), nullable=False, server_default="adaptive"),
        sa.Column("evaluation_criteria", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("scoring_weights", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("feedback_rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("ai_agent_key", sa.String(100), nullable=True, server_default="technical_interviewer"),
        sa.Column("rag_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("voice_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("anti_cheating_required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 2. New Table: career_roadmaps
    op.create_table(
        "career_roadmaps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("target_role", sa.String(100), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("difficulty", sa.String(50), nullable=False, server_default="Intermediate"),
        sa.Column("estimated_weeks", sa.Integer(), nullable=False, server_default="12"),
        sa.Column("prerequisites", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("skills", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("stages", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 3. New Table: practice_sets
    op.create_table(
        "practice_sets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("topic", sa.String(100), nullable=False, index=True),
        sa.Column("subtopic", sa.String(100), nullable=True),
        sa.Column("difficulty", sa.String(50), nullable=False, server_default="Intermediate"),
        sa.Column("role", sa.String(100), nullable=True),
        sa.Column("company", sa.String(100), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="45"),
        sa.Column("attempt_limit", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("is_premium", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 4. New Table: practice_set_questions
    op.create_table(
        "practice_set_questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_set_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("practice_sets.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("question_id", sa.String(64), sa.ForeignKey("practice_questions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("points", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 5. New Table: practice_set_attempts
    op.create_table(
        "practice_set_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("practice_set_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("practice_sets.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("max_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("percentage", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("responses", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(50), nullable=False, server_default="completed"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 6. Column extensions on existing tables
    op.add_column("contests", sa.Column("is_featured", sa.Boolean(), nullable=False, server_default="false"))

    op.add_column("practice_questions", sa.Column("company", sa.String(100), nullable=True))
    op.add_column("practice_questions", sa.Column("tags", sa.Text(), nullable=True))
    op.add_column("practice_questions", sa.Column("hints", sa.Text(), nullable=True))
    op.add_column("practice_questions", sa.Column("reference_links", sa.Text(), nullable=True))
    op.add_column("practice_questions", sa.Column("status", sa.String(50), nullable=False, server_default="PUBLISHED"))
    op.add_column("practice_questions", sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("practice_questions", sa.Column("is_featured", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("practice_questions", sa.Column("is_premium", sa.Boolean(), nullable=False, server_default="false"))

    op.add_column("coding_problems", sa.Column("solution_code", sa.Text(), nullable=True))
    op.add_column("coding_problems", sa.Column("status", sa.String(50), nullable=False, server_default="PUBLISHED"))
    op.add_column("coding_problems", sa.Column("is_published", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("coding_problems", sa.Column("is_featured", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("coding_problems", sa.Column("is_premium", sa.Boolean(), nullable=False, server_default="false"))

    op.add_column("companies", sa.Column("is_featured", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("companies", sa.Column("interview_patterns", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("companies", sa.Column("technical_topics", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("companies", sa.Column("hr_topics", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("companies", sa.Column("coding_topics", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("companies", sa.Column("faqs", postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    op.add_column("learning_resources", sa.Column("role", sa.String(100), nullable=True))
    op.add_column("learning_resources", sa.Column("is_premium", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("learning_resources", sa.Column("is_featured", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("learning_resources", sa.Column("is_published", sa.Boolean(), nullable=False, server_default="true"))

    op.add_column("ai_agent_configs", sa.Column("fallback_model", sa.String(100), nullable=True, server_default="gemini-1.5-flash"))
    op.add_column("ai_agent_configs", sa.Column("rag_enabled", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("ai_agent_configs", sa.Column("knowledge_scope", sa.String(255), nullable=True))
    op.add_column("ai_agent_configs", sa.Column("evaluation_criteria", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    pass
