"""Single fresh signup/sign-in flow; no device binding or legacy recovery API."""
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.billing_contention import retryable_contention
from app.db.session import get_db
from app.models.entities import Account, CreditLedger
from app.models.paid_accounts import PaidChallenge, PaidSession, PaidVerifiedEmail
from app.services import paid_accounts as auth, credits

router = APIRouter(prefix="/account", tags=["account"], dependencies=[Depends(auth.validate_client)])


class Start(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=255)

    @field_validator("email")
    @classmethod
    def normalize(cls, value):
        value = value.strip().lower()
        if (value.count("@") != 1 or any(c.isspace() or ord(c) < 32 for c in value)
                or not all(value.split("@")) or any(c in value for c in "<>()\\\"")):
            raise ValueError("Invalid email")
        return value


class Verify(BaseModel):
    model_config = ConfigDict(extra="forbid")
    challenge_id: str = Field(min_length=1, max_length=64)
    code: str = Field(min_length=1, max_length=128)


def client_ip(request):
    # Do not trust client-provided forwarding headers. Review trusted proxies at launch.
    return request.client.host if request.client else "unknown"


@router.post("/challenges", dependencies=[Depends(auth.require_enabled)])
@retryable_contention
def start(payload: Start, request: Request, db: Session = Depends(get_db), sender=Depends(auth.get_sender)):
    auth.rate_limit(db, "start-ip", client_ip(request), 20)
    auth.rate_limit(db, "start-email", payload.email, 5)
    challenge_id, code = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    db.add(PaidChallenge(id=challenge_id, code_hash=auth.digest(code), email=payload.email,
                        expires_at=datetime.utcnow() + timedelta(minutes=15)))
    db.commit()
    try:
        # Identical behavior for first-time and returning users, without lookup/enumeration.
        sender(payload.email, code)
    except Exception:
        db.execute(update(PaidChallenge).where(PaidChallenge.id == challenge_id).values(consumed=True))
        db.commit()
        raise HTTPException(503, "Email delivery unavailable") from None
    return {"challenge_id": challenge_id, "expires_in": 900}


@router.post("/verify", dependencies=[Depends(auth.require_enabled)])
@retryable_contention
def verify(payload: Verify, request: Request, response: Response, db: Session = Depends(get_db)):
    auth.rate_limit(db, "verify-ip", client_ip(request), 40)
    auth.rate_limit(db, "verify-challenge", payload.challenge_id, 5)
    challenge = db.get(PaidChallenge, payload.challenge_id)
    if not challenge or not secrets.compare_digest(challenge.code_hash, auth.digest(payload.code)):
        raise HTTPException(400, "Invalid or expired code")
    changed = db.execute(update(PaidChallenge).where(PaidChallenge.id == challenge.id,
        PaidChallenge.consumed.is_(False), PaidChallenge.expires_at > datetime.utcnow()).values(consumed=True))
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(400, "Invalid or expired code")
    try:
        binding = db.get(PaidVerifiedEmail, challenge.email)
        if binding is None:
            # A first successful mailbox proof creates an entirely new account.
            # Never match historical Account.email or attach an AccountDevice.
            account = Account()
            db.add(account)
            db.flush()
            binding = PaidVerifiedEmail(email=challenge.email, account_id=account.id)
            db.add(binding)
            db.flush()  # Unique email constraint serializes concurrent new signups.
            free = get_settings().ziwei_free_credits
            if free > 0:
                db.add(CreditLedger(account_id=account.id, delta=free, reason="welcome"))
        credits.lock_account(db, binding.account_id)
        auth.revoke_sessions(db, binding.account_id)
        token = auth.issue_session(db, binding.account_id)
        db.commit()
    except IntegrityError:
        # Concurrent verification of another challenge may have created this email.
        # Entire account/credit/challenge transaction rolls back; the same code may retry.
        db.rollback()
        raise HTTPException(409, "Account sign-in changed; retry this code") from None
    except BaseException:
        db.rollback()
        raise
    response.set_cookie(auth.cookie_name(), token, max_age=30 * 86400, httponly=True,
                        secure=get_settings().paid_session_secure, samesite="strict", path="/")
    response.headers["Cache-Control"] = "no-store"
    return {"authenticated": True}


@router.get("/session")
def session(request: Request, response: Response, db: Session = Depends(get_db)):
    principal = auth.optional_principal(request, db)
    response.headers["Cache-Control"] = "no-store"
    return {"authenticated": principal is not None, "enabled": get_settings().paid_accounts_enabled,
            "account_id": principal.account_id if principal is not None else None}


def clear_cookie(response):
    response.delete_cookie(auth.COOKIE, path="/", secure=True, httponly=True, samesite="strict")
    response.delete_cookie(auth.LOCAL_COOKIE, path="/", secure=False, httponly=True, samesite="strict")
    response.headers["Cache-Control"] = "no-store"


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    # Clearing an invalid or expired current cookie must remain possible.
    token = request.cookies.get(auth.cookie_name())
    if token:
        db.execute(delete(PaidSession).where(PaidSession.token_hash == auth.digest(token)))
        db.commit()
    clear_cookie(response)
    return {"authenticated": False}


@router.post("/logout-all")
def logout_all(response: Response, db: Session = Depends(get_db), principal=Depends(auth.require_principal)):
    credits.lock_account(db, principal.account_id)
    auth.revoke_sessions(db, principal.account_id)
    db.commit()
    clear_cookie(response)
    return {"authenticated": False}
