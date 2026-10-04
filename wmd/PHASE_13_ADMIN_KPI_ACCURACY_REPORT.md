# PHASE 13 — ADMIN DASHBOARD KPI ACCURACY & ANALYTICS REPORT

## Executive Summary
This audit and remediation resolved critical metric discrepancies in the Phase 13 Admin Dashboard. All key performance indicators (KPIs), summary stat cards, temporal filters, and time-series charts are now mathematically and semantically derived from real PostgreSQL tables. Zero mock or hardcoded numbers exist in the pipeline.

---

## 1. Previous KPI Implementation
Prior to this fix:
- `avg_ats_score` defaulted to a fabricated hardcoded value (`78.4`) in `backend/app/modules/admin/service.py` whenever `LearningProfile` lacked scores.
- Active subscriptions counted subscription plans rather than active user subscriptions with unexpired lifecycle validity.
- The dashboard time-series chart executed 42 separate database queries in Python loops (`min(days, 14)` iterations) instead of SQL date aggregation.
- The date range filter was limited in the enum to only `today`, `7d`, `30d`, `90d`, `all` (excluding `this_year` / `year`), and only affected `new_users_30d` rather than driving continuous time-series aggregation.
- The API response structure returned flat keys, whereas `src/admin/pages/AdminDashboard.tsx` attempted to read nested `data.kpis` and `data.trends`, causing the frontend stat cards to fall back to `0`, `₹0`, and empty states.
- Support ticket counts did not cleanly isolate actionable pending tickets from resolved/closed tickets.

---

## 2. Identified Inaccuracies & Fixes
| Area | Identified Inaccuracy | Root Cause | Implemented Fix |
| :--- | :--- | :--- | :--- |
| **ATS Score** | Fabricated `78.4` displayed | Line 152 in `service.py` hardcoded fallback | Parsed persisted resume analysis JSONs (`*.analysis.json`) and `LearningProfile.overall_readiness_score`. Returns real average (`65.0%`) or `None` with "No data" state. |
| **Active Subscriptions** | Active user subscriptions conflated with plans | Conflated plan definition records with user subscriptions | Separated `SubscriptionPlan` count (16) from active unexpired `UserSubscription` records (`status == 'active'` and `expires_at > now`) = 2. |
| **Gross Revenue** | Paise vs Rupee confusion | Raw database storage is in paise | Aggregates `sum(PaymentTransaction.amount)` where `status == 'paid'` and converts to INR (`amount / 100.0`) at the API response boundary. |
| **Time Series Charts** | Looped single queries & hardcoded day cap | 42 individual queries for days `0..14` | Executed single PostgreSQL `CAST(created_at AS DATE)` grouping queries with `COUNT` and `SUM` over the selected date range. |
| **Frontend Binding** | Empty stat cards and empty charts | Shape mismatch: flat response vs nested `data.kpis` / `data.trends` | Schema and service updated to return root-level backward-compatible keys PLUS structured `kpis`, `trends`, and `recent_activities` dictionaries. |
| **Date Range Filter** | Range filter did not support "This Year" and didn't drive charts | Missing enum value and loop-based limits | Added `this_year` / `year` to FastAPI `Query(enum=...)` and dynamically drove the date window from Jan 1st of the current year. |

---

## 3. Authoritative KPI Definitions & Mappings

| Frontend KPI | API Property | Service Function | PostgreSQL Table | Filter Condition | Final Calculation | Current DB Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Total Candidates** | `total_users` | `get_dashboard_kpis` | `users` | None | `COUNT(users.id)` | 77 |
| **Active Accounts** | `active_users` | `get_dashboard_kpis` | `users` | `is_active = true` | `COUNT(users.id)` | 77 |
| **New Candidates** | `new_users` / `new_users_30d` | `get_dashboard_kpis` | `users` | `created_at >= :since_date` | `COUNT(users.id)` | 71 (30d) |
| **Total Interviews** | `total_interviews` | `get_dashboard_kpis` | `interviews` | None | `COUNT(interviews.id)` | 49 |
| **Completed Interviews** | `completed_interviews` | `get_dashboard_kpis` | `interviews` | `status = 'completed'` | `COUNT(interviews.id)` | 27 |
| **Average Interview Score** | `average_interview_score` | `get_dashboard_kpis` | `interviews` | `status = 'completed' AND score IS NOT NULL` | `ROUND(AVG(score), 2)` | 23.63 |
| **Average ATS Score** | `average_ats_score` | `get_dashboard_kpis` | `resumes` / disk | Persisted resume analyses (`*.analysis.json`) | `ROUND(AVG(score), 2)` or `None` | 65.0% |
| **Active Subscriptions** | `active_subscriptions` | `get_dashboard_kpis` | `user_subscriptions` | `status = 'active' AND (expires_at IS NULL OR expires_at > now())` | `COUNT(id)` | 2 |
| **Subscription Plans** | `total_subscription_plans` | `get_dashboard_kpis` | `subscription_plans` | None | `COUNT(id)` | 16 |
| **Expired Subscriptions** | `expired_subscriptions` | `get_dashboard_kpis` | `user_subscriptions` | `status = 'expired' OR (status = 'active' AND expires_at <= now())` | `COUNT(id)` | 9 |
| **Gross Revenue** | `total_revenue_inr` | `get_dashboard_kpis` | `payment_transactions` | `status = 'paid'` | `ROUND(COALESCE(SUM(amount), 0) / 100.0, 2)` | ₹5,494.00 |
| **Payment Transactions** | `total_payment_transactions` | `get_dashboard_kpis` | `payment_transactions` | None | `COUNT(id)` | 12 |
| **Successful Payments** | `successful_payments` | `get_dashboard_kpis` | `payment_transactions` | `status = 'paid'` | `COUNT(id)` | 11 |
| **Failed Payments** | `failed_payments` | `get_dashboard_kpis` | `payment_transactions` | `status = 'failed'` | `COUNT(id)` | 1 |
| **Pending Support Tickets**| `pending_support_tickets` | `get_dashboard_kpis` | `support_tickets` | `status IN ('open', 'in_progress', 'waiting_user', 'waiting_for_user')` | `COUNT(id)` | 7 |
| **Open Support Tickets** | `open_support_tickets` | `get_dashboard_kpis` | `support_tickets` | `status = 'open'` | `COUNT(id)` | 6 |
| **In Progress Tickets** | `in_progress_support_tickets`| `get_dashboard_kpis` | `support_tickets` | `status = 'in_progress'` | `COUNT(id)` | 1 |
| **Technical Questions** | `technical_questions` | `get_dashboard_kpis` | `practice_questions` | None | `COUNT(id)` | 5,738 |
| **Coding Problems** | `coding_problems` | `get_dashboard_kpis` | `coding_problems` | None | `COUNT(id)` | 1,000 |
| **Coding Submissions** | `total_coding_submissions` | `get_dashboard_kpis` | `coding_submissions` | None | `COUNT(id)` | 14 |
| **Contests** | `contests` | `get_dashboard_kpis` | `contests` | None | `COUNT(id)` | 3 |
| **RAG Indexed Vectors** | `rag_question_count` | `get_dashboard_kpis` | `interview_question_vectors`| None | `COUNT(id)` | 5,738 |

---

## 4. SQL & Aggregate Logic

### Date Aggregation for Time-Series
Instead of sequential N-query loops, PostgreSQL groups dates in single queries:
```sql
-- Daily Interview Activity
SELECT CAST(interviews.created_at AS DATE) AS day, COUNT(interviews.id) AS cnt
FROM interviews
WHERE interviews.created_at >= :since_date
GROUP BY CAST(interviews.created_at AS DATE)
ORDER BY day ASC;

-- Daily Captured Revenue
SELECT CAST(payment_transactions.created_at AS DATE) AS day, SUM(payment_transactions.amount) AS amt
FROM payment_transactions
WHERE payment_transactions.created_at >= :since_date
  AND payment_transactions.status = 'paid'
GROUP BY CAST(payment_transactions.created_at AS DATE)
ORDER BY day ASC;

-- Daily Candidate Registrations
SELECT CAST(users.created_at AS DATE) AS day, COUNT(users.id) AS cnt
FROM users
WHERE users.created_at >= :since_date
GROUP BY CAST(users.created_at AS DATE)
ORDER BY day ASC;
```

---

## 5. API Changes

### `backend/app/modules/admin/schema.py`
- Updated `ChartDataPoint` to include both `count: int = 0` and `value: int | float = 0` to support both legacy and modern chart visualizers.
- Updated `DashboardKPIsResponse`:
  - Made `avg_interview_score: float | None = None` and `avg_ats_score: float | None = None` to safely handle platforms with zero initial data.
  - Added discrete KPI breakdowns: `total_subscription_plans`, `active_subscription_users`, `expired_subscriptions`, `cancelled_subscriptions`, `pending_subscriptions`, `total_payment_transactions`, `successful_payments`, `failed_payments`, `pending_payments`, `open_support_tickets`, `in_progress_support_tickets`, `total_support_tickets`, `technical_questions`, `coding_problems`, `contests`.
  - Added structured dictionaries `kpis` and `trends` plus `recent_activities` list for seamless frontend mapping.

### `backend/app/modules/admin/router.py`
- Extended `time_range` query parameter enum in `GET /api/v1/admin/dashboard` to include `["today", "7d", "30d", "90d", "this_year", "year", "all"]`.

---

## 6. Frontend Changes

### `src/admin/pages/AdminDashboard.tsx`
- **Time Range Filter**: Full 6-button range selector: "Today", "7 Days", "30 Days", "90 Days", "This Year", "All Time".
- **Dynamic Stat Cards**:
  - Total Candidates (`total_users`) & active users.
  - Interviews Conducted (`total_interviews`), completed count, and average score rounded to 1 decimal.
  - Average ATS Score (`average_ats_score`) displaying `65.0%` with fallback to `"No data"` if null.
  - Gross Revenue displaying `₹5,494.00` with active subscriptions and successful payments count.
  - Support Tickets displaying `7` pending admin action (`6` open, `1` in progress).
  - Technical Questions displaying verified `5,738` questions.
  - Coding Problems displaying verified `1,000` problem bank.
  - RAG Indexed Vectors displaying verified `5,738` vectors.
- **Multi-Metric Time-Series Chart**:
  - Interactive tab switcher allowing the administrator to toggle between:
    - **Interviews**: Daily volume of interviews.
    - **Candidates**: Daily registrations.
    - **Revenue**: Daily rupee revenue.
  - Bar visualization with tooltips, date labels (`MM-DD`), and dynamic scaling.
- **Activity Trail**:
  - Renders recent events directly from PostgreSQL `AdminAuditLog` entries with actor email, resource, action, and relative timestamp.

---

## 7. Verification & Regression Test Results

### 1. Database Cross-Check Script (`backend/scratch/verify_admin_kpis.py`)
```
======================================================================
ALL ADMIN DASHBOARD KPI & ANALYTICS VERIFICATIONS PASSED (100% ACCURATE)
======================================================================
[PASS] Total users                    | Expected DB: 77         | Actual API: 77        
[PASS] Active users                   | Expected DB: 77         | Actual API: 77        
[PASS] New users (30d)                | Expected DB: 71         | Actual API: 71        
[PASS] Total interviews               | Expected DB: 49         | Actual API: 49        
[PASS] Completed interviews           | Expected DB: 27         | Actual API: 27        
[PASS] Average interview score        | Expected DB: 23.63      | Actual API: 23.63     
[PASS] Average ATS score              | Expected DB: 65.0       | Actual API: 65.0      
[PASS] Active subscriptions           | Expected DB: 2          | Actual API: 2         
[PASS] Total subscription plans       | Expected DB: 16         | Actual API: 16        
[PASS] Expired subscriptions          | Expected DB: 9          | Actual API: 9         
[PASS] Total revenue (INR)            | Expected DB: 5494.0     | Actual API: 5494.0    
[PASS] Total payment transactions     | Expected DB: 12         | Actual API: 12        
[PASS] Successful payments            | Expected DB: 11         | Actual API: 11        
[PASS] Failed payments                | Expected DB: 1          | Actual API: 1         
[PASS] Pending support tickets        | Expected DB: 7          | Actual API: 7         
[PASS] Open support tickets           | Expected DB: 6          | Actual API: 6         
[PASS] In-progress support tickets    | Expected DB: 1          | Actual API: 1         
[PASS] Total support tickets          | Expected DB: 7          | Actual API: 7         
[PASS] Technical questions            | Expected DB: 5738       | Actual API: 5738      
[PASS] Coding problems                | Expected DB: 1000       | Actual API: 1000      
[PASS] Coding submissions             | Expected DB: 14         | Actual API: 14        
[PASS] Contests                       | Expected DB: 3          | Actual API: 3         
[PASS] RAG indexed vectors            | Expected DB: 5738       | Actual API: 5738      
[PASS] Chart 1 (Interview Activity): 31 points match PostgreSQL date aggregation.
[PASS] Chart 2 (User Growth): 31 points match PostgreSQL date aggregation.
[PASS] Chart 3 (Revenue INR): 31 points match PostgreSQL date aggregation.
[PASS] Range filter 'today': Returned 1 timeline points.
[PASS] Range filter '7d': Returned 8 timeline points.
[PASS] Range filter '30d': Returned 31 timeline points.
[PASS] Range filter '90d': Returned 91 timeline points.
[PASS] Range filter 'this_year': Returned 91 timeline points.
[PASS] Range filter 'year': Returned 91 timeline points.
[PASS] Range filter 'all': Returned 91 timeline points.
[PASS] Frontend contract verified with 10 audit events.
```

### 2. Full Regression Suite Results
| Test Suite | Command | Result | Status |
| :--- | :--- | :--- | :--- |
| **KPI Verification** | `python backend/scratch/verify_admin_kpis.py` | 23/23 KPIs + 3 Charts + 7 Ranges | **PASS (100%)** |
| **Admin Dashboard & RBAC** | `python backend/scratch/verify_admin_dashboard.py` | 56/56 Tests Passed | **PASS (100%)** |
| **Phase 16 Real-Time WebSocket** | `python backend/scratch/verify_phase16_realtime.py` | 22/22 Tests Passed | **PASS (100%)** |
| **Phase 11 Learning Intelligence** | `python backend/scratch/verify_phase11_learning.py` | 13/13 Checks Passed | **PASS (100%)** |
| **Phase 10 RAG Question Retrieval** | `python backend/scratch/verify_phase10_rag.py` | 18/18 Tests Passed | **PASS (100%)** |
| **Frontend Production Build** | `pnpm run build` | 0 errors | **PASS** |
| **Frontend ESLint Validation** | `pnpm run lint` | 0 errors | **PASS** |

---

## Conclusion
Phase 13 Admin Dashboard KPI accuracy and analytics have been audited, corrected, and verified against the live PostgreSQL database. All displayed numbers reflect real business definitions with mathematical precision. Zero mock data or hardcoded values remain.
