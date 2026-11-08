"""Fresh paid-product identities only. No legacy enrollment or data migration."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PaidVerifiedEmail(Base):
    __tablename__ = "paid_verified_emails"
    email: Mapped[str] = mapped_column(String(255), primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), unique=True, nullable=False)


class PaidSession(Base):
    __tablename__ = "paid_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class PaidChallenge(Base):
    __tablename__ = "paid_challenges"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    email: Mapped[str] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)


class PaidRateLimit(Base):
    __tablename__ = "paid_rate_limits"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=1)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class PaidZiweiOwner(Base):
    __tablename__ = "paid_ziwei_owners"
    profile_id: Mapped[int] = mapped_column(ForeignKey("ziwei_profiles.id", ondelete="CASCADE"), primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)


class PaidQianOwner(Base):
    __tablename__ = "paid_qian_owners"
    reading_id: Mapped[int] = mapped_column(ForeignKey("qian_readings.id", ondelete="CASCADE"), primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
