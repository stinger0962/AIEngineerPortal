"""Isolated, fresh-start paid-product API (no deployment is enabled here).

Run with PAID_DATABASE_URL pointing at a new dedicated database:
    uvicorn app.paid_main:app --app-dir backend --port 8001
Existing portal data is neither copied nor upgraded. Checkout remains test-only.
"""
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.api.v1.routes import billing, paid_accounts, qian, ziwei
from app.services import paid_accounts as auth
from app.models.paid_accounts import (PaidChallenge, PaidSession, PaidRateLimit,
                                      PaidVerifiedEmail, PaidZiweiOwner, PaidQianOwner)
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.logging import RequestLoggingMiddleware
from app.models.entities import (
    Account, AccountDevice, AIFeedback, BillingRequest, CreditLedger,
    PaymentOrder, QianReading, User, ZiweiConversation, ZiweiMessage, ZiweiProfile,
)

# User is an empty compatibility table for oracle usage attribution, not the
# portal's seeded personal user. No curriculum, projects or personal seed data.
PAID_TABLES = tuple(model.__table__ for model in (
    User, AIFeedback, ZiweiProfile, ZiweiConversation, ZiweiMessage,
    QianReading, Account, AccountDevice, CreditLedger, PaymentOrder, BillingRequest,
    PaidChallenge, PaidSession, PaidRateLimit, PaidVerifiedEmail, PaidZiweiOwner, PaidQianOwner,
))


def validate_configuration(settings):
    if not settings.paid_database_url:
        raise RuntimeError("PAID_DATABASE_URL must name a dedicated fresh database")
    if make_url(settings.paid_database_url) == make_url(settings.database_url):
        raise RuntimeError("Paid product must not use the portal DATABASE_URL")
    if settings.stripe_secret_key and not settings.stripe_secret_key.startswith("sk_test_"):
        raise RuntimeError("Paid product foundation accepts Stripe test keys only")
    if not settings.paid_session_secure and settings.app_env not in {"development", "test"}:
        raise RuntimeError("Insecure paid session cookies are only supported in local development/tests")
    if settings.ziwei_claim_code or settings.ziwei_auto_adopt:
        raise RuntimeError("Legacy claim and migration are not supported in the fresh product")


def create_app():
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app):
        validate_configuration(settings)
        # Validation runs before opening or creating the database.
        engine = create_engine(settings.paid_database_url, future=True)
        sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
        try:
            tables = set(inspect(engine).get_table_names())
            if tables - {table.name for table in PAID_TABLES}:
                raise RuntimeError("Paid database contains unrelated tables; use a dedicated database")
            Base.metadata.create_all(engine, tables=list(PAID_TABLES))
            app.state.paid_engine = engine

            def paid_db():
                with sessions() as db:
                    yield db

            app.dependency_overrides[get_db] = paid_db
            yield
        finally:
            app.dependency_overrides.pop(get_db, None)
            engine.dispose()

    app = FastAPI(title="Paid Features API", lifespan=lifespan)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins_list,
                       allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    # Copy, do not mutate the shared router: the portal retains its existing API.
    product_ziwei = APIRouter()
    product_ziwei.routes.extend(route for route in ziwei.router.routes if route.path != "/ziwei/claim")
    for router in (product_ziwei, qian.router):
        app.include_router(router, prefix="/api/v1", dependencies=[Depends(auth.require_private_access)])
    # Stripe's test webhook authenticates by signature, not a browser session.
    private_billing = APIRouter()
    webhook = APIRouter()
    for route in billing.router.routes:
        (webhook if route.path == "/billing/webhook" else private_billing).routes.append(route)
    app.include_router(private_billing, prefix="/api/v1", dependencies=[Depends(auth.require_private_access)])
    app.include_router(webhook, prefix="/api/v1")
    app.include_router(paid_accounts.router, prefix="/api/v1")
    for dependency in (ziwei.get_device_id, qian.get_device_id, billing.get_device_id):
        app.dependency_overrides[dependency] = auth.require_principal

    @app.middleware("http")
    async def private_responses(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/v1/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/health")
    def health():
        return {"status": "ok", "product": "paid-features", "payments": "test-only"}

    return app


app = create_app()
