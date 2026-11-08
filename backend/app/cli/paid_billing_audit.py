"""Read-only local ledger audit, not provider reconciliation or refund processing.

Uses explicit PAID_DATABASE_URL and DATABASE_URL. Never calls a payment provider,
repairs a ledger, changes an order or reads an implicit .env file.
"""
import argparse
from datetime import datetime, timedelta
import json
import os
import sys

from sqlalchemy import and_, func, inspect, or_, select, text

from app.cli.paid_retention import EXPECTED_TABLES, _engine
from app.models.entities import Account, CreditLedger, PaymentOrder


def inspect_ledger(conn, *, now=None):
    """Aggregate diagnostic only. No customer identifiers, balances or secrets."""
    now = now or datetime.utcnow()
    orders, ledger = PaymentOrder.__table__, CreditLedger.__table__
    purchases = (select(ledger.c.order_id, func.count().label("entries"),
                        func.min(ledger.c.account_id).label("account_min"),
                        func.max(ledger.c.account_id).label("account_max"),
                        func.sum(ledger.c.delta).label("credits"))
                 .where(ledger.c.reason == "purchase").group_by(ledger.c.order_id).subquery())
    joined = orders.outerjoin(purchases, purchases.c.order_id == orders.c.id)
    def order_count(predicate):
        return conn.scalar(select(func.count()).select_from(joined).where(predicate))
    wrong_grant = or_(func.coalesce(purchases.c.entries, 0) != 1,
                     purchases.c.account_min != orders.c.account_id,
                     purchases.c.account_max != orders.c.account_id,
                     purchases.c.credits != orders.c.credits)
    anomalies = {
        "paid_order_grant_mismatch": order_count(and_(orders.c.status == "paid", wrong_grant)),
        "unpaid_order_has_purchase": order_count(and_(orders.c.status != "paid", func.coalesce(purchases.c.entries, 0) > 0)),
        "unknown_order_state": order_count(or_(orders.c.status.is_(None), orders.c.status.not_in(["pending", "paid", "failed"]))),
        "orphan_purchase_entries": conn.scalar(select(func.count()).select_from(ledger.outerjoin(orders, ledger.c.order_id == orders.c.id)).where(ledger.c.reason == "purchase", orders.c.id.is_(None))),
        # Payment-linked refunds have no verified provider lifecycle in this product.
        # Reading-failure refunds without an order link are intentionally not included.
        "unsupported_payment_refund_entries": conn.scalar(select(func.count()).select_from(ledger).where(ledger.c.reason == "refund", ledger.c.order_id.is_not(None))),
    }
    balances = select(ledger.c.account_id, func.sum(ledger.c.delta).label("balance")).group_by(ledger.c.account_id).subquery()
    anomalies["negative_account_balances"] = conn.scalar(select(func.count()).select_from(balances).where(balances.c.balance < 0))
    anomalies["orphan_ledger_accounts"] = conn.scalar(select(func.count()).select_from(ledger.outerjoin(Account.__table__, ledger.c.account_id == Account.id)).where(Account.id.is_(None)))
    pending = {
        "older_than_safe_checkout_retry": order_count(and_(orders.c.status == "pending", orders.c.created_at <= now - timedelta(hours=23))),
        "without_saved_provider_session": order_count(and_(orders.c.status == "pending", orders.c.stripe_session_id.like("pending:%"))),
    }
    return {"read_only": True, "local_ledger_consistent": not any(anomalies.values()),
            "provider_reconciled": False, "payment_refunds_supported": False,
            "anomalies": anomalies, "pending_review": pending}


def run_audit(environment):
    engine = None
    try:
        engine = _engine(environment, False)
        with engine.connect() as conn, conn.begin():
            if engine.dialect.name == "postgresql":
                conn.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
                conn.execute(text("SET LOCAL statement_timeout = '10s'"))
                conn.execute(text("SET LOCAL lock_timeout = '5s'"))
            else:
                conn.exec_driver_sql("BEGIN")
            schema = inspect(conn)
            if set(schema.get_table_names()) != EXPECTED_TABLES or schema.get_view_names():
                raise ValueError("unexpected schema")
            return inspect_ledger(conn)
    except Exception:
        raise RuntimeError("Billing audit unavailable. Verify dedicated database configuration and schema.") from None
    finally:
        if engine is not None:
            engine.dispose()


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    try:
        report = run_audit(os.environ)
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True))
    # Old pending intents require investigation even when ledger invariants hold.
    return 0 if report["local_ledger_consistent"] and not report["pending_review"]["older_than_safe_checkout_retry"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
