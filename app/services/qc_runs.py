import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.qc_run import QcRun, QcRunStatus
from app.repositories.qc_runs import QcRunRepository
from app.schemas.qc_run import (
    QcRunCreate,
    QcRunRegisterLocal,
    QcRunRegisterLocalUpload,
)

MULTIQC_REPORT_NAME = "multiqc_report.html"


class QcRunService:
    def __init__(self, db: Session) -> None:
        self.repo = QcRunRepository(db)

    def list_runs(self) -> list[QcRun]:
        return self.repo.list_runs()

    def get_run(self, run_id: str) -> QcRun:
        run = self.repo.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="QC run not found")
        return run

    def create_run(self, data: QcRunCreate) -> QcRun:
        return self.repo.create(data)

    def register_completed_local_run(self, data: QcRunRegisterLocal) -> QcRun:
        run = QcRun(
            run_name=data.run_name,
            sample_name=None,
            workflow_name=data.workflow_name,
            workflow_engine=data.workflow_engine,
            workflow_version=data.workflow_version,
            status=data.status,
            input_path=data.samplesheet_path,
            output_dir=data.output_path,
            report_path=data.multiqc_report_path,
            started_at=data.started_at,
            finished_at=data.completed_at,
        )
        return self.repo.save(run)

    def register_uploaded_local_run(
        self,
        data: QcRunRegisterLocalUpload,
        *,
        report_filename: str | None,
        report_content: bytes,
    ) -> QcRun:
        clean_filename = self._clean_upload_filename(report_filename)
        if clean_filename != MULTIQC_REPORT_NAME:
            raise HTTPException(
                status_code=400,
                detail=f"multiqc_report filename must be {MULTIQC_REPORT_NAME}",
            )
        if not report_content:
            raise HTTPException(
                status_code=400,
                detail="multiqc_report must not be empty",
            )

        run_id = str(uuid4())
        storage_path = self._multiqc_report_storage_path(run_id)
        try:
            storage_path.parent.mkdir(parents=True, exist_ok=True)
            storage_path.write_bytes(report_content)
        except OSError as exc:
            raise HTTPException(
                status_code=500,
                detail="Could not store uploaded MultiQC report",
            ) from exc

        run = QcRun(
            id=run_id,
            run_name=data.run_name,
            sample_name=None,
            workflow_name=data.pipeline_name,
            workflow_engine="nextflow",
            workflow_version=data.pipeline_version,
            status=QcRunStatus.COMPLETED,
            sample_count=data.sample_count,
            input_path=data.samplesheet_path,
            output_dir=data.run_dir,
            report_filename=clean_filename,
            report_path=storage_path.as_posix(),
            report_size_bytes=len(report_content),
            report_sha256=hashlib.sha256(report_content).hexdigest(),
            started_at=data.started_at,
            finished_at=data.completed_at or datetime.now(UTC),
        )
        return self.repo.save(run)

    def get_uploaded_report_path(self, run_id: str) -> Path:
        """Resolve a run's own backend-owned MultiQC report, refusing anything else.

        Only runs created via ``register-local-upload`` own a stored artifact:
        they carry server-computed integrity metadata and the canonical path
        ``ARTIFACT_ROOT/qc-runs/{run_id}/multiqc_report.html``. Path-only
        ``register-local`` records lack that metadata, and any ``report_path``
        that is not exactly this run's canonical location is rejected. So a
        record can never be used to serve another run's report or an arbitrary
        file from disk, even one that happens to live under ``ARTIFACT_ROOT``.
        """
        run = self.get_run(run_id)
        canonical = (
            Path(settings.ARTIFACT_ROOT).resolve()
            / "qc-runs"
            / run.id
            / MULTIQC_REPORT_NAME
        )
        owns_uploaded_report = (
            run.report_filename == MULTIQC_REPORT_NAME
            and run.report_size_bytes is not None
            and run.report_sha256 is not None
            and run.report_path is not None
            and Path(run.report_path).resolve() == canonical
        )
        if not owns_uploaded_report or not canonical.is_file():
            raise HTTPException(status_code=404, detail="MultiQC report not found")
        return canonical

    def seed_demo_runs(self) -> list[QcRun]:
        now = datetime.now(UTC)
        demo_runs = [
            QcRunCreate(
                sample_name="sample_01",
                workflow_name="fastqc-multiqc",
                workflow_version="0.1.0",
                status=QcRunStatus.COMPLETED,
                input_path="pipelines/qc/testdata/sample_01.fastq",
                output_dir="results/qc",
                report_path="results/qc/multiqc/multiqc_report.html",
                started_at=now - timedelta(minutes=5),
                finished_at=now - timedelta(minutes=3),
            ),
            QcRunCreate(
                sample_name="sample_02",
                workflow_name="fastqc-multiqc",
                workflow_version="0.1.0",
                status=QcRunStatus.PENDING,
                input_path="pipelines/qc/testdata/sample_02.fastq",
                output_dir="results/qc",
                report_path=None,
            ),
        ]
        return self.repo.create_many(demo_runs)

    def _multiqc_report_storage_path(self, run_id: str) -> Path:
        return Path(settings.ARTIFACT_ROOT) / "qc-runs" / run_id / MULTIQC_REPORT_NAME

    @staticmethod
    def _clean_upload_filename(filename: str | None) -> str:
        if filename is None:
            return ""
        return filename.replace("\\", "/").rsplit("/", maxsplit=1)[-1]
