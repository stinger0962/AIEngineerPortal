"""付费点数 billing 端点。Phase 1: 余额 + 套餐。Phase 2 追加 checkout + webhook。
见 docs/superpowers/specs/2026-07-22-ziwei-paid-credits-design.md"""
from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.services import credits as credits_svc

router = APIRouter(prefix="/billing", tags=["billing"])


def get_device_id(x_device_id: str = Header(default="")) -> str:
    return (x_device_id or "").strip()


def _packs() -> list[dict]:
    return [
        {"key": k, "credits": v["credits"], "amount_cents": v["amount_cents"], "label": v["label"]}
        for k, v in credits_svc.PACKS.items()
    ]


@router.get("/balance")
def get_balance(db: Session = Depends(get_db), device: str = Depends(get_device_id)):
    """本设备账号余额 + 是否开启付费 + 套餐表。首次访问自动建账号并发放免费点数。"""
    s = get_settings()
    bal = 0
    if device:
        acct = credits_svc.resolve_account(db, device)
        bal = credits_svc.balance(db, acct.id)
    return {
        "balance": bal,
        "require_credits": s.ziwei_require_credits,
        "free_credits": s.ziwei_free_credits,
        "packs": _packs(),
    }
