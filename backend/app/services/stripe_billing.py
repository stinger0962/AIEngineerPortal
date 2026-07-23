"""Stripe 跨境收款：创建 Checkout Session（支付宝/微信，服务端权威定价）+ 处理 webhook。
Alipay/WeChat 可能异步结算 → 一律以 webhook 的 paid 状态发点，不靠跳转回来。
见 docs/superpowers/specs/2026-07-22-ziwei-paid-credits-design.md"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import Account, PaymentOrder
from app.services import credits as credits_svc

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    return bool(get_settings().stripe_secret_key)


def create_checkout_session(db: Session, account_id: int, pack_key: str) -> str:
    """建 Stripe Checkout Session，落一条 pending 订单，返回收银台 URL。金额/点数一律服务端定。"""
    import stripe

    s = get_settings()
    if not s.stripe_secret_key:
        raise RuntimeError("stripe_not_configured")
    pack = credits_svc.PACKS.get(pack_key)
    if not pack:
        raise ValueError("unknown_pack")

    stripe.api_key = s.stripe_secret_key
    base = s.public_base_url.rstrip("/")
    session = stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=["alipay", "wechat_pay", "card"],
        payment_method_options={"wechat_pay": {"client": "web"}},
        line_items=[{
            "price_data": {
                "currency": "cny",
                "unit_amount": pack["amount_cents"],
                "product_data": {"name": f"紫微解盘点数 · {pack['label']}"},
            },
            "quantity": 1,
        }],
        success_url=f"{base}/ziwei?paid=1&sid={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{base}/ziwei?canceled=1",
        metadata={"account_id": str(account_id), "pack": pack_key, "credits": str(pack["credits"])},
    )
    db.add(PaymentOrder(
        account_id=account_id, pack=pack_key, credits=pack["credits"],
        amount_cents=pack["amount_cents"], currency="cny",
        stripe_session_id=session.id, status="pending",
    ))
    db.commit()
    return session.url


def verify_event(payload: bytes, sig_header: str):
    """验签并返回 Stripe 事件；失败抛异常。"""
    import stripe

    s = get_settings()
    return stripe.Webhook.construct_event(payload, sig_header, s.stripe_webhook_secret)


def process_event(db: Session, event) -> str:
    """处理已验签的事件。付款成功→幂等发点；异步失败→标记订单 failed。返回状态串。"""
    etype = event["type"]
    obj = event["data"]["object"]
    sid = obj.get("id")

    if etype in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        if obj.get("payment_status") != "paid":
            return "not_paid_yet"  # 异步付款：等 async_payment_succeeded 再发点
        order = db.scalar(select(PaymentOrder).where(PaymentOrder.stripe_session_id == sid))
        if not order:
            return "order_not_found"
        if order.status == "paid":
            return "already_paid"  # 幂等：webhook 重投不重复发点
        order.status = "paid"
        credits_svc.grant(db, order.account_id, order.credits, "purchase", order_id=order.id)
        email = (obj.get("customer_details") or {}).get("email")
        if email:
            acct = db.get(Account, order.account_id)
            if acct and not acct.email and not db.scalar(select(Account).where(Account.email == email)):
                acct.email = email
                db.commit()
        logger.info("stripe: credited order=%s account=%s +%s", order.id, order.account_id, order.credits)
        return "credited"

    if etype == "checkout.session.async_payment_failed":
        order = db.scalar(select(PaymentOrder).where(PaymentOrder.stripe_session_id == sid))
        if order and order.status == "pending":
            order.status = "failed"
            db.commit()
        return "failed"

    return "ignored"
