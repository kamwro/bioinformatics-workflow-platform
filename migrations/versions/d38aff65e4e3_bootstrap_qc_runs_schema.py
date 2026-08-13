"""bootstrap qc runs schema

Revision ID: d38aff65e4e3
Revises:
Create Date: 2026-05-25 11:39:51.466067

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d38aff65e4e3"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEGACY_COLUMNS = {
    "id",
    "sample_name",
    "workflow_name",
    "workflow_version",
    "status",
    "input_path",
    "output_dir",
    "report_path",
    "error_message",
    "started_at",
    "finished_at",
    "created_at",
    "updated_at",
}

INDEX_COLUMNS = {
    "ix_qc_runs_run_name": "run_name",
    "ix_qc_runs_sample_name": "sample_name",
    "ix_qc_runs_status": "status",
    "ix_qc_runs_workflow_engine": "workflow_engine",
    "ix_qc_runs_workflow_name": "workflow_name",
}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("qc_runs"):
        _adopt_legacy_qc_runs_table()
        return

    _create_qc_runs_table()


def _create_qc_runs_table() -> None:
    op.create_table(
        "qc_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_name", sa.String(length=255), nullable=False),
        sa.Column("sample_name", sa.String(length=255), nullable=True),
        sa.Column("workflow_name", sa.String(length=100), nullable=False),
        sa.Column("workflow_engine", sa.String(length=50), nullable=False),
        sa.Column("workflow_version", sa.String(length=50), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "RUNNING",
                "COMPLETED",
                "FAILED",
                name="qc_run_status",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("input_path", sa.Text(), nullable=True),
        sa.Column("output_dir", sa.Text(), nullable=True),
        sa.Column("report_path", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_qc_runs_run_name"), "qc_runs", ["run_name"], unique=False)
    op.create_index(
        op.f("ix_qc_runs_sample_name"), "qc_runs", ["sample_name"], unique=False
    )
    op.create_index(op.f("ix_qc_runs_status"), "qc_runs", ["status"], unique=False)
    op.create_index(
        op.f("ix_qc_runs_workflow_engine"), "qc_runs", ["workflow_engine"], unique=False
    )
    op.create_index(
        op.f("ix_qc_runs_workflow_name"), "qc_runs", ["workflow_name"], unique=False
    )


def _adopt_legacy_qc_runs_table() -> None:
    """Bring a pre-Alembic ``create_all`` table under migration control."""
    columns = {
        column["name"]: column
        for column in sa.inspect(op.get_bind()).get_columns("qc_runs")
    }
    missing_legacy_columns = sorted(LEGACY_COLUMNS - columns.keys())
    if missing_legacy_columns:
        missing = ", ".join(missing_legacy_columns)
        raise RuntimeError(
            "Cannot adopt existing qc_runs table: "
            f"unrecognized legacy schema (missing: {missing})"
        )

    with op.batch_alter_table("qc_runs") as batch_op:
        if "run_name" not in columns:
            batch_op.add_column(
                sa.Column("run_name", sa.String(length=255), nullable=True)
            )
        if "workflow_engine" not in columns:
            batch_op.add_column(
                sa.Column("workflow_engine", sa.String(length=50), nullable=True)
            )

    qc_runs = sa.table(
        "qc_runs",
        sa.column("id", sa.String(length=36)),
        sa.column("run_name", sa.String(length=255)),
        sa.column("sample_name", sa.String(length=255)),
        sa.column("workflow_engine", sa.String(length=50)),
    )
    op.execute(
        qc_runs.update()
        .where(qc_runs.c.run_name.is_(None))
        .values(run_name=sa.func.coalesce(qc_runs.c.sample_name, qc_runs.c.id))
    )
    op.execute(
        qc_runs.update()
        .where(qc_runs.c.workflow_engine.is_(None))
        .values(workflow_engine="nextflow")
    )

    refreshed_columns = {
        column["name"]: column
        for column in sa.inspect(op.get_bind()).get_columns("qc_runs")
    }
    with op.batch_alter_table("qc_runs") as batch_op:
        batch_op.alter_column(
            "run_name",
            existing_type=refreshed_columns["run_name"]["type"],
            nullable=False,
        )
        batch_op.alter_column(
            "workflow_engine",
            existing_type=refreshed_columns["workflow_engine"]["type"],
            nullable=False,
        )
        if not refreshed_columns["sample_name"]["nullable"]:
            batch_op.alter_column(
                "sample_name",
                existing_type=refreshed_columns["sample_name"]["type"],
                nullable=True,
            )
        if not refreshed_columns["input_path"]["nullable"]:
            batch_op.alter_column(
                "input_path",
                existing_type=refreshed_columns["input_path"]["type"],
                nullable=True,
            )

    existing_indexes = {
        index["name"]
        for index in sa.inspect(op.get_bind()).get_indexes("qc_runs")
        if index["name"] is not None
    }
    for index_name, column_name in INDEX_COLUMNS.items():
        if index_name not in existing_indexes:
            op.create_index(index_name, "qc_runs", [column_name], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_qc_runs_workflow_name"), table_name="qc_runs")
    op.drop_index(op.f("ix_qc_runs_workflow_engine"), table_name="qc_runs")
    op.drop_index(op.f("ix_qc_runs_status"), table_name="qc_runs")
    op.drop_index(op.f("ix_qc_runs_sample_name"), table_name="qc_runs")
    op.drop_index(op.f("ix_qc_runs_run_name"), table_name="qc_runs")
    op.drop_table("qc_runs")
