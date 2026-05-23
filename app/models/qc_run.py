from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class QcRunStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class QcRun(Base):
    __tablename__ = "qc_runs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    run_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    sample_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    workflow_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="fastqc-multiqc",
        index=True,
    )
    workflow_engine: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="nextflow",
        index=True,
    )
    workflow_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="0.1.0",
    )
    status: Mapped[QcRunStatus] = mapped_column(
        SqlEnum(
            QcRunStatus,
            name="qc_run_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            native_enum=False,
            length=20,
        ),
        nullable=False,
        default=QcRunStatus.PENDING,
        index=True,
    )
    input_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_dir: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    @property
    def output_path(self) -> str | None:
        return self.output_dir

    @property
    def multiqc_report_path(self) -> str | None:
        return self.report_path

    @property
    def completed_at(self) -> datetime | None:
        return self.finished_at
