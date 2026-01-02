import enum
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import (
    DateTime,
    Enum,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

UTC = UTC


class Base(DeclarativeBase):
    pass


class StageStatus(str, enum.Enum):
    NEW = "NEW"
    READY = "READY"
    RUNNING = "RUNNING"
    DONE = "DONE"
    ERROR = "ERROR"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # for MVP we’ll do one stage: "audio"
    audio_status: Mapped[StageStatus] = mapped_column(
        Enum(StageStatus), default=StageStatus.NEW, index=True
    )
    visuals_status: Mapped[StageStatus] = mapped_column(
        Enum(StageStatus), default=StageStatus.NEW, index=True
    )
    render_status: Mapped[StageStatus] = mapped_column(
        Enum(StageStatus), default=StageStatus.NEW, index=True
    )

    attempts: Mapped[int] = mapped_column(Integer, default=0)

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

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def lease_is_expired(self, now: datetime) -> bool:
        if self.lease_expires_at is None:
            return True
        return self.lease_expires_at <= now

    @staticmethod
    def new_lease_expiry(now: datetime, minutes: int = 10) -> datetime:
        return now + timedelta(minutes=minutes)
