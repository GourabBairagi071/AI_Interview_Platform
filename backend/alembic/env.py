from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from app.core.config import settings
from app.core.database import Base
from app.modules.auth.model import User
from app.modules.resume.model import Resume
from app.modules.interview.model import Interview
from app.modules.anticheating.model import AntiCheatingEvent
from app.modules.coding.model import (
    CodingProblem,
    CodingSubmission,
    Contest,
    ContestProblem,
    ContestRegistration,
    ContestSubmission,
    ContestParticipantStats,
)
from app.modules.learning.model import (
    LearningProfile,
    SkillPerformance,
    LearningRoadmap,
    LearningResource,
    DailyPracticePlan,
    WeeklyGoal,
    LearningRecommendation,
)
from app.modules.practice.model import (
    PracticeProgress,
    PracticeQuestion,
)
from app.modules.achievements.model import (
    AchievementDefinition,
    UserAchievement,
)
from app.modules.notifications.model import (
    Notification,
)
from app.modules.rag.model import (
    InterviewQuestionVector,
)
from app.modules.payments.model import (
    SubscriptionPlan,
    UserSubscription,
    PaymentTransaction,
    Coupon,
    CouponUsage,
    Invoice,
)
from app.modules.support.model import (
    SupportTicket,
    SupportTicketMessage,
    Feedback,
    FAQ,
    HelpArticle,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in offline mode."""

    url = settings.database_url.replace(
        "postgresql+asyncpg://",
        "postgresql+psycopg://",
    )

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in online mode."""

    database_url = settings.database_url.replace(
        "postgresql+asyncpg://",
        "postgresql+psycopg://",
    )

    connectable = create_engine(database_url)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
