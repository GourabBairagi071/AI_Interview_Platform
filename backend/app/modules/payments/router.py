import json
import logging
from typing import Optional

import razorpay
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user, get_optional_current_user
from app.modules.auth.model import User
from app.modules.notifications.service import NotificationService
from app.modules.payments.schema import (
    CreateOrderRequest,
    CreateOrderResponse,
    CouponValidationResponse,
    InvoiceListResponse,
    InvoiceResponse,
    PaymentHistoryResponse,
    PaymentResponse,
    PlanResponse,
    SubscriptionResponse,
    UsageResponse,
    ValidateCouponRequest,
    VerifyPaymentRequest,
    VerifyPaymentResponse,
)
from app.modules.payments.service import (
    activate_subscription,
    cancel_subscription,
    create_invoice,
    create_payment_transaction,
    get_active_plans,
    get_current_plan,
    get_current_subscription,
    get_effective_limits,
    get_invoice_by_id,
    get_invoices,
    get_payment_by_id,
    get_payment_history,
    get_plan_by_id,
    get_transaction_by_order_id,
    get_transaction_by_payment_id,
    get_usage_stats,
    mark_payment_failed,
    mark_payment_paid,
    record_coupon_usage,
    validate_coupon,
    verify_razorpay_signature,
    verify_webhook_signature,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/payments",
    tags=["Payments & Subscriptions"],
)


def get_razorpay_client() -> razorpay.Client | None:
    """Create Razorpay client if credentials are configured."""
    key_id = getattr(settings, "razorpay_key_id", None)
    key_secret = getattr(settings, "razorpay_key_secret", None)
    if key_id and key_secret:
        return razorpay.Client(auth=(key_id, key_secret))
    return None


# ============================================================
# PLANS (public — no auth for listing)
# ============================================================

@router.get(
    "/plans",
    response_model=list[PlanResponse],
)
async def list_plans(
    db: AsyncSession = Depends(get_db),
):
    """Return all active subscription plans."""
    plans = await get_active_plans(db)
    return plans


# ============================================================
# CURRENT SUBSCRIPTION
# ============================================================

@router.get(
    "/subscription",
    response_model=SubscriptionResponse | None,
)
async def get_my_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's active subscription."""
    sub = await get_current_subscription(db, current_user.id)
    return sub


# ============================================================
# CREATE ORDER
# ============================================================

@router.post(
    "/create-order",
    response_model=CreateOrderResponse,
)
async def create_order(
    data: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Razorpay order for subscription purchase or direct amount."""
    plan = None
    discount = 0
    coupon_code = None

    if data.plan_id:
        # 1. Fetch and validate plan
        plan = await get_plan_by_id(db, data.plan_id)
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found",
            )

        if not plan.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This plan is no longer available",
            )

        if plan.price == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Free plan does not require payment",
            )

        original_amount = plan.price
        currency = plan.currency

        if data.coupon_code:
            coupon_result = await validate_coupon(
                db, data.coupon_code, data.plan_id, current_user.id
            )
            if not coupon_result["valid"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=coupon_result["message"],
                )
            discount = coupon_result["discount_amount"]
            coupon_code = data.coupon_code.upper().strip()

        final_amount = original_amount - discount

    elif data.amount is not None:
        # Direct amount order (minimum 100 paise = 1 INR)
        if data.amount < 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Amount must be at least 100 paise (₹1.00)",
            )
        original_amount = data.amount
        final_amount = data.amount
        currency = data.currency or "INR"

        # Associate with first active plan to satisfy database relation
        active_plans = await get_active_plans(db)
        plan = next((p for p in active_plans if p.price > 0), None)
        if not plan and active_plans:
            plan = active_plans[0]
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No active plan configured to link payment",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either plan_id or amount (minimum 100 paise) must be provided",
        )

    if final_amount < 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Calculated amount must be at least 100 paise",
        )

    # 2. Create Razorpay order via Razorpay API
    client = get_razorpay_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment provider is not configured. Please set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET.",
        )

    receipt = data.receipt or (f"sub_{current_user.id}_{plan.slug}" if plan else f"rcpt_{current_user.id}")
    # Razorpay receipt max length is 40 chars
    safe_receipt = receipt[:40]

    try:
        razorpay_order = client.order.create({
            "amount": final_amount,
            "currency": currency,
            "receipt": safe_receipt,
            "notes": {
                "user_id": str(current_user.id),
                "plan_id": str(plan.id) if plan else "",
                "plan_slug": plan.slug if plan else "",
            },
        })
    except Exception as exc:
        logger.error("Razorpay order creation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create payment order: {str(exc)}",
        ) from exc

    # 3. Store transaction in database
    txn = await create_payment_transaction(
        db=db,
        user_id=current_user.id,
        plan_id=plan.id,
        amount=final_amount,
        currency=currency,
        provider_order_id=razorpay_order["id"],
        metadata={
            "original_amount": original_amount,
            "discount": discount,
            "coupon_code": coupon_code,
            "receipt": safe_receipt,
        },
    )

    return CreateOrderResponse(
        order_id=razorpay_order["id"],
        amount=final_amount,
        currency=currency,
        razorpay_key_id=settings.razorpay_key_id,
        plan_name=plan.name if plan else "Standard Checkout",
        plan_slug=plan.slug if plan else "custom",
        original_amount=original_amount,
        discount=discount,
        transaction_id=txn.id,
    )


# ============================================================
# VERIFY PAYMENT
# ============================================================

@router.post(
    "/verify",
    response_model=VerifyPaymentResponse,
)
@router.post(
    "/verify-payment",
    response_model=VerifyPaymentResponse,
)
async def verify_payment(
    data: VerifyPaymentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify Razorpay payment and activate subscription."""
    # 1. Find the transaction
    txn = await get_transaction_by_order_id(db, data.razorpay_order_id)
    if not txn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    # Ensure user owns the transaction
    if txn.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Idempotency: already paid
    if txn.status == "paid":
        # Return existing data
        sub = await get_current_subscription(db, current_user.id)
        invoices_list, _ = await get_invoices(db, current_user.id, limit=1)
        return VerifyPaymentResponse(
            status="success",
            message="Payment already verified",
            payment=PaymentResponse.model_validate(txn),
            subscription=SubscriptionResponse.model_validate(sub) if sub else None,
            invoice=InvoiceResponse.model_validate(invoices_list[0]) if invoices_list else None,
        )

    # 2. Verify signature
    secret = getattr(settings, "razorpay_key_secret", "")
    if not verify_razorpay_signature(
        data.razorpay_order_id,
        data.razorpay_payment_id,
        data.razorpay_signature,
        secret,
    ):
        await mark_payment_failed(db, txn, "Signature verification failed")
        await NotificationService.create_notification(
            db=db,
            user_id=current_user.id,
            type="PAYMENT_FAILED",
            title="Payment Failed",
            message=f"Payment verification failed for transaction {txn.id}.",
            icon="⚠️",
            event_key=f"payment_fail_{txn.id}",
            action_url="/pricing",
            priority="high",
            commit=False,
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment verification failed — invalid signature",
        )

    # 3. Check for duplicate payment_id
    existing = await get_transaction_by_payment_id(db, data.razorpay_payment_id)
    if existing and existing.id != txn.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate payment detected",
        )

    # 4. Mark as paid
    await mark_payment_paid(
        db, txn, data.razorpay_payment_id, data.razorpay_signature
    )

    # 5. Activate subscription
    subscription = await activate_subscription(
        db, current_user.id, txn.plan_id, txn.id
    )

    # 6. Create invoice
    meta = txn.metadata_json or {}
    invoice = await create_invoice(
        db=db,
        user_id=current_user.id,
        payment_id=txn.id,
        subscription_id=subscription.id,
        amount=meta.get("original_amount", txn.amount),
        discount=meta.get("discount", 0),
        currency=txn.currency,
    )

    # 7. Record coupon usage
    coupon_code = meta.get("coupon_code")
    if coupon_code:
        await record_coupon_usage(
            db, coupon_code, current_user.id, txn.id,
            meta.get("discount", 0),
        )

    # 8. Notifications
    await NotificationService.create_notification(
        db=db,
        user_id=current_user.id,
        type="PAYMENT_SUCCESS",
        title="Payment Successful",
        message=f"Your payment of {txn.amount/100:.2f} {txn.currency} was processed successfully.",
        icon="💳",
        event_key=f"payment_succ_{txn.id}",
        action_url="/pricing",
        priority="normal",
        commit=False,
    )
    await NotificationService.create_notification(
        db=db,
        user_id=current_user.id,
        type="SUBSCRIPTION",
        title="Subscription Activated",
        message="Your subscription has been activated successfully! Enjoy all platform features.",
        icon="⭐",
        event_key=f"sub_act_{subscription.id}",
        action_url="/pricing",
        priority="normal",
        commit=False,
    )

    await db.commit()
    await db.refresh(txn)
    await db.refresh(subscription)
    await db.refresh(invoice)

    return VerifyPaymentResponse(
        status="success",
        message="Payment verified and subscription activated",
        payment=PaymentResponse.model_validate(txn),
        subscription=SubscriptionResponse.model_validate(subscription),
        invoice=InvoiceResponse.model_validate(invoice),
    )


# ============================================================
# WEBHOOK
# ============================================================

@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle Razorpay webhook events."""
    body = await request.body()
    signature = request.headers.get("x-razorpay-signature", "")

    webhook_secret = getattr(settings, "razorpay_webhook_secret", "")
    if webhook_secret and not verify_webhook_signature(body, signature, webhook_secret):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature",
        )

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON body",
        )

    event = payload.get("event", "")
    payment_entity = (
        payload.get("payload", {})
        .get("payment", {})
        .get("entity", {})
    )

    if event == "payment.captured":
        order_id = payment_entity.get("order_id")
        payment_id = payment_entity.get("id")

        if order_id and payment_id:
            txn = await get_transaction_by_order_id(db, order_id)
            if txn and txn.status != "paid":
                await mark_payment_paid(
                    db, txn, payment_id, "", payment_entity.get("method")
                )
                subscription = await activate_subscription(
                    db, txn.user_id, txn.plan_id, txn.id
                )
                meta = txn.metadata_json or {}
                await create_invoice(
                    db=db,
                    user_id=txn.user_id,
                    payment_id=txn.id,
                    subscription_id=subscription.id,
                    amount=meta.get("original_amount", txn.amount),
                    discount=meta.get("discount", 0),
                    currency=txn.currency,
                )
                coupon_code = meta.get("coupon_code")
                if coupon_code:
                    await record_coupon_usage(
                        db, coupon_code, txn.user_id, txn.id,
                        meta.get("discount", 0),
                    )
                await NotificationService.create_notification(
                    db=db,
                    user_id=txn.user_id,
                    type="PAYMENT_SUCCESS",
                    title="Payment Successful",
                    message=f"Your payment of {txn.amount/100:.2f} {txn.currency} was confirmed.",
                    icon="💳",
                    event_key=f"payment_succ_{txn.id}",
                    action_url="/pricing",
                    priority="normal",
                    commit=False,
                )
                await NotificationService.create_notification(
                    db=db,
                    user_id=txn.user_id,
                    type="SUBSCRIPTION",
                    title="Subscription Activated",
                    message="Your subscription has been activated successfully! Enjoy all platform features.",
                    icon="⭐",
                    event_key=f"sub_act_{subscription.id}",
                    action_url="/pricing",
                    priority="normal",
                    commit=False,
                )
                await db.commit()

    elif event == "payment.failed":
        order_id = payment_entity.get("order_id")
        if order_id:
            txn = await get_transaction_by_order_id(db, order_id)
            if txn:
                reason = (
                    payment_entity.get("error_description")
                    or payment_entity.get("error_reason")
                    or "Payment failed"
                )
                await mark_payment_failed(db, txn, reason)
                await NotificationService.create_notification(
                    db=db,
                    user_id=txn.user_id,
                    type="PAYMENT_FAILED",
                    title="Payment Failed",
                    message=f"Payment of {txn.amount/100:.2f} {txn.currency} failed: {reason}",
                    icon="⚠️",
                    event_key=f"payment_fail_{txn.id}",
                    action_url="/pricing",
                    priority="high",
                    commit=False,
                )
                await db.commit()

    return {"status": "ok"}


# ============================================================
# PAYMENT HISTORY
# ============================================================

@router.get(
    "/history",
    response_model=PaymentHistoryResponse,
)
async def payment_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Get payment history for the current user."""
    payments, total = await get_payment_history(
        db, current_user.id, limit, offset
    )
    return PaymentHistoryResponse(
        payments=[PaymentResponse.model_validate(p) for p in payments],
        total=total,
    )


# ============================================================
# INVOICES
# ============================================================

@router.get(
    "/invoices",
    response_model=InvoiceListResponse,
)
async def list_invoices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List all invoices for the current user."""
    invoices, total = await get_invoices(db, current_user.id, limit, offset)
    return InvoiceListResponse(
        invoices=[InvoiceResponse.model_validate(i) for i in invoices],
        total=total,
    )


@router.get(
    "/invoices/{invoice_id}",
    response_model=InvoiceResponse,
)
async def get_single_invoice(
    invoice_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific invoice."""
    import uuid as uuid_mod
    try:
        iid = uuid_mod.UUID(invoice_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invoice ID",
        )

    invoice = await get_invoice_by_id(db, iid, current_user.id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )
    return invoice


# ============================================================
# VALIDATE COUPON
# ============================================================

@router.post(
    "/validate-coupon",
    response_model=CouponValidationResponse,
)
async def validate_coupon_endpoint(
    data: ValidateCouponRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Validate a coupon code."""
    result = await validate_coupon(
        db, data.coupon_code, data.plan_id, current_user.id
    )
    return CouponValidationResponse(**result)


# ============================================================
# CANCEL SUBSCRIPTION
# ============================================================

@router.post(
    "/cancel-subscription",
    response_model=SubscriptionResponse | None,
)
async def cancel_my_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel the current user's active subscription."""
    sub = await cancel_subscription(db, current_user.id)
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription to cancel",
        )
    return sub


# ============================================================
# USAGE
# ============================================================

@router.get(
    "/usage",
    response_model=UsageResponse,
)
async def get_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current usage and limits."""
    plan = await get_current_plan(db, current_user.id)
    limits = get_effective_limits(plan)
    usage = await get_usage_stats(db, current_user.id)

    return UsageResponse(
        plan_name=plan.name if plan else "Free",
        plan_slug=plan.slug if plan else "free",
        limits=limits,
        current_usage=usage,
    )


# ============================================================
# SINGLE PAYMENT (declared last so it doesn't mask static routes)
# ============================================================

@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
)
async def get_payment(
    payment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific payment transaction."""
    import uuid as uuid_mod
    try:
        pid = uuid_mod.UUID(payment_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment ID",
        )

    payment = await get_payment_by_id(db, pid, current_user.id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )
    return payment

