from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.qc_run import QcRun, QcRunStatus
from app.repositories.qc_runs import QcRunRepository
from app.schemas.qc_run import QcRunCreate


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
            ),
        ]
        return self.repo.create_many(demo_runs)
