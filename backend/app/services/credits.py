"""付费点数：匿名 device_id → account，点数流水(只增不改)，余额 = SUM(delta)。
见 docs/superpowers/specs/2026-07-22-ziwei-paid-credits-design.md"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.billing_contention import bound_lock_wait
from app.models.entities import Account, AccountDevice, CreditLedger

# 服务端权威定价（前端只报 pack key，金额/点数一律以此为准）。amount_cents = CNY 分。
PACKS: dict[str, dict] = {
    "p10": {"credits": 10, "amount_cents": 990, "label": "10 点"},
    "p40": {"credits": 40, "amount_cents": 2990, "label": "40 点"},
    "p100": {"credits": 100, "amount_cents": 6800, "label": "100 点"},
}


def resolve_account(db: Session, device_id: str, *, create: bool = True) -> Optional[Account]:
    """device_id → account。新设备（create=True 时）自动建 account + 绑定 + 赠送免费点数。
    空 device_id 返回 None。"""
    bound_lock_wait(db)
    device_id = (device_id or "").strip()
    if not device_id:
        return None
    link = db.scalar(select(AccountDevice).where(AccountDevice.device_id == device_id))
    if link:
        return db.get(Account, link.account_id)
    if not create:
        return None
    acct = Account()
    db.add(acct)
    db.flush()  # 拿 acct.id
    db.add(AccountDevice(account_id=acct.id, device_id=device_id))
    free = get_settings().ziwei_free_credits
    if free > 0:
        db.add(CreditLedger(account_id=acct.id, delta=free, reason="welcome"))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return resolve_account(db, device_id, create=False)
    db.refresh(acct)
    return acct


def balance(db: Session, account_id: int) -> int:
    return int(
        db.scalar(
            select(func.coalesce(func.sum(CreditLedger.delta), 0)).where(CreditLedger.account_id == account_id)
        )
        or 0
    )


def grant(db: Session, account_id: int, delta: int, reason: str, order_id: Optional[int] = None) -> None:
    db.add(CreditLedger(account_id=account_id, delta=delta, reason=reason, order_id=order_id))
    db.commit()


def lock_account(db: Session, account_id: int) -> None:
    # An UPDATE obtains a write lock on SQLite and a row lock on PostgreSQL.
    # All balance-decreasing operations must acquire this lock before reading SUM.
    bound_lock_wait(db)
    db.execute(update(Account).where(Account.id == account_id).values(id=Account.id))


def consume_one(db: Session, account_id: int, reason: str = "ziwei_oracle", *, commit: bool = True) -> bool:
    lock_account(db, account_id)
    if balance(db, account_id) < 1:
        db.rollback()
        return False
    db.add(CreditLedger(account_id=account_id, delta=-1, reason=reason))
    db.flush()
    if commit:
        db.commit()
    return True


def request_identity(account_id: int, operation: str, key: str, payload: str):
    import hashlib
    if not key or not 8 <= len(key) <= 128:
        raise ValueError("invalid_idempotency_key")
    digest = lambda value: hashlib.sha256(value.encode()).hexdigest()
    return digest(f"{account_id}:{operation}:{key}"), digest(payload)
