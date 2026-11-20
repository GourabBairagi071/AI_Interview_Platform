import sys, os
sys.path.insert(0, os.path.abspath('.'))
import uuid
import hmac
import hashlib
import requests

BASE_URL = "http://127.0.0.1:8000/api/v1"

def print_test(num, desc, passed=True, extra=""):
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] Test {num}: {desc} {extra}")
    if not passed:
        sys.exit(1)

def main():
    print("==================================================")
    print("STARTING SUBSCRIPTION PLAN SIMPLIFICATION QA")
    print("==================================================")

    # 1. Candidate endpoint /payments/plans
    resp = requests.get(f"{BASE_URL}/payments/plans")
    assert resp.status_code == 200, f"Plans API failed: {resp.text}"
    plans = resp.json()

    print_test(1, "Candidate sees exactly 3 plans", len(plans) == 3, f"(got {len(plans)})")

    plan_by_slug = {p["slug"]: p for p in plans}

    print_test(2, "Free appears", "free" in plan_by_slug)
    print_test(3, "Pro appears", "pro" in plan_by_slug)
    print_test(4, "Premium appears", "premium" in plan_by_slug)

    extra_slugs = [slug for slug in plan_by_slug if slug not in ["free", "pro", "premium"]]
    print_test(5, "No extra plan appears", len(extra_slugs) == 0, f"(extra: {extra_slugs})")

    free_plan = plan_by_slug["free"]
    pro_plan = plan_by_slug["pro"]
    premium_plan = plan_by_slug["premium"]

    print_test(6, "Free price is INR 0", free_plan["price"] == 0, f"(price={free_plan['price']})")
    print_test(7, "Pro price is INR 499/month", pro_plan["price"] == 49900, f"(price={pro_plan['price']})")
    print_test(8, "Premium price is INR 999/month", premium_plan["price"] == 99900, f"(price={premium_plan['price']})")

    # Setup Candidate User
    rand = uuid.uuid4().hex[:6]
    candidate_email = f"qa_cand_{rand}@example.com"
    cand_reg = requests.post(f"{BASE_URL}/auth/register", json={
        "email": candidate_email,
        "full_name": "QA Candidate",
        "password": "Password@123",
        "role": "candidate"
    })
    assert cand_reg.status_code == 201, f"Candidate registration failed: {cand_reg.text}"

    cand_login = requests.post(f"{BASE_URL}/auth/login", json={
        "email": candidate_email,
        "password": "Password@123"
    })
    assert cand_login.status_code == 200, f"Candidate login failed: {cand_login.text}"
    token = cand_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 9. Free subscription / default quota works
    sub_resp = requests.get(f"{BASE_URL}/payments/subscription", headers=headers)
    print_test(9, "Free subscription / initial state works", sub_resp.status_code == 200)

    # 10. Pro checkout works (Razorpay order creation)
    pro_order_resp = requests.post(f"{BASE_URL}/payments/create-order", headers=headers, json={
        "plan_id": pro_plan["id"]
    })
    pro_order_data = pro_order_resp.json()
    print_test(10, "Pro checkout order creation works", 
               pro_order_resp.status_code == 200 and "order_id" in pro_order_data and pro_order_data["amount"] == 49900,
               f"(order_id={pro_order_data.get('order_id')})")

    # 11. Premium checkout works (Razorpay order creation)
    prem_order_resp = requests.post(f"{BASE_URL}/payments/create-order", headers=headers, json={
        "plan_id": premium_plan["id"]
    })
    prem_order_data = prem_order_resp.json()
    print_test(11, "Premium checkout order creation works",
               prem_order_resp.status_code == 200 and "order_id" in prem_order_data and prem_order_data["amount"] == 99900,
               f"(order_id={prem_order_data.get('order_id')})")

    # 12. Razorpay test mode & order response contains key_id
    print_test(12, "Razorpay test mode still works",
               "razorpay_key_id" in pro_order_data and pro_order_data["razorpay_key_id"].startswith("rzp_test_"))

    # 13. Coupon validation
    admin_login = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "admin@interviewplatform.ai",
        "password": "AdminPass123!"
    })
    assert admin_login.status_code == 200, "Admin login failed"
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    test_coupon_code = f"DISC_{rand}".upper()
    create_coupon_resp = requests.post(f"{BASE_URL}/admin/coupons", headers=admin_headers, json={
        "code": test_coupon_code,
        "discount_type": "PERCENTAGE",
        "discount_value": 20.0,
        "max_discount_inr": 500.0,
        "min_order_inr": 100.0,
        "valid_from": "2026-01-01T00:00:00Z",
        "valid_until": "2030-12-31T23:59:59Z",
        "usage_limit": 100
    })
    assert create_coupon_resp.status_code == 201, f"Coupon creation failed: {create_coupon_resp.text}"
    
    val_coupon_resp = requests.post(f"{BASE_URL}/payments/validate-coupon", headers=headers, json={
        "coupon_code": test_coupon_code,
        "plan_id": pro_plan["id"]
    })
    val_data = val_coupon_resp.json()
    print_test(13, "Coupon validation still works",
               val_coupon_resp.status_code == 200 and val_data.get("valid") is True and val_data.get("discount_amount") == 9980,
               f"(discount={val_data.get('discount_amount')})")

    # 14. Payment verification works & activates subscription
    from app.core.config import settings
    order_id = pro_order_data["order_id"]
    payment_id = f"pay_{uuid.uuid4().hex[:14]}"
    body = f"{order_id}|{payment_id}".encode("utf-8")
    valid_sig = hmac.new(settings.razorpay_key_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

    verify_resp = requests.post(f"{BASE_URL}/payments/verify", headers=headers, json={
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": valid_sig,
        "plan_id": pro_plan["id"]
    })
    verify_data = verify_resp.json()
    print_test(14, "Payment verification still works",
               verify_resp.status_code == 200 and verify_data.get("status") == "success" and verify_data.get("subscription") is not None)

    # 15. Invoice generation still works
    invoices_resp = requests.get(f"{BASE_URL}/payments/invoices", headers=headers)
    invoices_data = invoices_resp.json()
    invoices = invoices_data.get("invoices", [])
    print_test(15, "Invoice generation still works",
               invoices_resp.status_code == 200 and len(invoices) >= 1 and "invoice_number" in invoices[0],
               f"(invoice_count={len(invoices)})")

    # 16. Payment history still works
    hist_resp = requests.get(f"{BASE_URL}/payments/history", headers=headers)
    hist_data = hist_resp.json()
    payments_list = hist_data.get("payments", [])
    print('HIST PAYMENTS:', payments_list)
    print_test(16, 'Payment history still works',
               hist_resp.status_code == 200 and len(payments_list) >= 1 and any(p["amount"] == 49900 and p["status"] == "paid" for p in payments_list))

    # 17. Subscription status works
    my_sub_resp = requests.get(f"{BASE_URL}/payments/subscription", headers=headers)
    my_sub = my_sub_resp.json()
    print_test(17, "Subscription status works",
               my_sub_resp.status_code == 200 and my_sub is not None and my_sub["status"] == "active" and my_sub["plan"]["slug"] == "pro")

    # 18. Quotas enforcement / limits work
    usage_resp = requests.get(f"{BASE_URL}/payments/usage", headers=headers)
    usage = usage_resp.json()
    print_test(18, "Quotas still work",
               usage_resp.status_code == 200 and usage["plan_slug"] == "pro" and usage["limits"]["ai_interviews_per_month"] == 15)

    # 19. Admin payment dashboard still works
    admin_plans_resp = requests.get(f"{BASE_URL}/admin/subscriptions/plans", headers=admin_headers)
    admin_txns_resp = requests.get(f"{BASE_URL}/admin/payments?page=1&page_size=5", headers=admin_headers)
    print_test(19, "Admin payment dashboard still works",
               admin_plans_resp.status_code == 200 and admin_txns_resp.status_code == 200 and len(admin_plans_resp.json()) >= 3,
               f"(admin_plans_count={len(admin_plans_resp.json())})")

    # 20. Existing users are not corrupted
    user_test = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    print_test(20, "Existing users are not corrupted",
               user_test.status_code == 200 and user_test.json()["email"] == candidate_email)

    print("\n==================================================")
    print("ALL 20 VERIFICATION CHECKS PASSED PERFECTLY!")
    print("==================================================")

if __name__ == "__main__":
    main()