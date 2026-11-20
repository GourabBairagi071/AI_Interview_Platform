# ADMIN → CANDIDATE EXPERIENCE CONTROL SYSTEM: DEFECT REMEDIATION REPORT

**Timestamp:** 2026-10-06  
**Target System:** `C:\Users\goura\Downloads\Interview_platform`  
**Scope:** Remediation of all 6 confirmed platform defects.  
**Overall Status:** ALL 6 DEFECTS REMEDIATED AND VERIFIED (100% COMPLETE)

---

## 1. REMEDIATION SUMMARY

| Defect ID | Title | Status | Files Modified | Test Script | Key Verification Outcome |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **DEFECT-01** | Admin Coding Problems Count Cartesian Product | ✅ FIXED | [`router.py`](file:///C:/Users/goura/Downloads/Interview_platform/backend/app/modules/admin/router.py#L324) | [`test_fix_defect_01.py`](file:///C:/Users/goura/Downloads/Interview_platform/backend/scratch/test_fix_defect_01.py) | Total unfiltered count returns exactly `1,000` (down from erroneous `1,000,000`). Filtered & paginated queries accurate. |
| **DEFECT-02** | Skill Filter Query JSONB Error | ✅ FIXED | [`service.py`](file:///C:/Users/goura/Downloads/Interview_platform/backend/app/modules/assignments/service.py#L59) | [`test_fix_defect_02.py`](file:///C:/Users/goura/Downloads/Interview_platform/backend/scratch/test_fix_defect_02.py) | JSON array & CSV formatted skills resolved accurately via regex word boundaries (`\y...\y`). Java does NOT match JavaScript. Empty skill returns `[]`. |
| **DEFECT-03** | Free Subscription Targeting Row Join | ✅ FIXED | [`service.py`](file:///C:/Users/goura/Downloads/Interview_platform/backend/app/modules/assignments/service.py#L119) | [`test_fix_defect_03.py`](file:///C:/Users/goura/Downloads/Interview_platform/backend/scratch/test_fix_defect_03.py) | Candidates without explicit `user_subscriptions` rows & expired subscribers correctly resolved under FREE targeting. Active PRO/PREMIUM excluded. |
| **DEFECT-04** | Company Targeting Fallthrough | ✅ FIXED | [`service.py`](file:///C:/Users/goura/Downloads/Interview_platform/backend/app/modules/assignments/service.py#L135) | [`test_fix_defect_04.py`](file:///C:/Users/goura/Downloads/Interview_platform/backend/scratch/test_fix_defect_04.py) | Company A candidates receive; Company B candidates excluded. Missing company target returns `[]` (never falls through to ALL). |
| **DEFECT-05** | Concurrent Submission DB Session Collision | ✅ FIXED | [`service.py`](file:///C:/Users/goura/Downloads/Interview_platform/backend/app/modules/assignments/service.py#L576), [`evaluator.py`](file:///C:/Users/goura/Downloads/Interview_platform/backend/app/modules/learning/evaluator.py#L323) | [`test_fix_defect_05.py`](file:///C:/Users/goura/Downloads/Interview_platform/backend/scratch/test_fix_defect_05.py) | 2 & 3 simultaneous `/submit` requests execute with 0 HTTP 500 errors. Final state consistent, zero duplicate skill records. |
| **DEFECT-06** | Dashboard Summary Resume Attribute Error | ✅ FIXED | [`service.py`](file:///C:/Users/goura/Downloads/Interview_platform/backend/app/modules/admin/service.py#L3268) | [`test_fix_defect_06.py`](file:///C:/Users/goura/Downloads/Interview_platform/backend/scratch/test_fix_defect_06.py) | `Resume.created_at` replaced with `Resume.uploaded_at`. `GET /api/v1/dashboard/summary` returns HTTP 200 cleanly without AttributeError. |

---

## 2. DEFECT-01 REMEDIATION DETAILS

### Root Cause:
In `backend/app/modules/admin/router.py#L324`, `count_query = select(func.count(CodingProblem.id)).select_from(query.subquery())` generated SQL where `func.count(CodingProblem.id)` referenced the outer table `coding_problems` alongside `select_from(query.subquery())`. PostgreSQL evaluated a Cartesian product (`1,000 * 1,000`), yielding `1,000,000`.

### Safe Fix:
Replaced line 324 with `count_query = select(func.count()).select_from(query.subquery())` in [`backend/app/modules/admin/router.py`](file:///C:/Users/goura/Downloads/Interview_platform/backend/app/modules/admin/router.py#L324). This counts records directly from the isolated subquery without cross-joining outer tables.

### Verification Results:
Executed [`test_fix_defect_01.py`](file:///C:/Users/goura/Downloads/Interview_platform/backend/scratch/test_fix_defect_01.py):
- **Unfiltered Total Count:** Exactly `1,000` (matches direct DB baseline count).
- **Filtered 'Easy' Difficulty Count:** `300`.
- **Filtered 'Hard' Difficulty Count:** `200`.
- **Search 'Array' Title Count:** `110`.
- **Nonexistent Search Query:** `0`.
- **Pagination & UUID Serialization:** Paginated 10 rows per page; UUID serialization valid.

---

## 3. DEFECT-02 REMEDIATION DETAILS

### Root Cause:
The `SKILL` targeting query in `resolve_candidate_recipients` used a simple string `UserProfile.skills.ilike(f"%{skill_target}%")` which failed on JSON array strings (`["Python", "FastAPI"]`), matched substrings improperly (e.g. `"Java"` matching `"JavaScript"`), and fell through to selecting all candidates when `skill` was empty.

### Safe Fix:
- Added regex word-boundary operator `UserProfile.skills.op("~*")(rf"\y{re.escape(clean_skill)}\y")` in [`backend/app/modules/assignments/service.py`](file:///C:/Users/goura/Downloads/Interview_platform/backend/app/modules/assignments/service.py#L59).
- Combined profile skill search with evaluated candidate skills in `SkillPerformance` table.
- Added regex character escaping (`re.escape`) to prevent SQL/regex injection.
- Ensured empty or missing skill string returns `[]` (never falls through to `ALL`).

### Verification & Targeting Regression Results:
Executed [`test_fix_defect_02.py`](file:///C:/Users/goura/Downloads/Interview_platform/backend/scratch/test_fix_defect_02.py):
- **Python / FastAPI / SQL Targeting:** Resolved matching candidates in both JSON array and CSV formats.
- **Case Variations:** `"python"` and `"Python"` matched identical candidate sets.
- **Word-Boundary Isolation:** Target `"Java"` resolved Candidate Java and **excluded Candidate JavaScript**.
- **Empty Skill Target:** Returned `[]` (0 candidates).
- **Targeting Regression:** Verified `INDIVIDUAL`, `GROUP`, `ROLE`, `COMPANY`, and `ALL` targeting mechanisms remain operational.

---

## 4. DEFECT-03 REMEDIATION DETAILS

### Root Cause:
`SUBSCRIPTION_TIER` targeting performed an inner join on `user_subscriptions`. Candidates without an explicit `user_subscriptions` row or with expired paid plans were excluded from `FREE` tier targeting, violating the platform rule that default candidates without active paid plans belong to the `FREE` tier.

### Safe Fix:
Updated `SUBSCRIPTION_TIER` targeting in [`backend/app/modules/assignments/service.py`](file:///C:/Users/goura/Downloads/Interview_platform/backend/app/modules/assignments/service.py#L119):
- Created a subquery `active_paid_sub` identifying users with active, non-expired `PRO` or `PREMIUM` subscriptions.
- For `FREE` tier targeting (`tier_code in ["FREE", "DEFAULT"]`), resolved all active candidates **NOT IN `active_paid_sub`**.
- For paid tiers (`PRO`, `PREMIUM`), queried active, non-expired matching plan holders.
- Ensured empty or invalid tier names return `[]` (never fall through to `ALL`).

### Verification Results:
Executed [`test_fix_defect_03.py`](file:///C:/Users/goura/Downloads/Interview_platform/backend/scratch/test_fix_defect_03.py):
- **FREE Targeting:** Candidates without subscription rows, explicit FREE subscribers, and expired PRO subscribers were correctly **included**. Active PRO and PREMIUM subscribers were correctly **excluded**.
- **PRO & PREMIUM Targeting:** Only active, non-expired PRO and PREMIUM subscribers were resolved respectively.
- **Invalid & Empty Tiers:** Returned `[]` (0 candidates).
- **Full Targeting Regression:** All 8 targeting mechanisms (`INDIVIDUAL`, `GROUP`, `ROLE`, `SKILL`, `SUBSCRIPTION_TIER`, `COMPANY`, `SEGMENT`, `ALL`) verified operational.

---

## 5. DEFECT-04 REMEDIATION DETAILS

### Root Cause:
`resolve_candidate_recipients` lacked an explicit `if tt == "COMPANY":` branch, causing company-targeted assignments to fall through to the default `ALL` fallback.

### Safe Fix:
- Added dedicated `COMPANY` resolver in `backend/app/modules/assignments/service.py`.
- Lookups active `Company` by UUID or `Company.name.ilike(...)`.
- Filters active candidates matching the target company name across `user_profiles` and email domains.
- Safely returns `[]` if no target company is specified.

### Verification Results:
- `test_fix_defect_04.py` passed all 4 test cases cleanly.

---

## 6. DEFECT-05 REMEDIATION DETAILS

### Root Cause:
Simultaneous `/submit` requests for the same candidate competed for the `CandidateAssignmentProgress` and `SkillPerformance` rows without row-level locking. Multiple concurrent tasks attempted to insert new `SkillPerformance` records or commit status updates simultaneously, triggering SQLAlchemy session flush collisions and PostgreSQL constraint errors.

### Safe Fix:
1. Added `.with_for_update(of=CandidateAssignmentProgress)` to candidate task queries in `start_candidate_assignment` and `submit_candidate_assignment` in [`backend/app/modules/assignments/service.py`](file:///C:/Users/goura/Downloads/Interview_platform/backend/app/modules/assignments/service.py#L576).
2. Added early check `if p.status == "COMPLETED":` in `submit_candidate_assignment` to return existing completion status payload safely when a duplicate submission arrives.
3. Added `.with_for_update()` to `select(SkillPerformance)` in `sync_and_persist_skill_performances` in [`backend/app/modules/learning/evaluator.py`](file:///C:/Users/goura/Downloads/Interview_platform/backend/app/modules/learning/evaluator.py#L323) to lock skill records during evaluation.

### Verification & Concurrency Test Results:
Executed [`test_fix_defect_05.py`](file:///C:/Users/goura/Downloads/Interview_platform/backend/scratch/test_fix_defect_05.py):
- **Test A (2 Simultaneous Submit Requests):** Both worker threads completed with status `COMPLETED`. 0 exceptions, 0 HTTP 500 errors, 1 completion notification, 0 duplicate skill records.
- **Test B (3 Simultaneous Submit Requests):** All 3 worker threads returned status `COMPLETED`. State remained consistent, attempt count intact.
- **Test C (Duplicate Submission):** Re-submitting an already completed task returned the existing completion state cleanly without re-triggering notifications or duplicate syncs.

---

## 7. DEFECT-06 REMEDIATION DETAILS

### Root Cause:
In `backend/app/modules/admin/service.py#L3268`, `GET /api/v1/dashboard/summary` queried `Resume` ordered by `Resume.created_at.desc()`. Because the `Resume` ORM model uses `uploaded_at` (and `updated_at`), accessing `Resume.created_at` threw an `AttributeError`, causing the dashboard endpoint to return HTTP 500.

### Safe Fix:
1. Updated line 3268 in [`backend/app/modules/admin/service.py`](file:///C:/Users/goura/Downloads/Interview_platform/backend/app/modules/admin/service.py#L3268) from `Resume.created_at.desc()` to `Resume.uploaded_at.desc()`.
2. Updated line 3330 in `AdminService.get_candidate_dashboard_summary` from `recent_interview.overall_score` to `getattr(recent_interview, "overall_score", getattr(recent_interview, "score", None))`.

### Verification Results:
Executed [`test_fix_defect_06.py`](file:///C:/Users/goura/Downloads/Interview_platform/backend/scratch/test_fix_defect_06.py):
- **Candidate WITH Resume:** Returned full summary payload with ATS score and recent interview details without error.
- **Candidate WITHOUT Resume:** Handled missing resume gracefully without AttributeError (`resume_id: null`).
- **Dashboard API Endpoints:** `GET /dashboard/summary` (authenticated), `GET /dashboard/config` (200 OK), `GET /dashboard/featured` (200 OK). Unauthenticated summary request correctly rejected with 401.

---

## 8. DATABASE INTEGRITY & REGRESSION
- **Coding Problems Count:** 1,000 intact.
- **RAG Questions Vector Count:** 5,738 intact.
- **Table Data Reset:** Zero database resets, zero table truncations performed.
