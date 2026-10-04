import hashlib
import hmac
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.payments.model import (
    Coupon,
    CouponUsage,
    Invoice,
    PaymentTransaction,
    SubscriptionPlan,
    UserSubscription,
)


# ============================================================
# PLAN QUERIES
# ============================================================

async def get_active_plans(db: AsyncSession) -> list[SubscriptionPlan]:
    """Return all active subscription plans ordered by sort_order."""
    result = await db.execute(
        select(SubscriptionPlan)
        .where(SubscriptionPlan.is_active.is_(True))
        .order_by(SubscriptionPlan.sort_order)
    )
    return list(result.scalars().all())


async def get_plan_by_id(
    db: AsyncSession,
    plan_id: uuid.UUID,
) -> SubscriptionPlan | None:
    result = await db.execute(
        select(SubscriptionPlan)
        .where(SubscriptionPlan.id == plan_id)
    )
    return result.scalar_one_or_none()


# ============================================================
# SUBSCRIPTION QUERIES
# ============================================================

async def get_current_subscription(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> UserSubscription | None:
    """Return the user's current active or pending subscription.
    Also marks expired subscriptions."""
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(UserSubscription)
        .where(
            UserSubscription.user_id == user_id,
            UserSubscription.status.in_(["active", "pending"]),
        )
        .order_by(UserSubscription.created_at.desc())
        .limit(1)
    )
    sub = result.scalar_one_or_none()

    if sub and sub.status == "active" and sub.expires_at:
        if sub.expires_at < now:
            sub.status = "expired"
            await db.commit()
            await db.refresh(sub)
            return None

    return sub


async def get_current_plan(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> SubscriptionPlan | None:
    """Return the plan of the current active subscription."""
    sub = await get_current_subscription(db, user_id)
    if not sub:
        return None
    return sub.plan


async def activate_subscription(
    db: AsyncSession,
    user_id: uuid.UUID,
    plan_id: uuid.UUID,
    transaction_id: uuid.UUID,
) -> UserSubscription:
    """Create or update subscription to active status."""
    now = datetime.now(timezone.utc)
    plan = await get_plan_by_id(db, plan_id)
    if not plan:
        raise ValueError("Plan not found")

    # Expire any existing active subscription
    existing = await get_current_subscription(db, user_id)
    if existing and existing.status == "active":
        existing.status = "expired"

    expires = now + timedelta(days=plan.duration_days)

    subscription = UserSubscription(
        user_id=user_id,
        plan_id=plan_id,
        status="active",
        starts_at=now,
        expires_at=expires,
        auto_renew=False,
    )
    db.add(subscription)
    await db.flush()

    # Update the transaction with subscription id
    result = await db.execute(
        select(PaymentTransaction)
        .where(PaymentTransaction.id == transaction_id)
    )
    txn = result.scalar_one_or_none()
    if txn:
        txn.subscription_id = subscription.id

    await db.commit()
    await db.refresh(subscription)
    return subscription


async def cancel_subscription(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> UserSubscription | None:
    """Cancel the user's current active subscription."""
    sub = await get_current_subscription(db, user_id)
    if not sub or sub.status != "active":
        return None

    sub.status = "cancelled"
    sub.cancelled_at = datetime.now(timezone.utc)
    sub.auto_renew = False
    await db.commit()
    await db.refresh(sub)
    return sub


# ============================================================
# FEATURE ACCESS
# ============================================================

# Default free-tier limits
FREE_LIMITS = {
    "ai_interviews_per_month": 3,
    "coding_problems_per_day": 5,
    "resume_analyses_per_month": 2,
    "contest_participation": True,
    "question_practice": True,
    "basic_analytics": True,
    "advanced_analytics": False,
    "priority_support": False,
}


def get_effective_limits(plan: SubscriptionPlan | None) -> dict:
    """Return the effective usage limits for the user's plan."""
    if not plan or not plan.limits:
        return FREE_LIMITS.copy()
    merged = FREE_LIMITS.copy()
    merged.update(plan.limits)
    return merged


async def has_feature_access(
    db: AsyncSession,
    user_id: uuid.UUID,
    feature: str,
) -> bool:
    """Check if user has access to a specific feature."""
    plan = await get_current_plan(db, user_id)
    limits = get_effective_limits(plan)
    value = limits.get(feature)
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value > 0
    return True


async def get_usage_stats(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> dict:
    """Return aggregated usage stats for current month and day."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 1. Count interviews this month
    from app.modules.interview.model import Interview
    interview_result = await db.execute(
        select(func.count(Interview.id))
        .where(
            Interview.user_id == user_id,
            Interview.created_at >= month_start,
        )
    )
    interview_count = interview_result.scalar() or 0

    # 2. Count distinct coding problems attempted today
    from app.modules.coding.model import CodingSubmission
    coding_result = await db.execute(
        select(func.count(func.distinct(CodingSubmission.problem_id)))
        .where(
            CodingSubmission.user_id == user_id,
            CodingSubmission.created_at >= day_start,
        )
    )
    coding_count = coding_result.scalar() or 0

    # 3. Count resumes uploaded/analyzed this month
    from app.modules.resume.model import Resume
    resume_result = await db.execute(
        select(func.count(Resume.id))
        .where(
            Resume.user_id == user_id,
            Resume.uploaded_at >= month_start,
        )
    )
    resume_count = resume_result.scalar() or 0

    return {
        "ai_interviews_this_month": interview_count,
        "coding_problems_today": coding_count,
        "resume_analyses_this_month": resume_count,
    }


async def check_quota(
    db: AsyncSession,
    user_id: uuid.UUID,
    action: str,
) -> tuple[bool, str]:
    """Check whether a user has remaining quota or permission for an action.
    Returns (is_allowed, reason_if_denied)."""
    plan = await get_current_plan(db, user_id)
    limits = get_effective_limits(plan)
    stats = await get_usage_stats(db, user_id)
    plan_name = plan.name if plan else "Free"

    if action == "ai_interview":
        max_interviews = limits.get("ai_interviews_per_month", 3)
        current = stats.get("ai_interviews_this_month", 0)
        if current >= max_interviews:
            return (
                False,
                f"You have reached your monthly limit of {max_interviews} AI interviews on the {plan_name} plan. Upgrade to Pro or Premium for more!",
            )

    elif action == "coding_problem":
        max_daily = limits.get("coding_problems_per_day", 5)
        current = stats.get("coding_problems_today", 0)
        if current >= max_daily:
            return (
                False,
                f"You have reached your daily limit of {max_daily} coding problems on the {plan_name} plan. Upgrade to unlock unlimited coding problems!",
            )

    elif action == "resume_analysis":
        max_resumes = limits.get("resume_analyses_per_month", 2)
        current = stats.get("resume_analyses_this_month", 0)
        if current >= max_resumes:
            return (
                False,
                f"You have reached your monthly limit of {max_resumes} resume analyses on the {plan_name} plan. Upgrade to Pro or Premium for more!",
            )

    elif action in limits:
        val = limits[action]
        if isinstance(val, bool) and not val:
            return (
                False,
                f"The feature '{action}' is not included in the {plan_name} plan. Please upgrade your subscription to access it.",
            )

    return (True, "")


# ============================================================
# COUPON
# ============================================================

async def validate_coupon(
    db: AsyncSession,
    code: str,
    plan_id: uuid.UUID,
    user_id: uuid.UUID,
) -> dict:
    """Validate a coupon and return discount details."""
    plan = await get_plan_by_id(db, plan_id)
    if not plan:
        return {"valid": False, "message": "Plan not found"}

    if plan.price == 0:
        return {"valid": False, "message": "Coupons cannot be applied to free plans"}

    result = await db.execute(
        select(Coupon).where(
            Coupon.code == code.upper().strip(),
            Coupon.is_active.is_(True),
        )
    )
    coupon = result.scalar_one_or_none()

    if not coupon:
        return {"valid": False, "message": "Invalid coupon code"}

    now = datetime.now(timezone.utc)

    if coupon.valid_from and now < coupon.valid_from:
        return {"valid": False, "message": "Coupon is not yet active"}

    if coupon.valid_until and now > coupon.valid_until:
        return {"valid": False, "message": "Coupon has expired"}

    if coupon.usage_limit is not None and coupon.used_count >= coupon.usage_limit:
        return {"valid": False, "message": "Coupon usage limit reached"}

    if coupon.minimum_amount > 0 and plan.price < coupon.minimum_amount:
        return {
            "valid": False,
            "message": f"Minimum order amount is ₹{coupon.minimum_amount / 100:.2f}",
        }

    # Check if user already used this coupon
    usage_result = await db.execute(
        select(func.count(CouponUsage.id))
        .where(
            CouponUsage.coupon_id == coupon.id,
            CouponUsage.user_id == user_id,
        )
    )
    if (usage_result.scalar() or 0) > 0:
        return {"valid": False, "message": "You have already used this coupon"}

    # Calculate discount
    discount = calculate_discount(coupon, plan.price)

    return {
        "valid": True,
        "message": "Coupon applied successfully",
        "coupon_code": coupon.code,
        "discount_type": coupon.discount_type,
        "discount_value": coupon.discount_value,
        "original_amount": plan.price,
        "discount_amount": discount,
        "final_amount": plan.price - discount,
    }


def calculate_discount(coupon: Coupon, amount: int) -> int:
    """Calculate discount amount in paise."""
    if coupon.discount_type == "percentage":
        discount = (amount * coupon.discount_value) // 100
        if coupon.max_discount is not None:
            discount = min(discount, coupon.max_discount)
    else:  # fixed
        discount = coupon.discount_value

    # Discount cannot exceed the order amount
    return min(discount, amount)


async def record_coupon_usage(
    db: AsyncSession,
    coupon_code: str,
    user_id: uuid.UUID,
    payment_id: uuid.UUID,
    discount_amount: int,
) -> None:
    """Record coupon usage and increment the used_count."""
    result = await db.execute(
        select(Coupon).where(Coupon.code == coupon_code.upper().strip())
    )
    coupon = result.scalar_one_or_none()
    if not coupon:
        return

    usage = CouponUsage(
        coupon_id=coupon.id,
        user_id=user_id,
        payment_id=payment_id,
        discount_amount=discount_amount,
    )
    db.add(usage)
    coupon.used_count += 1
    await db.flush()


# ============================================================
# PAYMENT
# ============================================================

async def create_payment_transaction(
    db: AsyncSession,
    user_id: uuid.UUID,
    plan_id: uuid.UUID,
    amount: int,
    currency: str,
    provider_order_id: str,
    metadata: dict | None = None,
) -> PaymentTransaction:
    """Create a new payment transaction record."""
    txn = PaymentTransaction(
        user_id=user_id,
        plan_id=plan_id,
        amount=amount,
        currency=currency,
        provider="razorpay",
        provider_order_id=provider_order_id,
        status="created",
        metadata_json=metadata,
    )
    db.add(txn)
    await db.commit()
    await db.refresh(txn)
    return txn


async def get_transaction_by_order_id(
    db: AsyncSession,
    order_id: str,
) -> PaymentTransaction | None:
    result = await db.execute(
        select(PaymentTransaction)
        .where(PaymentTransaction.provider_order_id == order_id)
    )
    return result.scalar_one_or_none()


async def get_transaction_by_payment_id(
    db: AsyncSession,
    payment_id: str,
) -> PaymentTransaction | None:
    result = await db.execute(
        select(PaymentTransaction)
        .where(PaymentTransaction.provider_payment_id == payment_id)
    )
    return result.scalar_one_or_none()


async def mark_payment_paid(
    db: AsyncSession,
    txn: PaymentTransaction,
    payment_id: str,
    signature: str,
    method: str | None = None,
) -> PaymentTransaction:
    """Mark a transaction as paid (idempotent)."""
    if txn.status == "paid":
        return txn  # Already processed

    txn.provider_payment_id = payment_id
    txn.provider_signature = signature
    txn.status = "paid"
    txn.payment_method = method
    await db.flush()
    return txn


async def mark_payment_failed(
    db: AsyncSession,
    txn: PaymentTransaction,
    reason: str | None = None,
) -> PaymentTransaction:
    if txn.status == "paid":
        return txn  # Don't downgrade

    txn.status = "failed"
    txn.failure_reason = reason
    await db.flush()
    return txn


async def get_payment_history(
    db: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[PaymentTransaction], int]:
    """Return paginated payment history for a user."""
    count_result = await db.execute(
        select(func.count(PaymentTransaction.id))
        .where(PaymentTransaction.user_id == user_id)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(PaymentTransaction)
        .where(PaymentTransaction.user_id == user_id)
        .order_by(PaymentTransaction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all()), total


async def get_payment_by_id(
    db: AsyncSession,
    payment_id: uuid.UUID,
    user_id: uuid.UUID,
) -> PaymentTransaction | None:
    result = await db.execute(
        select(PaymentTransaction)
        .where(
            PaymentTransaction.id == payment_id,
            PaymentTransaction.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


# ============================================================
# INVOICE
# ============================================================

async def create_invoice(
    db: AsyncSession,
    user_id: uuid.UUID,
    payment_id: uuid.UUID,
    subscription_id: uuid.UUID | None,
    amount: int,
    discount: int,
    currency: str,
) -> Invoice:
    """Create an invoice for a successful payment (idempotent)."""
    # Check if invoice already exists for this payment
    existing = await db.execute(
        select(Invoice).where(Invoice.payment_id == payment_id)
    )
    if existing.scalar_one_or_none():
        result = await db.execute(
            select(Invoice).where(Invoice.payment_id == payment_id)
        )
        return result.scalar_one()

    # Generate sequential invoice number
    count_result = await db.execute(
        select(func.count(Invoice.id))
    )
    count = (count_result.scalar() or 0) + 1
    invoice_number = f"INV-{datetime.now(timezone.utc).strftime('%Y%m')}-{count:06d}"

    tax = 0  # Can be extended for GST
    total = amount - discount + tax

    invoice = Invoice(
        user_id=user_id,
        subscription_id=subscription_id,
        payment_id=payment_id,
        invoice_number=invoice_number,
        amount=amount,
        discount=discount,
        tax=tax,
        total_amount=total,
        currency=currency,
        status="paid",
    )
    db.add(invoice)
    await db.flush()
    return invoice


async def get_invoices(
    db: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Invoice], int]:
    count_result = await db.execute(
        select(func.count(Invoice.id))
        .where(Invoice.user_id == user_id)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Invoice)
        .where(Invoice.user_id == user_id)
        .order_by(Invoice.issued_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all()), total


async def get_invoice_by_id(
    db: AsyncSession,
    invoice_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Invoice | None:
    result = await db.execute(
        select(Invoice)
        .where(
            Invoice.id == invoice_id,
            Invoice.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


# ============================================================
# RAZORPAY SIGNATURE VERIFICATION
# ============================================================

def verify_razorpay_signature(
    order_id: str,
    payment_id: str,
    signature: str,
    secret: str,
) -> bool:
    """Verify Razorpay payment signature using HMAC SHA256."""
    message = f"{order_id}|{payment_id}"
    expected = hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_webhook_signature(
    body: bytes,
    signature: str,
    secret: str,
) -> bool:
    """Verify Razorpay webhook signature."""
    expected = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


# ============================================================
# SEED DEFAULT PLANS
# ============================================================

DEFAULT_PLANS = [
    {
        "name": "Free",
        "slug": "free",
        "description": "Get started with basic interview preparation tools",
        "price": 0,
        "currency": "INR",
        "billing_interval": "monthly",
        "duration_days": 36500,  # Essentially unlimited
        "sort_order": 0,
        "features": {
            "items": [
                "3 AI Mock Interviews per month",
                "5 Coding Problems per day",
                "2 Resume Analyses per month",
                "Basic Performance Analytics",
                "Question Practice Access",
                "Contest Participation",
            ]
        },
        "limits": {
            "ai_interviews_per_month": 3,
            "coding_problems_per_day": 5,
            "resume_analyses_per_month": 2,
            "contest_participation": True,
            "question_practice": True,
            "basic_analytics": True,
            "advanced_analytics": False,
            "priority_support": False,
        },
    },
    {
        "name": "Pro",
        "slug": "pro",
        "description": "Accelerate your preparation with advanced AI features",
        "price": 49900,  # ₹499
        "currency": "INR",
        "billing_interval": "monthly",
        "duration_days": 30,
        "sort_order": 1,
        "features": {
            "items": [
                "15 AI Mock Interviews per month",
                "Unlimited Coding Problems",
                "10 Resume Analyses per month",
                "Advanced Performance Analytics",
                "Weak Topic Radar",
                "Daily Practice Plans",
                "Personalized Learning Path",
                "Contest Participation",
                "Question Practice Access",
            ]
        },
        "limits": {
            "ai_interviews_per_month": 15,
            "coding_problems_per_day": 9999,
            "resume_analyses_per_month": 10,
            "contest_participation": True,
            "question_practice": True,
            "basic_analytics": True,
            "advanced_analytics": True,
            "priority_support": False,
        },
    },
    {
        "name": "Premium",
        "slug": "premium",
        "description": "Unlimited access to all platform capabilities",
        "price": 99900,  # ₹999
        "currency": "INR",
        "billing_interval": "monthly",
        "duration_days": 30,
        "sort_order": 2,
        "features": {
            "items": [
                "Unlimited AI Mock Interviews",
                "Unlimited Coding Problems",
                "Unlimited Resume Analyses",
                "Advanced Performance Analytics",
                "Weak Topic Radar",
                "Daily Practice Plans",
                "Personalized Learning Path",
                "Priority Support",
                "Contest Participation",
                "Question Practice Access",
                "All Future Features",
            ]
        },
        "limits": {
            "ai_interviews_per_month": 9999,
            "coding_problems_per_day": 9999,
            "resume_analyses_per_month": 9999,
            "contest_participation": True,
            "question_practice": True,
            "basic_analytics": True,
            "advanced_analytics": True,
            "priority_support": True,
        },
    },
]


async def seed_default_plans(db: AsyncSession) -> None:
    """Seed default subscription plans if they don't exist."""
    for plan_data in DEFAULT_PLANS:
        result = await db.execute(
            select(SubscriptionPlan)
            .where(SubscriptionPlan.slug == plan_data["slug"])
        )
        existing = result.scalar_one_or_none()
        if not existing:
            plan = SubscriptionPlan(**plan_data)
            db.add(plan)

    await db.commit()
