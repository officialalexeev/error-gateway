"""SQLAlchemy models for error groups and events."""

from datetime import datetime, timezone
from uuid import uuid4

from app.core.database import Base
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship


class ErrorGroupModel(Base):
    """SQLAlchemy model for error group."""

    __tablename__ = "error_groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    exception_type: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    first_seen: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    is_notified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_notified_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, default=None, index=True
    )

    events: Mapped[list["ErrorEventModel"]] = relationship(
        "ErrorEventModel",
        back_populates="group",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ErrorEventModel(Base):
    """SQLAlchemy model for error event."""

    __tablename__ = "error_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    group_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("error_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    stack_trace: Mapped[str | None] = mapped_column(Text, nullable=True)
    context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    group: Mapped["ErrorGroupModel"] = relationship(
        "ErrorGroupModel",
        back_populates="events",
    )
