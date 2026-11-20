from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Analysis(Base):
    """One analysed X-ray. Only derived results and a reference to the
    re-encoded image are stored — never the original filename."""

    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)

    image_path: Mapped[str] = mapped_column(String(200))
    image_width: Mapped[int] = mapped_column(Integer)
    image_height: Mapped[int] = mapped_column(Integer)

    prediction: Mapped[str] = mapped_column(String(16))          # PNEUMONIA | NORMAL
    pneumonia_probability: Mapped[float] = mapped_column(Float)
    uncertainty: Mapped[float] = mapped_column(Float)            # 0 (certain) .. 1 (maximally uncertain)
    decision: Mapped[str] = mapped_column(String(8))             # AUTO | REFER
    decision_reason: Mapped[str] = mapped_column(String(300))
    referral_threshold: Mapped[float] = mapped_column(Float)

    model_version: Mapped[str] = mapped_column(String(32))
    processing_ms: Mapped[float] = mapped_column(Float)
    gradcam_path: Mapped[str | None] = mapped_column(String(200), nullable=True)
