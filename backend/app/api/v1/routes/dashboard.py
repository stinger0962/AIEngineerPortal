from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import DashboardSummary, DashboardToday
from app.services.dashboard_service import build_dashboard_summary, build_today_view

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(db: Session = Depends(get_db)) -> DashboardSummary:
    return DashboardSummary(**build_dashboard_summary(db))


@router.get("/today", response_model=DashboardToday)
def get_dashboard_today(db: Session = Depends(get_db)) -> DashboardToday:
    return DashboardToday(**build_today_view(db))
