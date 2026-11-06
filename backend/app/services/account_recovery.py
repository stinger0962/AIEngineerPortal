"""Verified identity independent of browser storage. No real email transport installed."""
import hashlib
import secrets
from datetime import datetime, timedelta

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import (AccountDevice, AccountSession, AccountRateLimit,
                                 VerifiedAccountEmail, ZiweiProfileOwner)

COOKIE = "__Host-oracle_session"
LOCAL_COOKIE = "oracle_session_local"


def cookie_name() -> str:
    settings = get_settings()
    if settings.account_session_secure:
        return COOKIE
    if settings.app_env not in {"development", "test"}:
        raise HTTPException(503, "Insecure session cookies are only available in local development/tests")
    return LOCAL_COOKIE


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class Principal(str):
    """Internal authenticated identity; never constructed from a caller's account ID."""
    def __new__(cls, account_id: int):
        obj = super().__new__(cls, f"account:{account_id}")
        obj.account_id = account_id
        return obj


def require_enabled():
    cookie_name()  # fail before creating any challenge or ownership binding
    if not get_settings().account_recovery_enabled:
        raise HTTPException(404, "Recovery unavailable")


def send_code(email: str, code: str):
    """Override this dependency with an in-memory fake in local development/tests.

    Fail closed until a separately reviewed email transport is supplied. Never log codes.
    """
    raise HTTPException(503, "Email delivery unavailable")


def get_sender():
    return send_code


def rate_limit(db: Session, scope: str, value: str, maximum: int):
    """Atomic fixed-hour counters shared by workers. No raw email/IP in rate table."""
    now = datetime.utcnow()
    bucket = now.replace(minute=0, second=0, microsecond=0)
    key = digest(f"{scope}:{bucket.isoformat()}:{value}")
    dialect = db.get_bind().dialect.name
    if dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert
    elif dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    else:
        raise HTTPException(503, "Unsupported recovery database")
    stmt = insert(AccountRateLimit).values(key=key, count=1, expires_at=bucket + timedelta(hours=2))
    db.execute(stmt.on_conflict_do_update(index_elements=["key"], set_={"count": AccountRateLimit.count + 1}))
    count = db.get(AccountRateLimit, key).count
    # Commit failed attempts too, separately from the ownership transaction.
    db.commit()
    if count > maximum:
        raise HTTPException(429, "Too many attempts", headers={"Retry-After": "3600"})


def validate_client(request: Request):
    origin = request.headers.get("origin")
    if request.headers.get("x-recovery-client") != "1" or (origin and origin not in get_settings().cors_origins_list):
        raise HTTPException(403, "Invalid session request")


def identity(request: Request, x_device_id: str = Header(default=""), db: Session = Depends(get_db)) -> str:
    device = x_device_id.strip()
    name = cookie_name()
    token = request.cookies.get(name)
    # Ignore all other names: sibling-set parent-domain cookies must neither
    # authenticate nor prevent anonymous access after logout.
    if token:
        # A custom header prevents form CSRF; Origin is checked when browsers send it.
        validate_client(request)
        session = db.get(AccountSession, digest(token))
        if not session or session.expires_at <= datetime.utcnow():
            raise HTTPException(401, "Session expired; verify your email again")
        return Principal(session.account_id)
    if len(device) > 64:
        raise HTTPException(400, "Invalid device credential")
    if device:
        link = db.scalar(select(AccountDevice).where(AccountDevice.device_id == device))
        if link and db.get(VerifiedAccountEmail, link.account_id):
            # Verified accounts cannot be reopened using a revoked browser credential.
            raise HTTPException(401, "Verify your email to access this account")
    return device


def owns_profile(db: Session, profile, principal: str) -> bool:
    owner = db.get(ZiweiProfileOwner, profile.id)
    if isinstance(principal, Principal):
        return owner is not None and owner.account_id == principal.account_id
    return bool(principal and not owner and profile.device_id == principal)


def issue_session(db: Session, account_id: int) -> str:
    token = secrets.token_urlsafe(32)
    db.add(AccountSession(token_hash=digest(token), account_id=account_id,
                          expires_at=datetime.utcnow() + timedelta(days=30)))
    return token


def revoke_sessions(db: Session, account_id: int):
    db.execute(delete(AccountSession).where(AccountSession.account_id == account_id))
