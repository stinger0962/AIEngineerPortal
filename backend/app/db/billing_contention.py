"""Bound database lock waits for billing transactions, including post-commit work."""
from functools import wraps
from inspect import iscoroutinefunction, signature

from fastapi import HTTPException
from sqlalchemy import event, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.config import get_settings


def _apply(connection, milliseconds: int):
    if connection.dialect.name == "postgresql":
        connection.execute(text("SELECT set_config('lock_timeout', :timeout, true)"),
                           {"timeout": f"{milliseconds}ms"})
    elif connection.dialect.name == "sqlite":
        # Validated integer, not user SQL. SQLite has a connection-level busy handler.
        connection.exec_driver_sql(f"PRAGMA busy_timeout = {milliseconds}")


@event.listens_for(Session, "after_begin")
def _transaction_started(session, transaction, connection):
    milliseconds = session.info.get("billing_lock_timeout_ms")
    if milliseconds is not None:
        _apply(connection, milliseconds)


def bound_lock_wait(db: Session):
    milliseconds = get_settings().billing_lock_timeout_ms
    db.info["billing_lock_timeout_ms"] = milliseconds
    # A profile lookup may already have started the transaction.
    if db.in_transaction():
        _apply(db.connection(), milliseconds)


def is_lock_contention(exc: DBAPIError) -> bool:
    original = exc.orig
    code = getattr(original, "sqlstate", None) or getattr(original, "pgcode", None)
    if code in ("55P03", "40P01"):  # lock timeout / deadlock victim
        return True
    sqlite_code = getattr(original, "sqlite_errorcode", None)
    return isinstance(sqlite_code, int) and (sqlite_code & 255) in (5, 6)  # BUSY / LOCKED


def _translate(db, exc):
    if not is_lock_contention(exc):
        raise exc
    db.rollback()
    raise HTTPException(503, {"code": "billing_busy", "retryable": True,
                              "retry_after_seconds": 2}, headers={"Retry-After": "2"}) from exc


def retryable_contention(function):
    """HTTP boundary: do not mislabel arbitrary database/provider errors as contention."""
    parameters = signature(function)
    if iscoroutinefunction(function):
        @wraps(function)
        async def async_wrapper(*args, **kwargs):
            db = parameters.bind(*args, **kwargs).arguments["db"]
            try:
                bound_lock_wait(db)
                return await function(*args, **kwargs)
            except DBAPIError as exc:
                _translate(db, exc)
        return async_wrapper

    @wraps(function)
    def wrapper(*args, **kwargs):
        # Direct route tests also pass the dependency positionally.
        db = parameters.bind(*args, **kwargs).arguments["db"]
        try:
            bound_lock_wait(db)
            return function(*args, **kwargs)
        except DBAPIError as exc:
            _translate(db, exc)
    return wrapper
