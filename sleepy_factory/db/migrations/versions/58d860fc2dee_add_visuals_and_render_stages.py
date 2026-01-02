"""add visuals and render stages

Revision ID: 58d860fc2dee
Revises: 958d0d1b987c
Create Date: 2026-01-02 14:30:17.587694

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "58d860fc2dee"
down_revision: str | Sequence[str] | None = "958d0d1b987c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1) Add columns with a server_default so existing rows get filled
    op.add_column(
        "jobs",
        sa.Column(
            "visuals_status",
            sa.Enum("NEW", "READY", "RUNNING", "DONE", "ERROR", name="stagestatus"),
            nullable=False,
            server_default="NEW",
        ),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "render_status",
            sa.Enum("NEW", "READY", "RUNNING", "DONE", "ERROR", name="stagestatus"),
            nullable=False,
            server_default="NEW",
        ),
    )

    # 2) Create indexes (these lines might already exist in your file)
    op.create_index("ix_jobs_visuals_status", "jobs", ["visuals_status"], unique=False)
    op.create_index("ix_jobs_render_status", "jobs", ["render_status"], unique=False)

    # 3) Remove the server_default so future behavior comes from your ORM default,
    # not a DB default (optional but recommended)
    op.alter_column("jobs", "visuals_status", server_default=None)
    op.alter_column("jobs", "render_status", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_jobs_render_status", table_name="jobs")
    op.drop_index("ix_jobs_visuals_status", table_name="jobs")
    op.drop_column("jobs", "render_status")
    op.drop_column("jobs", "visuals_status")
