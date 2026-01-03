import enum
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class StageStatus(str, enum.Enum):
    NEW = "NEW"
    READY = "READY"
    RUNNING = "RUNNING"
    DONE = "DONE"
    ERROR = "ERROR"


STATUS_ENUM = Enum(StageStatus, name="stagestatus")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # stage statuses
    script_status: Mapped[StageStatus] = mapped_column(
        STATUS_ENUM, default=StageStatus.NEW, nullable=False, index=True
    )
    audio_status: Mapped[StageStatus] = mapped_column(
        STATUS_ENUM, default=StageStatus.NEW, nullable=False, index=True
    )
    visuals_status: Mapped[StageStatus] = mapped_column(
        STATUS_ENUM, default=StageStatus.NEW, nullable=False, index=True
    )
    render_status: Mapped[StageStatus] = mapped_column(
        STATUS_ENUM, default=StageStatus.NEW, nullable=False, index=True
    )

    attempts: Mapped[int] = mapped_column(Integer, default=0)

    # per-stage leases
    script_lease_owner: Mapped[str | None] = mapped_column(String(200), nullable=True)
    script_lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    audio_lease_owner: Mapped[str | None] = mapped_column(String(200), nullable=True)
    audio_lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    visuals_lease_owner: Mapped[str | None] = mapped_column(String(200), nullable=True)
    visuals_lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    render_lease_owner: Mapped[str | None] = mapped_column(String(200), nullable=True)
    render_lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    @staticmethod
    def new_lease_expiry(now: datetime, minutes: int = 10) -> datetime:
        # now should be timezone-aware (UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        return now + timedelta(minutes=minutes)
