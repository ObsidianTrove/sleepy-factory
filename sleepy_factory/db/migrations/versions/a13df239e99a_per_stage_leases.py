"""per stage leases

Revision ID: a13df239e99a
Revises: 58d860fc2dee
Create Date: 2026-01-02 14:50:28.313556

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a13df239e99a"
down_revision: str | Sequence[str] | None = "58d860fc2dee"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1) Add new per-stage lease columns
    op.add_column("jobs", sa.Column("audio_lease_owner", sa.String(length=200), nullable=True))
    op.add_column(
        "jobs", sa.Column("audio_lease_expires_at", sa.DateTime(timezone=True), nullable=True)
    )

    op.add_column("jobs", sa.Column("visuals_lease_owner", sa.String(length=200), nullable=True))
    op.add_column(
        "jobs", sa.Column("visuals_lease_expires_at", sa.DateTime(timezone=True), nullable=True)
    )

    op.add_column("jobs", sa.Column("render_lease_owner", sa.String(length=200), nullable=True))
    op.add_column(
        "jobs", sa.Column("render_lease_expires_at", sa.DateTime(timezone=True), nullable=True)
    )

    # 2) Backfill from the legacy shared lease columns (if they exist)
    # Assumption: at most one stage is RUNNING at a time per job.
    op.execute(
        """
        UPDATE jobs
        SET audio_lease_owner = lease_owner,
            audio_lease_expires_at = lease_expires_at
        WHERE lease_owner IS NOT NULL
          AND audio_status = 'RUNNING';
        """
    )
    op.execute(
        """
        UPDATE jobs
        SET visuals_lease_owner = lease_owner,
            visuals_lease_expires_at = lease_expires_at
        WHERE lease_owner IS NOT NULL
          AND visuals_status = 'RUNNING';
        """
    )
    op.execute(
        """
        UPDATE jobs
        SET render_lease_owner = lease_owner,
            render_lease_expires_at = lease_expires_at
        WHERE lease_owner IS NOT NULL
          AND render_status = 'RUNNING';
        """
    )

    # 3) Drop legacy columns (only if your table currently has them)
    # If Alembic did not autogenerate drops, add them here anyway.
    with op.batch_alter_table("jobs") as batch:
        batch.drop_column("lease_owner")
        batch.drop_column("lease_expires_at")


def downgrade() -> None:
    # Recreate legacy columns
    op.add_column("jobs", sa.Column("lease_owner", sa.String(length=200), nullable=True))
    op.add_column("jobs", sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True))

    # Best-effort backfill legacy columns from whichever stage is RUNNING
    op.execute(
        """
        UPDATE jobs
        SET lease_owner = audio_lease_owner,
            lease_expires_at = audio_lease_expires_at
        WHERE audio_status = 'RUNNING'
          AND audio_lease_owner IS NOT NULL;
        """
    )
    op.execute(
        """
        UPDATE jobs
        SET lease_owner = visuals_lease_owner,
            lease_expires_at = visuals_lease_expires_at
        WHERE visuals_status = 'RUNNING'
          AND visuals_lease_owner IS NOT NULL;
        """
    )
    op.execute(
        """
        UPDATE jobs
        SET lease_owner = render_lease_owner,
            lease_expires_at = render_lease_expires_at
        WHERE render_status = 'RUNNING'
          AND render_lease_owner IS NOT NULL;
        """
    )

    # Drop per-stage columns
    with op.batch_alter_table("jobs") as batch:
        batch.drop_column("render_lease_expires_at")
        batch.drop_column("render_lease_owner")
        batch.drop_column("visuals_lease_expires_at")
        batch.drop_column("visuals_lease_owner")
        batch.drop_column("audio_lease_expires_at")
        batch.drop_column("audio_lease_owner")
