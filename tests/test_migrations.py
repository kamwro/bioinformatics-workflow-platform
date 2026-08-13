from datetime import UTC, datetime
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from app.core.config import settings

HEAD_REVISION = "b7d4e9c2a1f3"


def test_migrations_build_current_schema_from_scratch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _upgrade_database(tmp_path / "fresh.db", monkeypatch)

    inspector = sa.inspect(engine)
    assert _current_revision(engine) == HEAD_REVISION
    assert {column["name"] for column in inspector.get_columns("qc_runs")} >= {
        "run_name",
        "workflow_engine",
        "report_filename",
        "sample_count",
        "report_size_bytes",
        "report_sha256",
    }


def test_migrations_adopt_pre_alembic_schema_without_losing_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "legacy.db"
    engine = sa.create_engine(f"sqlite:///{database_path}")
    legacy_runs = _create_legacy_qc_runs_table(engine)
    created_at = datetime(2026, 5, 1, tzinfo=UTC)
    with engine.begin() as connection:
        connection.execute(
            legacy_runs.insert().values(
                id="legacy-run-id",
                sample_name="legacy-sample",
                workflow_name="fastqc-multiqc",
                workflow_version="0.1.0",
                status="COMPLETED",
                input_path="legacy.fastq",
                report_path="legacy/multiqc_report.html",
                created_at=created_at,
                updated_at=created_at,
            )
        )
    engine.dispose()

    upgraded_engine = _upgrade_database(database_path, monkeypatch)

    inspector = sa.inspect(upgraded_engine)
    columns = {column["name"]: column for column in inspector.get_columns("qc_runs")}
    with upgraded_engine.connect() as connection:
        row = (
            connection.execute(
                sa.text(
                    "SELECT id, run_name, sample_name, workflow_engine, input_path "
                    "FROM qc_runs WHERE id = 'legacy-run-id'"
                )
            )
            .mappings()
            .one()
        )

    assert _current_revision(upgraded_engine) == HEAD_REVISION
    assert row == {
        "id": "legacy-run-id",
        "run_name": "legacy-sample",
        "sample_name": "legacy-sample",
        "workflow_engine": "nextflow",
        "input_path": "legacy.fastq",
    }
    assert columns["run_name"]["nullable"] is False
    assert columns["workflow_engine"]["nullable"] is False
    assert columns["sample_name"]["nullable"] is True
    assert columns["input_path"]["nullable"] is True


def _upgrade_database(
    database_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> sa.Engine:
    database_url = f"sqlite:///{database_path}"
    monkeypatch.setattr(settings, "DATABASE_URL", database_url)
    alembic_config = Config("alembic.ini")
    command.upgrade(alembic_config, "head")
    return sa.create_engine(database_url)


def _current_revision(engine: sa.Engine) -> str:
    with engine.connect() as connection:
        revision = connection.scalar(sa.text("SELECT version_num FROM alembic_version"))
    assert isinstance(revision, str)
    return revision


def _create_legacy_qc_runs_table(engine: sa.Engine) -> sa.Table:
    metadata = sa.MetaData()
    table = sa.Table(
        "qc_runs",
        metadata,
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("sample_name", sa.String(length=255), nullable=False, index=True),
        sa.Column("workflow_name", sa.String(length=100), nullable=False, index=True),
        sa.Column("workflow_version", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, index=True),
        sa.Column("input_path", sa.Text(), nullable=False),
        sa.Column("output_dir", sa.Text(), nullable=True),
        sa.Column("report_path", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    metadata.create_all(engine)
    return table
