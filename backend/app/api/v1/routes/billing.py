"""付费点数 billing 端点：余额 + 套餐 + Stripe 下单 + webhook。
见 docs/superpowers/specs/2026-07-22-ziwei-paid-credits-design.md"""
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.services import credits as credits_svc
from app.services import stripe_billing

logger = logging.getLogger(__name__)
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
        "paid_enabled": stripe_billing.is_configured(),
        "packs": _packs(),
    }


class CheckoutRequest(BaseModel):
    pack: str


@router.post("/checkout")
def checkout(payload: CheckoutRequest, db: Session = Depends(get_db), device: str = Depends(get_device_id)):
    """创建 Stripe 收银台会话，返回跳转 URL。金额/点数一律服务端定。"""
    if not stripe_billing.is_configured():
        raise HTTPException(503, "支付暂未开通。")
    if not device:
        raise HTTPException(400, "缺少设备标识，请刷新页面重试。")
    if payload.pack not in credits_svc.PACKS:
        raise HTTPException(400, "未知套餐。")
    acct = credits_svc.resolve_account(db, device)
    try:
        url = stripe_billing.create_checkout_session(db, acct.id, payload.pack)
    except Exception:  # noqa: BLE001
        logger.exception("stripe checkout create failed (account=%s pack=%s)", acct.id, payload.pack)
        raise HTTPException(502, "创建支付会话失败，请稍后重试。")
    return {"url": url}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Stripe 付款回调：验签 → 幂等发点。必须读原始 body 验签。"""
    s = get_settings()
    if not s.stripe_secret_key or not s.stripe_webhook_secret:
        raise HTTPException(503, "billing not configured")
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe_billing.verify_event(payload, sig)
    except Exception:  # noqa: BLE001 — invalid signature / malformed
        logger.warning("stripe webhook signature verification failed")
        raise HTTPException(400, "invalid signature")
    status = stripe_billing.process_event(db, event)
    return {"status": status}
