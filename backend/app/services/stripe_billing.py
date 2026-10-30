"""Explicitly opt-in Stripe TEST checkout and atomic fulfillment."""
from urllib.parse import urlparse
from datetime import datetime, timedelta
from ipaddress import ip_address

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.billing_contention import bound_lock_wait
from app.models.entities import BillingRequest, CreditLedger, PaymentOrder
from app.services import credits as credits_svc


def _canonical_hostname(hostname: str | None) -> str:
    # Compare DNS names independent of case, IDNA spelling and the root dot.
    return (hostname or "").rstrip(".").encode("idna").decode("ascii").lower().rstrip(".")


def is_configured() -> bool:
    s = get_settings()
    try:
        if any(c.isspace() or c == "\\" for c in s.stripe_test_base_url):
            return False
        base = urlparse(s.stripe_test_base_url)
        port = base.port  # Reject malformed/out-of-range ports before contacting Stripe.
        host = _canonical_hostname(base.hostname)
        production_host = _canonical_hostname(urlparse(s.public_base_url).hostname)
    except (ValueError, UnicodeError):
        return False
    try:
        loopback = host == "localhost" or ip_address(host).is_loopback
    except ValueError:
        loopback = host == "localhost"
    return bool(s.stripe_test_enabled and s.stripe_secret_key.startswith("sk_test_")
                and host and (base.scheme == "https" or (base.scheme == "http" and loopback))
                and port != 0
                and not base.username and not base.password and not base.query and not base.fragment and not base.params
                and host != production_host
                and not host.endswith("leipan.cc"))


def create_checkout_session(db: Session, account_id: int, pack_key: str, idempotency_key: str) -> dict:
    import stripe
    if not is_configured():
        raise RuntimeError("stripe_test_not_configured")
    pack = credits_svc.PACKS.get(pack_key)
    if not pack:
        raise ValueError("unknown_pack")
    key, fingerprint = credits_svc.request_identity(account_id, "checkout", idempotency_key, pack_key)
    credits_svc.lock_account(db, account_id)
    req = db.get(BillingRequest, key)
    if req:
        if req.fingerprint != fingerprint:
            db.rollback()
            raise ValueError("idempotency_conflict")
        order = db.get(PaymentOrder, req.response_json["order_id"])
        if req.response_json.get("url"):
            result = dict(req.response_json)
            db.rollback()
            return result
    else:
        order = PaymentOrder(account_id=account_id, pack=pack_key, credits=pack["credits"],
                             amount_cents=pack["amount_cents"], currency="cny",
                             stripe_session_id=f"pending:{key}", status="pending")
        db.add(order)
        db.flush()
        req = BillingRequest(key=key, account_id=account_id, fingerprint=fingerprint,
                             response_json={"order_id": order.id})
        db.add(req)
    if datetime.utcnow() - order.created_at >= timedelta(hours=23):
        db.rollback()
        raise ValueError("checkout_reconciliation_required")
    # Persist intent before Stripe. Retrying a timeout uses the same Stripe key.
    db.commit()
    s = get_settings()
    base = s.stripe_test_base_url.rstrip("/")
    session = stripe.checkout.Session.create(
        api_key=s.stripe_secret_key, idempotency_key=f"ziwei-test-{key}",
        mode="payment", payment_method_types=["alipay", "wechat_pay", "card"],
        payment_method_options={"wechat_pay": {"client": "web"}},
        line_items=[{"price_data": {"currency": "cny", "unit_amount": order.amount_cents,
                     "product_data": {"name": f"紫微解盘点数 · {pack['label']}"}}, "quantity": 1}],
        success_url=f"{base}/ziwei?paid=1&order_id={order.id}",
        cancel_url=f"{base}/ziwei?canceled=1&order_id={order.id}",
        metadata={"order_id": str(order.id), "account_id": str(account_id)},
    )
    if session.livemode is not False:
        raise RuntimeError("live_session_rejected")
    order.stripe_session_id = session.id
    result = {"url": session.url, "order_id": order.id, "mode": "test"}
    req.response_json = result
    db.commit()
    return result


def verify_event(payload: bytes, sig_header: str):
    import stripe
    return stripe.Webhook.construct_event(payload, sig_header, get_settings().stripe_webhook_secret)


def process_event(db: Session, event) -> str:
    bound_lock_wait(db)
    obj = event["data"]["object"]
    if event.get("livemode") is not False or obj.get("livemode") is not False:
        return "live_or_unknown_mode_rejected"
    etype = event["type"]
    if etype not in ("checkout.session.completed", "checkout.session.async_payment_succeeded",
                     "checkout.session.async_payment_failed"):
        return "ignored"
    order = db.scalar(select(PaymentOrder).where(PaymentOrder.stripe_session_id == obj.get("id")))
    if not order:
        # Delivery can precede saving the Checkout response; ask Stripe to retry.
        return "order_not_found"
    # Failure events must identify the same purchase just as success events do.
    if (obj.get("amount_total") != order.amount_cents or obj.get("currency") != order.currency
            or obj.get("mode") != "payment"
            or (obj.get("metadata") or {}).get("order_id") != str(order.id)
            or (obj.get("metadata") or {}).get("account_id") != str(order.account_id)):
        return "payment_mismatch"
    if etype == "checkout.session.async_payment_failed":
        changed = db.execute(update(PaymentOrder).where(PaymentOrder.id == order.id, PaymentOrder.status == "pending")
                             .values(status="failed")).rowcount
        db.commit()
        if changed:
            return "failed"
        db.refresh(order)  # Another delivery may have paid it after our SELECT.
        return "already_paid" if order.status == "paid" else "already_failed"
    if obj.get("payment_status") != "paid":
        return "not_paid_yet"
    changed = db.execute(update(PaymentOrder).where(PaymentOrder.id == order.id, PaymentOrder.status != "paid")
                         .values(status="paid")).rowcount
    if not changed:
        db.rollback()
        return "already_paid"
    # Status transition and ledger insert share ONE transaction. No intermediate commit.
    db.add(CreditLedger(account_id=order.account_id, delta=order.credits, reason="purchase", order_id=order.id))
    db.commit()
    return "credited"
