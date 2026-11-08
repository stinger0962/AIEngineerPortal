"""Explicit maintenance of expired auth material, never account/product records.

Run from backend: python -m app.cli.paid_retention [--apply --max-delete N]
Only explicit environment URLs are read; no .env or application startup imports.
"""
import argparse
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import sqlite3
import sys
from urllib.parse import quote

from sqlalchemy import create_engine, delete, func, inspect, select, text
from sqlalchemy.engine import make_url

from app.models.paid_accounts import PaidChallenge, PaidRateLimit, PaidSession
from app.db.paid_isolation import DatabaseIsolationError, validate_database_isolation

EXPECTED_TABLES = frozenset({
    "users", "ai_feedback", "ziwei_profiles", "ziwei_conversations", "ziwei_messages",
    "qian_readings", "accounts", "account_devices", "credit_ledger", "payment_orders",
    "billing_requests", "paid_challenges", "paid_sessions", "paid_rate_limits",
    "paid_verified_emails", "paid_ziwei_owners", "paid_qian_owners",
})


class RetentionError(Exception):
    """Only fixed, credential-free messages reach the CLI."""


def _engine(environment, apply):
    paid_raw = environment.get("PAID_DATABASE_URL", "")
    portal_raw = environment.get("DATABASE_URL", "")
    if not paid_raw or not portal_raw:
        raise RetentionError("Both dedicated PAID_DATABASE_URL and portal DATABASE_URL are required.")
    try:
        validate_database_isolation(paid_raw, portal_raw)
    except DatabaseIsolationError as error:
        raise RetentionError(str(error)) from None
    paid, portal = make_url(paid_raw), make_url(portal_raw)
    if paid == portal:
        raise RetentionError("Paid and portal databases must differ.")
    if paid.get_backend_name() == "sqlite":
        if paid.query or not paid.database or paid.database == ":memory:":
            raise RetentionError("An existing plain SQLite file is required.")
        path = Path(paid.database).resolve(strict=True)
        if not path.is_file():
            raise RetentionError("An existing plain SQLite file is required.")
        if portal.get_backend_name() == "sqlite" and portal.database:
            other = Path(portal.database).resolve()
            if path == other or (other.exists() and path.samefile(other)):
                raise RetentionError("Paid and portal databases must differ.")
        uri = "file:" + quote(str(path), safe="/") + ("?mode=rw" if apply else "?mode=ro")
        return create_engine("sqlite://", creator=lambda: sqlite3.connect(uri, uri=True, timeout=5))
    if paid.get_backend_name() != "postgresql" or not paid.database:
        raise RetentionError("Only plain PostgreSQL URLs or existing SQLite files are supported.")
    # Ignore login identity/driver spelling: different users can access the same DB.
    if portal.get_backend_name() == "postgresql" and (paid.host, paid.port or 5432, paid.database) == (portal.host, portal.port or 5432, portal.database):
        raise RetentionError("Paid and portal databases must differ.")
    return create_engine(paid, connect_args={"connect_timeout": 5}, echo=False, hide_parameters=True)


def run_retention(environment, *, apply=False, max_delete=None):
    if apply and (type(max_delete) is not int or max_delete < 1):
        raise RetentionError("Apply requires a positive --max-delete budget.")
    engine = None
    try:
        engine = _engine(environment, apply)
        now = datetime.utcnow()
        predicates = (
            (PaidSession.__table__, PaidSession.expires_at <= now),
            (PaidRateLimit.__table__, PaidRateLimit.expires_at <= now),
            (PaidChallenge.__table__, PaidChallenge.expires_at <= now - timedelta(days=1)),
        )
        with engine.connect() as conn:
            with conn.begin():
                if engine.dialect.name == "postgresql":
                    conn.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
                    if not apply:
                        conn.execute(text("SET TRANSACTION READ ONLY"))
                    conn.execute(text("SET LOCAL statement_timeout = '10s'"))
                    conn.execute(text("SET LOCAL lock_timeout = '5s'"))
                elif apply:
                    conn.exec_driver_sql("BEGIN IMMEDIATE")
                inspector = inspect(conn)
                if set(inspector.get_table_names()) != EXPECTED_TABLES or inspector.get_view_names():
                    raise RetentionError("Database is not the dedicated paid schema; no changes made.")
                # Maintenance must not invoke user-defined delete side effects.
                triggers = (conn.exec_driver_sql("SELECT name FROM sqlite_master WHERE type = 'trigger'").first()
                            if engine.dialect.name == "sqlite" else
                            conn.execute(text("SELECT 1 FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid JOIN pg_namespace n ON n.oid = c.relnamespace WHERE NOT t.tgisinternal AND n.nspname = current_schema() LIMIT 1")).first())
                if triggers:
                    raise RetentionError("Unexpected database triggers; no changes made.")
                auth_names = {table.name for table, _ in predicates}
                for table_name in EXPECTED_TABLES:
                    if any(fk.get("referred_table") in auth_names for fk in inspector.get_foreign_keys(table_name)):
                        raise RetentionError("Unexpected references to authentication tables; no changes made.")
                if engine.dialect.name == "postgresql":
                    inbound = conn.execute(text("SELECT 1 FROM pg_constraint f JOIN pg_class target ON target.oid = f.confrelid JOIN pg_namespace n ON n.oid = target.relnamespace WHERE f.contype = 'f' AND n.nspname = current_schema() AND target.relname IN ('paid_sessions', 'paid_rate_limits', 'paid_challenges') LIMIT 1")).first()
                    if inbound:
                        raise RetentionError("Unexpected references to authentication tables; no changes made.")
                    rules = conn.execute(text("SELECT 1 FROM pg_rules WHERE schemaname = current_schema() AND tablename IN ('paid_sessions', 'paid_rate_limits', 'paid_challenges') LIMIT 1")).first()
                    if rules:
                        raise RetentionError("Unexpected database rules; no changes made.")
                counts = {table.name: conn.scalar(select(func.count()).select_from(table).where(predicate)) for table, predicate in predicates}
                if apply:
                    if sum(counts.values()) > max_delete:
                        raise RetentionError("Deletion budget exceeded; no changes made.")
                    deleted = {table.name: conn.execute(delete(table).where(predicate)).rowcount for table, predicate in predicates}
                    if deleted != counts:
                        raise RetentionError("Concurrent changes detected; transaction rolled back.")
                return {"mode": "apply" if apply else "dry-run", "cutoff_utc": now.isoformat() + "Z", "challenge_grace_hours": 24, "counts": counts}
    except RetentionError:
        raise
    except Exception:
        raise RetentionError("Retention did not complete successfully. Verify database state before retrying.") from None
    finally:
        if engine is not None:
            engine.dispose()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--max-delete", type=int)
    args = parser.parse_args(argv)
    try:
        result = run_retention(os.environ, apply=args.apply, max_delete=args.max_delete)
    except RetentionError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
