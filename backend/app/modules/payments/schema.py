from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================
# SUBSCRIPTION PLAN
# ============================================================

class PlanResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str | None
    price: int
    currency: str
    billing_interval: str
    duration_days: int
    is_active: bool
    features: dict | None
    limits: dict | None
    sort_order: int

    model_config = {"from_attributes": True}


# ============================================================
# USER SUBSCRIPTION
# ============================================================

class SubscriptionResponse(BaseModel):
    id: UUID
    user_id: UUID
    plan_id: UUID
    status: str
    starts_at: datetime | None
    expires_at: datetime | None
    auto_renew: bool
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime
    plan: PlanResponse | None = None

    model_config = {"from_attributes": True}


# ============================================================
# PAYMENT TRANSACTION
# ============================================================

class PaymentResponse(BaseModel):
    id: UUID
    user_id: UUID
    subscription_id: UUID | None
    plan_id: UUID
    provider: str
    provider_order_id: str | None
    provider_payment_id: str | None
    amount: int
    currency: str
    status: str
    payment_method: str | None
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============================================================
# INVOICE
# ============================================================

class InvoiceResponse(BaseModel):
    id: UUID
    user_id: UUID
    subscription_id: UUID | None
    payment_id: UUID
    invoice_number: str
    amount: int
    discount: int
    tax: int
    total_amount: int
    currency: str
    status: str
    issued_at: datetime

    model_config = {"from_attributes": True}


# ============================================================
# REQUEST SCHEMAS
# ============================================================

class CreateOrderRequest(BaseModel):
    plan_id: UUID | None = None
    coupon_code: str | None = None
    amount: int | None = Field(default=None, description="Amount in paise (minimum 100)")
    currency: str = Field(default="INR", max_length=10)
    receipt: str | None = Field(default=None, max_length=100)


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str = Field(min_length=1)
    razorpay_payment_id: str = Field(min_length=1)
    razorpay_signature: str = Field(min_length=1)


class ValidateCouponRequest(BaseModel):
    coupon_code: str = Field(min_length=1, max_length=50)
    plan_id: UUID


# ============================================================
# RESPONSE SCHEMAS
# ============================================================

class CreateOrderResponse(BaseModel):
    order_id: str
    amount: int
    currency: str
    razorpay_key_id: str
    plan_name: str | None = None
    plan_slug: str | None = None
    original_amount: int | None = None
    discount: int = 0
    transaction_id: UUID | None = None


class VerifyPaymentResponse(BaseModel):
    status: str
    message: str
    payment: PaymentResponse | None = None
    subscription: SubscriptionResponse | None = None
    invoice: InvoiceResponse | None = None


class CouponValidationResponse(BaseModel):
    valid: bool
    message: str
    coupon_code: str | None = None
    discount_type: str | None = None
    discount_value: int | None = None
    original_amount: int | None = None
    discount_amount: int | None = None
    final_amount: int | None = None


class UsageResponse(BaseModel):
    plan_name: str
    plan_slug: str
    limits: dict | None
    current_usage: dict


class PaymentHistoryResponse(BaseModel):
    payments: list[PaymentResponse]
    total: int


class InvoiceListResponse(BaseModel):
    invoices: list[InvoiceResponse]
    total: int
