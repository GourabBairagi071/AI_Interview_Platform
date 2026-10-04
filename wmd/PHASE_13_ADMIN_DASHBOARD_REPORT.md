# PHASE 13 — PRODUCTION ADMIN DASHBOARD & RBAC CONTROL CENTER
## AI-Powered Intelligent Interview and Career Preparation Platform

---

### EXECUTIVE SUMMARY

Phase 13 delivers the complete, production-grade **Admin Dashboard & RBAC Management Console** for the platform. This implementation is entirely non-destructive, fully additive, backed exclusively by real PostgreSQL persistence, and tightly unified with all prior platform modules:

- **Authentication & User Management** (Phase 1)
- **Resume Intelligence & ATS Scoring** (Phase 2)
- **Adaptive AI Interview & Evaluation** (Phases 3–5)
- **AI Avatar & Voice Synthesis** (Phase 6)
- **Anti-Cheating & Proctoring** (Phase 7)
- **Coding Arena & 1,000 Coding Problems** (Phase 8)
- **Competitive Coding & Live Contests** (Phase 8D)
- **Technical Question Bank** (Phase 9)
- **RAG & Hybrid Semantic Retrieval** (Phase 10)
- **Adaptive Learning Intelligence & Skill Retention** (Phase 11)
- **Achievements, Notifications & Profile Dossier** (Phases 12–13)
- **Razorpay Payments & Subscription Billing** (Phase 14)
- **Support, Help Desk & User Feedback** (Phase 15)
- **Real-Time WebSocket & Event-Driven Notification Layer** (Phase 16)

---

### ARCHITECTURE & RBAC DESIGN

```
┌────────────────────────────────────────────────────────────────────────┐
│                   VITE + REACT 19 ADMIN CONSOLE                        │
│   src/admin/layouts/AdminLayout.tsx + AdminSidebar + AdminHeader      │
│   25 Dedicated Management Pages with Glassmorphic Dark Design         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Bearer JWT + AdminGuard
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                 FASTAPI ADMIN MODULE (/api/v1/admin/*)                 │
│      require_permission("...") FastAPI Dependency Injection            │
│      AdminService with Aggregate PostgreSQL Queries & Audit Logging    │
└──────────────────┬─────────────────┬───────────────────┬───────────────┘
                   │                 │                   │
                   ▼                 ▼                   ▼
           ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
           │  PostgreSQL  │  │ Realtime WS  │  │ Vector Search    │
           │  (Alembic    │  │ Event Bus    │  │ (Interview Qs    │
           │  Migrations) │  │ Broadcasts   │  │ Embeddings)      │
           └──────────────┘  └──────────────┘  └──────────────────┘
```

#### RBAC Roles & Fine-Grained Permissions
The system enforces 8 distinct operational roles mapped to 36 fine-grained permissions:
1. `SUPER_ADMIN`: Full unrestricted clearance across all systems and settings. Self-lockout protection built-in.
2. `ADMIN`: Broad administrative clearance across users, questions, companies, resources, payments, support, and audit logs.
3. `INTERVIEW_ADMIN`: Specializes in interview monitoring, rubrics, questions, and RAG search indexing.
4. `CONTENT_ADMIN`: Curates practice questions, companies, and learning roadmaps.
5. `SUPPORT_AGENT`: Resolves candidate support tickets, adds internal staff notes, and manages user feedback.
6. `FINANCE_ADMIN`: Inspects Razorpay transactions, subscription tiers, promo coupons, and tax invoices.
7. `AI_ENGINEER`: Tunes prompt architectures, model engines, and sampling temperatures for all system personas.
8. `CANDIDATE`: Default candidate clearance; strictly forbidden (`403 Forbidden`) from accessing administrative endpoints.

---

### DATABASE PERSISTENCE & MIGRATIONS

Alembic Migration: `backend/alembic/versions/d7e8f9a0b1c2_add_admin_dashboard_and_rbac_tables.py`

#### Added Columns:
- `users.role` (`VARCHAR(50)`, default `'CANDIDATE'`)
- `users.is_admin` (`BOOLEAN`, default `False`)

#### Added Tables:
1. `admin_roles`: System and custom role definitions with granular JSONB permissions.
2. `admin_audit_logs`: Immutable security ledger tracking `actor_email`, `action`, `resource_type`, `resource_id`, `changes` (JSONB), `ip_address`, and `timestamp`.
3. `system_settings`: Key-value configuration store with JSONB values, category tags, and validation rules.
4. `companies`: Target hiring companies with difficulty bars, roles, logos, and rubrics.
5. `ai_agent_configs`: Prompt architectures, model engines, temperatures, and token caps (API credentials remain securely hidden).

---

### BACKEND ENDPOINTS OVERVIEW

Mounted at `/api/v1/admin/*`:
- `GET /api/v1/admin/dashboard`: Live PostgreSQL KPI aggregates and daily telemetry series.
- `GET /api/v1/admin/users`: Search, filter by role/status, paginated user list.
- `GET /api/v1/admin/users/{user_id}`: Deep dossier (interviews, payments, subscriptions, tickets, coding stats).
- `PATCH /api/v1/admin/users/{user_id}/status`: Account suspension and restoration.
- `PATCH /api/v1/admin/users/{user_id}/role`: Security clearance role updates.
- `GET /api/v1/admin/interviews`: Auditable interview sessions with search and status filters.
- `GET /api/v1/admin/interviews/{interview_id}`: Full transcript, evaluation, and question inspection.
- `GET, POST, PUT, DELETE /api/v1/admin/questions`: Practice Question Bank CRUD.
- `GET /api/v1/admin/coding/problems`: 1,000 Coding Arena problem bank inspection with test cases and canonical solutions.
- `GET, POST, PUT, DELETE /api/v1/admin/companies`: Target company profile CRUD.
- `GET, POST, PUT, DELETE /api/v1/admin/resources`: Curated learning resource CRUD.
- `GET, PUT /api/v1/admin/ai-agents`: AI Agent prompt and model configuration tuning.
- `GET /api/v1/admin/resume-ats`: Candidate resume ATS evaluation records.
- `GET, POST /api/v1/admin/subscriptions/plans`: Subscription plan management.
- `GET /api/v1/admin/payments`: Live Razorpay billing transactions with secret masking.
- `GET, POST, PATCH /api/v1/admin/coupons`: Discount coupons and promotional campaign management.
- `GET /api/v1/admin/invoices`: Tax invoices and billing receipts.
- `GET, POST, PATCH /api/v1/admin/support/tickets`: Support ticket triage with internal notes and status transitions.
- `GET, PATCH /api/v1/admin/feedback`: Candidate feedback and bug report acknowledgement.
- `POST /api/v1/admin/notifications/broadcast`: Simultaneous WebSocket push and PostgreSQL announcement persistence.
- `GET, POST /api/v1/admin/achievements`: Gamification badge management.
- `GET /api/v1/admin/audit-logs`: Immutable administrative audit trail.
- `GET, PUT /api/v1/admin/settings`: Global system settings management.
- `GET, PUT, POST /api/v1/admin/rbac/*`: Role permission matrix updates and direct user role assignment.
- `GET /api/v1/admin/rag/status`: High-dimensional vector index health.
- `GET /api/v1/admin/learning/stats`: Learning intelligence proficiency and practice metrics.
- `GET /api/v1/admin/contests`: Live competitive coding tournaments.

---

### FRONTEND SUITE IMPLEMENTATION

Located in `user_side_frontend/src/admin/`:
- **Architecture**:
  - `types/index.ts`: TypeScript contracts for all models, KPIs, and requests.
  - `services/adminApi.ts`: Fetch-based API client supporting Bearer JWT auth.
  - `hooks/useAdminAuth.ts`: RBAC permission verification hook (`hasPermission(perm)`).
  - `components/`: `AdminIcons.tsx`, `AdminSidebar.tsx`, `AdminHeader.tsx`, `AdminBreadcrumbs.tsx`, `AdminProtectedRoute.tsx`, `AdminRoleGuard.tsx`, `AdminErrorBoundary.tsx`, `AdminStatCard.tsx`, `AdminTable.tsx`, `AdminConfirmModal.tsx`.
  - `layouts/AdminLayout.tsx` & `AdminLayout.css`: Premium dark glassmorphism layout matching candidate platform design tokens.
  - `pages/`: 25 comprehensive management pages mounted under `/admin/*` in `App.tsx`.

---

### VERIFICATION & REGRESSION TESTING SUMMARY

1. **Phase 13 Admin & RBAC Test Suite (`verify_admin_dashboard.py`)**:
   - **56 / 56 Tests Passed (100% Success)**
   - Verified 401 unauthenticated rejection, 403 candidate rejection, Super Admin access, self-lockout guard.
   - Verified live database aggregations (73 users, 46 interviews, 5,738 practice questions, 1,000 coding problems, 12 subscription plans, 12 payments, 7 tickets, 10 feedback items, 29,584 audit log records).
   - Verified real-time WebSocket connection, heartbeat ping-pong, and live administrative event delivery.

2. **Phase 16 Real-Time WebSocket Suite (`verify_phase16_realtime.py`)**:
   - **22 / 22 Tests Passed (100% Success)**

3. **Phase 11 Learning Intelligence Suite (`verify_phase11_learning.py`)**:
   - **13 / 13 Tests Passed (100% Success)**

4. **Phase 10 RAG Semantic Retrieval Suite (`verify_phase10_rag.py`)**:
   - **18 / 18 Tests Passed (100% Success)**

5. **Frontend Compilation & Linting**:
   - `pnpm run build`: **Exit Code 0** (0 TypeScript errors, production bundle compiled cleanly).
   - `pnpm run lint`: **Exit Code 0** (0 linting errors).

---

### SEEDED DEFAULT CREDENTIALS

- **Super Administrator**:
  - **Email**: `admin@interviewplatform.ai`
  - **Password**: `AdminPass123!`
  - **Role**: `SUPER_ADMIN`
  - **Capabilities**: Unrestricted platform clearance across all 36 capabilities.
