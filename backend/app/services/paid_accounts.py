"""Mailbox-verified fresh accounts, without any anonymous-account adoption."""
import hashlib
import secrets
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, Request
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import Account
from app.models.paid_accounts import PaidChallenge, PaidRateLimit, PaidSession
from app.services.paid_identity import PaidPrincipal

COOKIE = "__Host-paid_session"
LOCAL_COOKIE = "paid_session_local"


def cookie_name():
    settings = get_settings()
    if settings.paid_session_secure:
        return COOKIE
    if settings.app_env not in {"development", "test"}:
        raise HTTPException(503, "Insecure cookies are only supported for local development/tests")
    return LOCAL_COOKIE


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def validate_client(request: Request):
    origin = request.headers.get("origin")
    if request.headers.get("x-paid-client") != "1" or (origin and origin not in get_settings().cors_origins_list):
        raise HTTPException(403, "Invalid account request")


def require_enabled():
    cookie_name()
    if not get_settings().paid_accounts_enabled:
        raise HTTPException(503, "Account sign-in unavailable")


def send_code(email: str, code: str):
    # Explicit provider configuration is required; the default stays fail-closed.
    # Tests still replace get_sender with an in-memory fake.
    from app.services.paid_email import send_verification_email
    send_verification_email(get_settings(), email, code)


def get_sender():
    return send_code


def rate_limit(db: Session, scope: str, value: str, maximum: int):
    now = datetime.utcnow()
    bucket = now.replace(minute=0, second=0, microsecond=0)
    key = digest(f"{scope}:{bucket.isoformat()}:{value}")
    dialect = db.get_bind().dialect.name
    if dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert
    elif dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    else:
        raise HTTPException(503, "Unsupported account database")
    stmt = insert(PaidRateLimit).values(key=key, count=1, expires_at=bucket + timedelta(hours=2))
    count = db.scalar(stmt.on_conflict_do_update(index_elements=["key"],
                      set_={"count": PaidRateLimit.count + 1}).returning(PaidRateLimit.count))
    # Failed attempts also count; commit independently from verification.
    db.commit()
    if count > maximum:
        raise HTTPException(429, "Too many attempts", headers={"Retry-After": "3600"})


def optional_principal(request: Request, db: Session):
    validate_client(request)
    token = request.cookies.get(cookie_name())
    if not token:
        return None
    session = db.get(PaidSession, digest(token))
    if not session or session.expires_at <= datetime.utcnow() or not db.get(Account, session.account_id):
        raise HTTPException(401, "Session expired; verify your email again")
    return PaidPrincipal(session.account_id)


def require_principal(request: Request, db: Session = Depends(get_db)):
    # Deliberately ignores X-Device-Id, account IDs and all legacy cookie names.
    principal = optional_principal(request, db)
    if principal is None:
        raise HTTPException(401, "Verify your email to continue")
    return principal


def require_private_access(request: Request, db: Session = Depends(get_db)):
    require_enabled()
    return require_principal(request, db)


def issue_session(db: Session, account_id: int):
    token = secrets.token_urlsafe(32)
    db.add(PaidSession(token_hash=digest(token), account_id=account_id,
                       expires_at=datetime.utcnow() + timedelta(days=30)))
    return token


def revoke_sessions(db: Session, account_id: int):
    db.execute(delete(PaidSession).where(PaidSession.account_id == account_id))


def purge_expired_auth_records(db: Session, *, now=None):
    """Maintenance primitive, no external scheduler or deletion endpoint installed.

    Removes only expired authentication material, never account/history/credit data.
    The caller commits; expired challenges retain a day for operational diagnosis.
    """
    now = now or datetime.utcnow()
    db.execute(delete(PaidSession).where(PaidSession.expires_at <= now))
    db.execute(delete(PaidRateLimit).where(PaidRateLimit.expires_at <= now))
    db.execute(delete(PaidChallenge).where(PaidChallenge.expires_at <= now - timedelta(days=1)))
