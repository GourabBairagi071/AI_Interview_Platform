# Phase 16 — Real-Time Features & WebSocket System Report

## 1. Objective
Introduce an enterprise-grade, secure, authenticated real-time communication layer across the AI Interview & Career Preparation Platform. The architecture enables bi-directional communication, event-driven updates from backend domain modules directly to connected candidate and admin browsers, eliminates manual polling overhead, maintains seamless fallbacks to PostgreSQL-backed REST APIs, and ensures zero data loss or security vulnerabilities.

---

## 2. Architecture Overview
The real-time layer operates as an event-driven distribution pipeline:

```
[Domain Service (Notifications, Support, Interviews, Contests, Learning)]
                            ↓
                    publish_event(...)
                            ↓
       [EventPublisher (Redis Pub/Sub OR In-Memory Bus)]
                            ↓
         [ConnectionManager (User ID → Set[WebSocket])]
                            ↓
        [Authenticated Client Connections (WS /api/v1/ws)]
                            ↓
   [Frontend RealtimeService (Singleton with Subscriptions)]
                            ↓
     [React UI State (Dashboard, Support Tickets, Leaderboards)]
```

### Key Principles:
- **Database Persistence as Source of Truth**: WebSocket is strictly an asynchronous delivery and presentation acceleration layer. PostgreSQL persists all state (notifications, tickets, messages, submissions, scores).
- **Zero Impersonation**: Client connection authentication is strictly derived from the cryptographically validated JWT token (`sub` claim validated against the DB user record).
- **Multi-Tab / Multi-Device Support**: Users can have multiple browser tabs or devices simultaneously connected. Events target all active sockets belonging to that user ID.
- **Graceful Fallback**: If WebSockets are blocked by proxies or temporarily disconnect, the frontend functions with REST APIs and manual/reconnect refreshes.

---

## 3. Files Created

### Backend:
1. `backend/app/core/websocket/__init__.py`: Package initialization exporting the connection manager, event publisher, event types, and router.
2. `backend/app/core/websocket/events.py`: Standardized event envelope definition (`WebSocketEventType` enum, `format_event` serializer with `event`, `timestamp`, `data`, `id`, `version`).
3. `backend/app/core/websocket/auth.py`: Secure WebSocket authentication helper (`authenticate_websocket`) extracting tokens from query parameters or protocols, verifying signatures, expiration, user existence, and account active state.
4. `backend/app/core/websocket/manager.py`: `ConnectionManager` class managing user-to-socket mappings (`dict[str, set[WebSocket]]`), thread-safe asynchronous locking, stale connection eviction, personal delivery, role-based broadcasting, and system broadcasts.
5. `backend/app/core/websocket/publisher.py`: Event distribution abstraction with `EventPublisher` base class, `InMemoryEventPublisher` for single-process environments, and `RedisEventPublisher` for multi-instance distributed deployments.
6. `backend/app/core/websocket/router.py`: WebSocket endpoint definition (`/api/v1/ws` and `/ws`), handling 64KB message limits, client heartbeat keep-alives (`{"type": "ping"}` -> `{"event": "pong"}`), graceful disconnection, and internal event publishing bridge.
7. `backend/scratch/verify_phase16_realtime.py`: 22-test automated verification suite covering security, event routing, RBAC, heartbeat, reconnection, and fallbacks.

### Frontend:
1. `user_side_frontend/src/services/websocket.ts`: Central singleton `RealtimeService` providing JWT-authenticated connections, bounded exponential backoff reconnection (1.5s–15s, 10 retries), keep-alive heartbeat interval (25s), and type-safe event subscriptions.
2. `user_side_frontend/src/hooks/useWebSocket.ts`: Reusable React hook exposing connection status (`connected`, `connecting`, `error`) and `useWebSocketEvent` for declarative event listener lifecycles.
3. `user_side_frontend/src/components/RealtimeStatusBadge.tsx`: Glassmorphism-styled live status indicator displaying connection health ("Live", "Connecting...", "Offline (REST)") with animated pulsing indicator dot.
4. `user_side_frontend/src/components/RealtimeStatusBadge.css`: CSS styling for connection badge, pulse animations, and real-time toast notifications.

---

## 4. Files Modified

### Backend:
1. `backend/app/core/config.py`: Added `redis_url: str = ""` configuration parameter.
2. `backend/app/main.py`: Mounted `websocket_router` at `/api/v1` and `/`, integrated startup event publisher initialization.
3. `backend/app/modules/notifications/service.py`: Integrated `publish_event` for `notification.created` and `notification.read`.
4. `backend/app/modules/support/service.py`: Integrated real-time events for `support.ticket.created`, `support.ticket.message` (strictly preventing candidate exposure to internal notes), and `support.ticket.status`.
5. `backend/app/modules/interview/service.py`: Integrated `interview.started` and `interview.completed` event triggers with final evaluation scores.
6. `backend/app/modules/learning/router.py`: Integrated `learning.plan.updated` event dispatch on AI roadmap generation.
7. `backend/app/modules/coding/contest_service.py`: Added `contest.leaderboard.updated` (broadcast) and `contest.participant.updated` events on solution submission.

### Frontend:
1. `user_side_frontend/src/pages/Dashboard.tsx`: Integrated `RealtimeStatusBadge`, real-time notification prepending with unread count updates, interactive toast popup with auto-dismiss, and learning plan re-sync.
2. `user_side_frontend/src/pages/SupportTicketDetails.tsx`: Integrated live message appending without page refresh, real-time ticket status updates, and `RealtimeStatusBadge`.
3. `user_side_frontend/src/pages/ContestLeaderboard.tsx`: Added `RealtimeStatusBadge` and automatic background leaderboard reload upon receiving `contest.leaderboard.updated` and `contest.status` events.

---

## 5. WebSocket Endpoint
- **Primary Route**: `GET /api/v1/ws` (WebSocket upgrade)
- **Fallback Route**: `GET /ws` (WebSocket upgrade)
- **Protocol**: `ws://` (HTTP) or `wss://` (HTTPS)
- **Query Parameter**: `?token=<JWT_TOKEN>`

---

## 6. Authentication Mechanism
1. The client supplies the JWT token via URL query parameter `?token=<token>`.
2. The server extracts the token and validates:
   - Cryptographic signature using the application `SECRET_KEY` and `ALGORITHM` (HS256).
   - Expiration timestamp (`exp`).
   - Token subject (`sub`) corresponding to the user ID.
3. The server queries PostgreSQL to verify the user exists and their account is active (`is_active = True`).
4. If invalid or expired, the server terminates the handshake with WebSocket close code `1008` (Policy Violation / HTTP 403 Forbidden).
5. **No Client-Supplied User Identity**: Any `user_id` query parameter is strictly ignored. The authenticated user identity is derived exclusively from the token claims.

---

## 7. Event Types & Envelope Contract

Standardized Event Envelope:
```json
{
  "event": "notification.created",
  "timestamp": "2026-10-04T12:00:00.000Z",
  "data": { ... },
  "id": "uuid-v4-string",
  "version": "1.0"
}
```

Supported Events:
- `notification.created`: Fired when a system or administrative notification is saved.
- `notification.read`: Fired when notifications are marked read.
- `support.ticket.created`: Dispatched when a ticket is opened.
- `support.ticket.message`: Dispatched when a new reply is submitted.
- `support.ticket.status`: Dispatched when ticket status transitions (`RESOLVED`, `CLOSED`, `REOPENED`).
- `interview.started`: Dispatched when an interview session begins.
- `interview.completed`: Dispatched when interview grading finishes.
- `learning.plan.updated`: Dispatched when a new roadmap/learning plan is generated.
- `contest.status`: Broadcast when a contest state changes (`UPCOMING`, `ACTIVE`, `ENDED`).
- `contest.leaderboard.updated`: Broadcast when participants submit solutions and standings update.
- `contest.participant.updated`: User-scoped update for submission verdicts.
- `system.event`: Platform-wide maintenance announcements.

---

## 8. Redis Architecture
- **Abstraction**: `EventPublisher` ABC with `publish(event_type, data, user_id=None, role=None)`.
- **Implementations**:
  - `InMemoryEventPublisher`: Delivers events directly through the in-process `ConnectionManager`. Used in local development and single-instance deployments.
  - `RedisEventPublisher`: Uses Redis Pub/Sub channel `interview_platform_events`. A background listener task receives events published by any FastAPI worker process and broadcasts them to locally connected WebSocket clients.
- **Current Environment**: Single-process environment (`redis_url` not configured, Redis package optional). Cleanly operating on `InMemoryEventPublisher` fallback with multi-worker Redis upgrade readiness built-in.

---

## 9. Frontend Integration
- **Singleton Lifecycle**: `realtimeService` maintains a single authenticated socket per browser session.
- **Connection Management**:
  - Automatically initializes when an authenticated user loads the application.
  - Terminates gracefully when the user logs out.
- **Component Subscriptions**:
  - `Dashboard.tsx`: Listens to `notification.created` (updates unread count, prepends notification item, shows toast banner) and `learning.plan.updated` (re-syncs roadmap).
  - `SupportTicketDetails.tsx`: Listens to `support.ticket.message` (instantly appends agent replies) and `support.ticket.status` (updates status badge).
  - `ContestLeaderboard.tsx`: Listens to `contest.leaderboard.updated` and `contest.status` (reloads leaderboard standings).
- **Subtle Glassmorphism Status Badge**: Renders connection health with a minimal footprint in the navigation bar and headers.

---

## 10. Reconnection Strategy
- **Exponential Backoff**: Initial delay of 1.5 seconds, multiplying by 1.5 on each subsequent failure up to a ceiling of 15 seconds.
- **Bounded Attempts**: Maximum of 10 consecutive retry attempts before marking the connection as offline to prevent aggressive battery and bandwidth consumption.
- **Network Awareness**: Automatic event listeners on `window.addEventListener('online')` trigger immediate reconnection attempts when network recovery is detected.
- **Post-Reconnection Data Sync**: Sockets do not guarantee message delivery during network downtime; critical domain views automatically perform background REST synchronization upon re-establishing connection.

---

## 11. REST Fallback
- If WebSockets fail to connect, are disabled, or are blocked by network firewalls:
  - All application functionality continues to operate through REST APIs.
  - Dashboard loads notifications via `GET /api/v1/notifications`.
  - Support Tickets load and send messages via standard REST endpoints.
  - Contests retain manual refresh controls and REST endpoints for leaderboard loading.
  - The `RealtimeStatusBadge` displays "Offline (REST)" cleanly without crashing the UI.

---

## 12. Security & RBAC Enforcement
- **Strict User Isolation**: Candidate A cannot receive Candidate B's notifications or ticket messages.
- **Role-Based Broadcasting**: System and administrative events can be scoped using `broadcast_to_role()`.
- **Support Privacy**: Internal notes added to support tickets are strictly filtered on the backend and never dispatched over WebSocket to candidate clients.
- **Input Sanitization & Abuse Protection**: Inbound client messages are capped at 64KB, ping-pong payloads are validated, and arbitrary client event broadcasting is disallowed.
- **No Secret Leakage**: No JWT tokens, passwords, payment secrets, or hidden test cases are transmitted in WebSocket payloads.

---

## 13. Automated Test Suite (22/22 Scenarios Passed)
A verification script was executed against the active FastAPI server: `backend/scratch/verify_phase16_realtime.py`.

| Test # | Test Name | Result |
|--------|-----------|--------|
| 1 | Authenticated WebSocket Connection | PASS |
| 2 | Invalid JWT Rejection (Code 1008 / HTTP 403) | PASS |
| 3 | Expired JWT Rejection | PASS |
| 4 | User Identity Derived from JWT (Spoofing Ignored) | PASS |
| 5 | Connection and Disconnection Lifecycle | PASS |
| 6 | Multiple Concurrent Connections per User | PASS |
| 7 | Personal Event Delivery | PASS |
| 8 | Cross-User Event Isolation (No Leakage) | PASS |
| 9 | Notification Event Delivery (`notification.created`) | PASS |
| 10 | Support Ticket Event Delivery (`support.ticket.created`) | PASS |
| 11 | Support Message Event Delivery (`support.ticket.message`) | PASS |
| 12 | Support Status Transition Event (`support.ticket.status`) | PASS |
| 13 | Internal Support Notes Privacy (Filtered from Candidates) | PASS |
| 14 | RBAC Role-Based Event Delivery | PASS |
| 15 | Interview Lifecycle Events (`interview.completed`) | PASS |
| 16 | Learning Plan Events (`learning.plan.updated`) | PASS |
| 17 | Contest Broadcast Events (`contest.leaderboard.updated`) | PASS |
| 18 | Malformed Message Handling | PASS |
| 19 | Stale Connection Eviction | PASS |
| 20 | Reconnection Handling | PASS |
| 21 | REST API Fallback Verification | PASS |
| 22 | Redis Fallback / Publisher Verification | PASS |

---

## 14. Build Results
- **Command**: `pnpm run build` in `user_side_frontend/`
- **Output**: `✓ built in 438ms`
- **TypeScript Errors**: 0

---

## 15. Lint Results
- **Command**: `pnpm run lint` in `user_side_frontend/`
- **Output**: 0 errors across 38 files.

---

## 16. Regression Testing
- **Phase 14 Payments & Subscriptions**: `python scratch/verify_payments.py` -> 100% Passed.
- **Phase 15 Support & Communication**: `python scratch/verify_support.py` -> 22/22 Passed.
- **Phase 8D Contests**: `python scratch/verify_contests.py` -> 12/12 Passed.
- **Phase 8 Coding Problems & Database**: `python scratch/verify_database.py` -> 1000/1000 Problems verified, 0 duplicates, valid test cases.

---

## 17. Known Limitations & Environment State
1. **Redis**: Not configured in local development environment. Operating on `InMemoryEventPublisher` fallback.
2. **Single-Process vs Multi-Process**: In-memory event delivery works for single-process instances (current dev environment). For multi-worker Kubernetes/distributed deployment, setting `REDIS_URL` in `.env` activates the already-implemented `RedisEventPublisher`.
3. **Delivery Guarantees**: WebSockets operate on best-effort delivery. Network drops are handled gracefully by frontend automatic re-synchronization with REST endpoints upon reconnection.
