"""add qc run report filename

Revision ID: 0e7c8a1f0c0d
Revises: d38aff65e4e3
Create Date: 2026-05-30 23:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0e7c8a1f0c0d"
down_revision: str | None = "d38aff65e4e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "qc_runs",
        sa.Column("report_filename", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("qc_runs", "report_filename")
