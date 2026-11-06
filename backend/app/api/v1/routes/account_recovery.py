"""Local/test recovery preparation; routes are disabled by default."""
import secrets
from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.db.billing_contention import retryable_contention
from app.models.entities import (AccountChallenge, AccountDevice, AccountSession,
                                 VerifiedAccountEmail, ZiweiProfile, ZiweiProfileOwner)
from app.services import account_recovery as auth, credits

router = APIRouter(prefix="/account", tags=["account"], dependencies=[Depends(auth.validate_client)])


class Start(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    purpose: Literal["bind", "recover"]

    @field_validator("email")
    @classmethod
    def normalize(cls, value):
        value = value.strip().lower()
        if value.count("@") != 1 or any(c.isspace() for c in value) or not all(value.split("@")):
            raise ValueError("Invalid email")
        return value


class Verify(BaseModel):
    challenge_id: str = Field(min_length=1, max_length=64)
    code: str = Field(min_length=1, max_length=128)


def client_ip(request):
    # Do not trust caller-supplied forwarding headers.
    return request.client.host if request.client else "unknown"


@router.post("/challenges", dependencies=[Depends(auth.require_enabled)])
@retryable_contention
def start(payload: Start, request: Request, db: Session = Depends(get_db),
          sender=Depends(auth.get_sender)):
    auth.rate_limit(db, "start-ip", client_ip(request), 20)
    auth.rate_limit(db, "start-email", payload.email, 5)
    device = request.headers.get("x-device-id", "").strip()
    account_id = None
    if payload.purpose == "bind":
        principal = auth.identity(request, device, db)
        if isinstance(principal, auth.Principal) or not principal:
            raise HTTPException(409, "Use recovery for an existing verified account")
        account = credits.resolve_account(db, principal)
        account_id = account.id
    else:
        binding = db.scalar(select(VerifiedAccountEmail).where(VerifiedAccountEmail.email == payload.email))
        account_id = binding.account_id if binding else None
    challenge_id, code = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    challenge = AccountChallenge(id=challenge_id, code_hash=auth.digest(code), email=payload.email,
        purpose=payload.purpose, account_id=account_id, device_hash=auth.digest(device) if payload.purpose == "bind" else "",
        expires_at=datetime.utcnow() + timedelta(minutes=15))
    db.add(challenge)
    db.commit()
    try:
        # Same delivery behavior for unknown emails; no account-existence disclosure.
        sender(payload.email, code)
    except Exception:
        db.execute(update(AccountChallenge).where(AccountChallenge.id == challenge_id).values(consumed=True))
        db.commit()
        raise HTTPException(503, "Email delivery unavailable") from None
    return {"challenge_id": challenge_id, "expires_in": 900}


@router.post("/verify", dependencies=[Depends(auth.require_enabled)])
@retryable_contention
def verify(payload: Verify, request: Request, response: Response, db: Session = Depends(get_db)):
    auth.rate_limit(db, "verify-ip", client_ip(request), 40)
    auth.rate_limit(db, "verify-challenge", payload.challenge_id, 5)
    challenge = db.get(AccountChallenge, payload.challenge_id)
    if not challenge or not secrets.compare_digest(challenge.code_hash, auth.digest(payload.code)):
        raise HTTPException(400, "Invalid or expired code")
    # Conditional consume serializes replay and rolls back with ownership on conflict.
    changed = db.execute(update(AccountChallenge).where(AccountChallenge.id == challenge.id,
        AccountChallenge.consumed.is_(False), AccountChallenge.expires_at > datetime.utcnow()).values(consumed=True))
    if changed.rowcount != 1 or challenge.account_id is None:
        db.rollback()
        raise HTTPException(400, "Invalid or expired code")
    try:
        credits.lock_account(db, challenge.account_id)
        if challenge.purpose == "bind":
            device = request.headers.get("x-device-id", "").strip()
            if not device or not secrets.compare_digest(challenge.device_hash, auth.digest(device)):
                raise HTTPException(400, "Original device credential required")
            link = db.scalar(select(AccountDevice).where(AccountDevice.device_id == device))
            if not link or link.account_id != challenge.account_id:
                raise HTTPException(409, "Device ownership changed")
            existing = db.get(VerifiedAccountEmail, challenge.account_id)
            other = db.scalar(select(VerifiedAccountEmail).where(VerifiedAccountEmail.email == challenge.email))
            if existing or other:
                raise HTTPException(409, "Account already bound; recover it without merging accounts")
            db.add(VerifiedAccountEmail(account_id=challenge.account_id, email=challenge.email))
            # Migrate only the presented bearer credential's profiles. No bulk adoption
            # of NULL owners, other mapped devices, contact emails or Checkout emails.
            profiles = db.scalars(select(ZiweiProfile).where(ZiweiProfile.device_id == device)).all()
            for profile in profiles:
                owner = db.get(ZiweiProfileOwner, profile.id)
                if owner and owner.account_id != challenge.account_id:
                    raise HTTPException(409, "Profile ownership conflict")
                if not owner:
                    db.add(ZiweiProfileOwner(profile_id=profile.id, account_id=challenge.account_id))
        else:
            binding = db.get(VerifiedAccountEmail, challenge.account_id)
            if not binding or binding.email != challenge.email:
                raise HTTPException(409, "Account ownership changed")
            # Recovery revokes every prior session, including a lost/stolen browser.
            auth.revoke_sessions(db, challenge.account_id)
        token = auth.issue_session(db, challenge.account_id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Account ownership conflict") from None
    except Exception:
        db.rollback()
        raise
    response.set_cookie(auth.cookie_name(), token, max_age=30 * 86400, httponly=True,
                        secure=get_settings().account_session_secure, samesite="strict", path="/")
    response.headers["Cache-Control"] = "no-store"
    return {"verified": True}


@router.get("/session")
def session(request: Request, response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    # Session inspection ignores anonymous device ownership. A verified old device
    # without a cookie is logged out, and may explicitly restore another legacy ID.
    principal = auth.identity(request, "", db)
    return {"authenticated": isinstance(principal, auth.Principal)}


def clear_cookie(response: Response):
    response.delete_cookie(auth.COOKIE, path="/", secure=True, httponly=True, samesite="strict")
    response.delete_cookie(auth.LOCAL_COOKIE, path="/", secure=False, httponly=True, samesite="strict")
    # Retire the pre-hardening host-only cookie; never use it as identity proof.
    response.delete_cookie("oracle_session", path="/api/v1", secure=True, httponly=True, samesite="strict")
    response.delete_cookie("oracle_session", path="/", secure=True, httponly=True, samesite="strict")
    response.headers["Cache-Control"] = "no-store"


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    # Idempotent even for expired/revoked/unknown cookies. Router CSRF checks still
    # apply, but a valid session is not required to clear this browser's state.
    token = request.cookies.get(auth.cookie_name())
    if token:
        db.execute(delete(AccountSession).where(AccountSession.token_hash == auth.digest(token)))
        db.commit()
    clear_cookie(response)
    return {"authenticated": False}


@router.post("/logout-all")
def logout_all(response: Response, db: Session = Depends(get_db), principal=Depends(auth.identity)):
    if not isinstance(principal, auth.Principal):
        raise HTTPException(401, "Session required")
    credits.lock_account(db, principal.account_id)
    auth.revoke_sessions(db, principal.account_id)
    db.commit()
    clear_cookie(response)
    return {"authenticated": False}
