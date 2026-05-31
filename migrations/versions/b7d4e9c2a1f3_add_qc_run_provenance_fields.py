"""add qc run provenance fields

Adds sample count and uploaded-report integrity columns (size + sha256).
Run timing already exists via started_at / finished_at from the bootstrap
migration.

Revision ID: b7d4e9c2a1f3
Revises: 0e7c8a1f0c0d
Create Date: 2026-05-31 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7d4e9c2a1f3"
down_revision: str | None = "0e7c8a1f0c0d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "qc_runs",
        sa.Column("sample_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "qc_runs",
        sa.Column("report_size_bytes", sa.Integer(), nullable=True),
    )
    op.add_column(
        "qc_runs",
        sa.Column("report_sha256", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("qc_runs", "report_sha256")
    op.drop_column("qc_runs", "report_size_bytes")
    op.drop_column("qc_runs", "sample_count")
