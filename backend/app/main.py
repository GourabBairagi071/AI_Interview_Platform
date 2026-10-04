from fastapi import FastAPI
from sqlalchemy import text

from app.core.database import AsyncSessionLocal
from app.modules.auth.router import router as auth_router
from app.modules.resume.router import router as resume_router
from app.modules.interview.router import router as interview_router
from app.modules.analytics.router import router as analytics_router
from app.modules.practice.router import router as practice_router
from app.modules.achievements.router import router as achievements_router
from app.modules.notifications.router import router as notifications_router
from app.modules.profile.router import router as profile_router
from app.modules.anticheating.router import router as anticheating_router
from app.modules.coding.router import router as coding_router
from app.modules.coding.contest_router import router as contest_router
from app.modules.rag.router import router as rag_router
from app.modules.learning.router import router as learning_router
from app.modules.payments.router import router as payments_router
from app.modules.support.router import router as support_router
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import logging

logger = logging.getLogger("app.security")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(self), microphone=(self), geolocation=()"
        return response


app = FastAPI(
    title="AI Interview Platform API",
    version="1.0.0",
)

app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled server exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Incident logged."},
    )



app.include_router(
    auth_router,
    prefix="/api/v1",
)

app.include_router(
    resume_router,
    prefix="/api/v1",
)

app.include_router(
    interview_router,
    prefix="/api/v1",
)

app.include_router(
    analytics_router,
    prefix="/api/v1",
)

app.include_router(
    practice_router,
    prefix="/api/v1",
)

app.include_router(
    achievements_router,
    prefix="/api/v1",
)

app.include_router(
    notifications_router,
    prefix="/api/v1",
)

app.include_router(
    profile_router,
    prefix="/api/v1",
)

app.include_router(
    anticheating_router,
    prefix="/api/v1",
)

app.include_router(
    coding_router,
    prefix="/api/v1",
)

app.include_router(
    contest_router,
    prefix="/api/v1",
)

app.include_router(
    rag_router,
    prefix="/api/v1",
)

app.include_router(
    learning_router,
    prefix="/api/v1",
)

app.include_router(
    payments_router,
    prefix="/api/v1",
)

app.include_router(
    support_router,
    prefix="/api/v1",
)

from app.modules.admin.router import router as admin_router

app.include_router(
    admin_router,
    prefix="/api/v1",
)

from app.core.websocket.router import router as websocket_router

app.include_router(
    websocket_router,
    prefix="/api/v1",
)
app.include_router(
    websocket_router,
)

# Standard Razorpay integration routes
from app.modules.payments.router import create_order as create_order_endpoint
from app.modules.payments.router import verify_payment as verify_payment_endpoint

app.add_api_route("/api/create-order", create_order_endpoint, methods=["POST"], tags=["Razorpay Checkout"])
app.add_api_route("/api/verify-payment", verify_payment_endpoint, methods=["POST"], tags=["Razorpay Checkout"])


@app.on_event("startup")
async def seed_plans_on_startup():
    """Seed default subscription plans, support content, and admin data if they don't exist."""
    from app.modules.payments.service import seed_default_plans
    from app.modules.support.service import seed_support_content
    from app.modules.admin.service import AdminService
    from app.core.config import settings
    from app.core.websocket.publisher import RedisEventPublisher, set_publisher

    if settings.redis_url:
        redis_pub = RedisEventPublisher(settings.redis_url)
        if await redis_pub.initialize():
            set_publisher(redis_pub)

    async with AsyncSessionLocal() as session:
        await seed_default_plans(session)
        await seed_support_content(session)
        await AdminService.seed_default_admin_data(session)


@app.get("/health")
async def health_check():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT 1"))

    return {
        "status": "healthy",
        "database": result.scalar() == 1,
    }