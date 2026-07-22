"""付费点数：匿名 device_id → account，点数流水(只增不改)，余额 = SUM(delta)。
见 docs/superpowers/specs/2026-07-22-ziwei-paid-credits-design.md"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
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
    db.commit()
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


def consume_one(db: Session, account_id: int, reason: str = "ziwei_oracle") -> bool:
    """扣 1 点；余额不足则不扣、返回 False。
    注：并发下的检查-扣减非原子（低流量可接受；最坏偶尔多送一次）。"""
    if balance(db, account_id) < 1:
        return False
    db.add(CreditLedger(account_id=account_id, delta=-1, reason=reason))
    db.commit()
    return True
