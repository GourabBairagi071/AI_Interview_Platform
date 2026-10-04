import asyncio
import hmac
import hashlib
import json
import httpx
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import create_access_token
from app.modules.auth.model import User
from app.modules.payments.model import SubscriptionPlan, UserSubscription, PaymentTransaction, Invoice, Coupon
from app.modules.payments.service import (
    verify_razorpay_signature,
    verify_webhook_signature,
    check_quota,
    get_usage_stats,
    activate_subscription,
    create_invoice,
    validate_coupon,
)

BASE_URL = "http://127.0.0.1:8000"

async def test_payments_system():
    print("\n==================================================")
    print("PHASE 14 — PAYMENT & SUBSCRIPTION SYSTEM VERIFICATION")
    print("==================================================")

    # 1. Fetch a test user from database
    async with AsyncSessionLocal() as db:
        user_stmt = select(User).limit(1)
        user = (await db.execute(user_stmt)).scalar_one_or_none()
        assert user is not None, "No user found in database for authentication test"
        user_id = user.id
        token = create_access_token(str(user.id))
        headers = {"Authorization": f"Bearer {token}"}
        print(f"[OK] Found test user: {user.email} (ID: {user_id})")

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        # 1. Test GET /api/v1/payments/plans (Public)
        r = await client.get("/api/v1/payments/plans")
        assert r.status_code == 200, f"Failed /payments/plans: {r.status_code} - {r.text}"
        plans = r.json()
        print(f"[OK] 1. Public Plans API: Found {len(plans)} active plans: {[p['name'] for p in plans]}")
        assert len(plans) >= 3, "Expected at least 3 plans (Free, Pro, Premium)"
        free_plan = next(p for p in plans if p["slug"] == "free")
        pro_plan = next(p for p in plans if p["slug"] == "pro")
        premium_plan = next(p for p in plans if p["slug"] == "premium")
        assert free_plan["price"] == 0
        assert pro_plan["price"] == 49900  # Rs. 499
        assert premium_plan["price"] == 99900  # Rs. 999

        # 2. Test GET /api/v1/payments/subscription (Protected)
        r = await client.get("/api/v1/payments/subscription", headers=headers)
        assert r.status_code == 200, f"Failed /payments/subscription: {r.status_code}"
        sub = r.json()
        print(f"[OK] 2. Current User Subscription: {sub['status'] if sub else 'Free Tier (Default)'}")

        # 3. Test GET /api/v1/payments/usage (Protected)
        r = await client.get("/api/v1/payments/usage", headers=headers)
        assert r.status_code == 200, f"Failed /payments/usage: {r.status_code}"
        usage = r.json()
        print(f"[OK] 3. Usage & Quotas: Plan = {usage['plan_name']}, AI Interviews limit = {usage['limits'].get('ai_interviews_per_month')}")
        assert "limits" in usage
        assert "current_usage" in usage

        # 4. Test POST /api/v1/payments/validate-coupon
        r = await client.post(
            "/api/v1/payments/validate-coupon",
            headers=headers,
            json={"coupon_code": "WELCOME50", "plan_id": pro_plan["id"]},
        )
        assert r.status_code == 200, f"Failed /payments/validate-coupon: {r.status_code}"
        coupon_res = r.json()
        print(f"[OK] 4. Coupon Validation (WELCOME50 on Pro Plan): Valid={coupon_res['valid']}, Discount=Rs.{coupon_res['discount_amount']/100}, Final=Rs.{coupon_res['final_amount']/100}")
        assert coupon_res["valid"] is True
        assert coupon_res["discount_amount"] > 0

        # 5. Test GET /api/v1/payments/invoices (Protected)
        r = await client.get("/api/v1/payments/invoices", headers=headers)
        assert r.status_code == 200, f"Failed /payments/invoices: {r.status_code}"
        invoices = r.json()
        print(f"[OK] 5. Invoices Endpoint: Total invoices = {invoices['total']}")

        # 6. Test GET /api/v1/payments/history (Protected)
        r = await client.get("/api/v1/payments/history", headers=headers)
        assert r.status_code == 200, f"Failed /payments/history: {r.status_code}"
        history = r.json()
        print(f"[OK] 6. Payment History Endpoint: Total transactions = {history['total']}")

        # 7. Test POST /api/create-order - Auth validation (401 without token)
        r_unauth = await client.post("/api/create-order", json={"amount": 50000})
        assert r_unauth.status_code == 401, f"Expected 401 unauthenticated, got {r_unauth.status_code}"
        print("[OK] 7. Create Order Auth: Correctly rejected unauthenticated request with 401")

        # 8. Test POST /api/create-order - Amount validation (< 100 paise)
        r_low_amt = await client.post("/api/create-order", headers=headers, json={"amount": 50})
        assert r_low_amt.status_code == 400, f"Expected 400 for amount < 100 paise, got {r_low_amt.status_code}"
        print("[OK] 8. Create Order Validation: Correctly rejected amount < 100 paise with 400")

        # 9. Test POST /api/create-order - Real Razorpay API Order Creation
        r_order = await client.post(
            "/api/create-order",
            headers=headers,
            json={"amount": 50000, "currency": "INR", "receipt": "test_order_101"}
        )
        assert r_order.status_code == 200, f"Failed /api/create-order: {r_order.status_code} - {r_order.text}"
        order_res = r_order.json()
        print(f"[OK] 9. Razorpay API Create Order: Generated Order ID={order_res['order_id']}, Amount=Rs.{order_res['amount']/100}")
        assert order_res["order_id"].startswith("order_"), f"Unexpected order_id format: {order_res['order_id']}"
        assert order_res["amount"] == 50000
        assert order_res["currency"] == "INR"

        created_order_id = order_res["order_id"]

        # 10. Test POST /api/verify-payment - Invalid signature (400)
        r_invalid_sig = await client.post(
            "/api/verify-payment",
            headers=headers,
            json={
                "razorpay_order_id": created_order_id,
                "razorpay_payment_id": "pay_test_random_123",
                "razorpay_signature": "fake_invalid_signature_hex",
            }
        )
        assert r_invalid_sig.status_code == 400, f"Expected 400 for invalid signature, got {r_invalid_sig.status_code}"
        print("[OK] 10. Verify Payment Mismatch: Correctly rejected invalid signature with 400")

        # 11. Test POST /api/verify-payment - Valid HMAC-SHA256 signature
        from app.core.config import settings
        import uuid as uuid_mod
        test_payment_id = f"pay_test_{uuid_mod.uuid4().hex[:8]}"
        message = f"{created_order_id}|{test_payment_id}"
        expected_sig = hmac.new(
            settings.razorpay_key_secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

        r_valid_sig = await client.post(
            "/api/verify-payment",
            headers=headers,
            json={
                "razorpay_order_id": created_order_id,
                "razorpay_payment_id": test_payment_id,
                "razorpay_signature": expected_sig,
            }
        )
        assert r_valid_sig.status_code == 200, f"Failed verify with valid signature: {r_valid_sig.status_code} - {r_valid_sig.text}"
        verify_res = r_valid_sig.json()
        print(f"[OK] 11. Verify Payment Success: Status={verify_res['status']}, Message='{verify_res['message']}'")
        assert verify_res["status"] == "success"

    # 7. Unit logic testing: Signature verification
    order_id = "order_test_12345"
    payment_id = "pay_test_67890"
    secret = "test_razorpay_secret_key"
    msg = f"{order_id}|{payment_id}"
    valid_sig = hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
    assert verify_razorpay_signature(order_id, payment_id, valid_sig, secret) is True
    assert verify_razorpay_signature(order_id, payment_id, "invalid_sig", secret) is False
    print("[OK] 7. HMAC-SHA256 Signature verification: Verified and tamper-proof")

    # 8. Webhook signature verification
    payload_body = b'{"event":"payment.captured"}'
    webhook_secret = "whsec_test_secret"
    wh_sig = hmac.new(webhook_secret.encode(), payload_body, hashlib.sha256).hexdigest()
    assert verify_webhook_signature(payload_body, wh_sig, webhook_secret) is True
    assert verify_webhook_signature(payload_body, "tampered", webhook_secret) is False
    print("[OK] 8. Razorpay Webhook HMAC verification: Verified")

    # 9. Quota Check Logic
    async with AsyncSessionLocal() as db:
        allowed, reason = await check_quota(db, user_id, "ai_interview")
        print(f"[OK] 9. Subscription Quota Check: Allowed={allowed}, Message='{reason}'")

        # 10. Idempotent Invoice generation verification
        inv_plan = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.slug == "pro"))
        plan_obj = inv_plan.scalar_one()

        # Create a test transaction
        import uuid as uuid_mod
        rnd = uuid_mod.uuid4().hex[:8]
        test_tx = PaymentTransaction(
            user_id=user_id,
            plan_id=plan_obj.id,
            provider="razorpay",
            provider_order_id=f"order_unit_{rnd}",
            provider_payment_id=f"pay_unit_{rnd}",
            amount=49900,
            currency="INR",
            status="paid",
        )
        db.add(test_tx)
        await db.flush()

        test_sub = await activate_subscription(db, user_id, plan_obj.id, test_tx.id)
        assert test_sub.status == "active"
        print(f"[OK] 10. Subscription Activation: Sub ID={test_sub.id}, Status={test_sub.status}")

        test_invoice = await create_invoice(
            db=db,
            user_id=user_id,
            payment_id=test_tx.id,
            subscription_id=test_sub.id,
            amount=49900,
            discount=0,
            currency="INR",
        )
        assert test_invoice.invoice_number.startswith("INV-")
        assert test_invoice.total_amount == 49900
        print(f"[OK] 11. Invoice Generation: Number={test_invoice.invoice_number}, Total=Rs.{test_invoice.total_amount/100}")

        await db.commit()

    print("\n==================================================")
    print("ALL PHASE 14 VERIFICATIONS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(test_payments_system())
