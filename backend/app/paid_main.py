"""Isolated, fresh-start paid-product API (no deployment is enabled here).

Run with PAID_DATABASE_URL pointing at a new dedicated database:
    uvicorn app.paid_main:app --app-dir backend --port 8001
Existing portal data is neither copied nor upgraded. Checkout remains test-only.
"""
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.api.v1.routes import billing, qian, ziwei
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
))


def validate_configuration(settings):
    if not settings.paid_database_url:
        raise RuntimeError("PAID_DATABASE_URL must name a dedicated fresh database")
    if make_url(settings.paid_database_url) == make_url(settings.database_url):
        raise RuntimeError("Paid product must not use the portal DATABASE_URL")
    if settings.stripe_secret_key and not settings.stripe_secret_key.startswith("sk_test_"):
        raise RuntimeError("Paid product foundation accepts Stripe test keys only")
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
    for router in (product_ziwei, qian.router, billing.router):
        app.include_router(router, prefix="/api/v1")

    @app.get("/health")
    def health():
        return {"status": "ok", "product": "paid-features", "payments": "test-only"}

    return app


app = create_app()
