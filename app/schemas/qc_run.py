from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.qc_run import QcRunStatus

DEFAULT_SAMPLESHEET_PATH = "pipelines/qc/samplesheet.csv"
DEFAULT_RUN_DIR = "results/qc"
DEFAULT_INPUT_PATH = "pipelines/qc/testdata/sample_01.fastq"
DEFAULT_MULTIQC_REPORT_PATH = "results/qc/multiqc/multiqc_report.html"


def _reject_naive_datetime(value: datetime | None) -> None:
    if value is not None and value.tzinfo is None:
        raise ValueError(
            "must be timezone-aware (include a UTC offset, for example '...Z')"
        )


class QcRunCreate(BaseModel):
    run_name: str | None = Field(default=None, min_length=1, max_length=255)
    sample_name: str = Field(min_length=1, max_length=255)
    workflow_name: str = Field(default="fastqc-multiqc", min_length=1, max_length=100)
    workflow_engine: str = Field(default="nextflow", min_length=1, max_length=50)
    workflow_version: str = Field(default="0.1.0", min_length=1, max_length=50)
    status: QcRunStatus = QcRunStatus.PENDING
    input_path: str = Field(default=DEFAULT_INPUT_PATH, min_length=1)
    output_dir: str | None = DEFAULT_RUN_DIR
    report_path: str | None = DEFAULT_MULTIQC_REPORT_PATH
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @model_validator(mode="after")
    def default_run_name(self) -> Self:
        if self.run_name is None:
            self.run_name = self.sample_name
        return self


class QcRunRegisterLocal(BaseModel):
    """Register a completed local QC run from paths and metadata only.

    The MultiQC report stays on the caller's filesystem; the API records the
    provided paths without copying anything. Use ``register-local-upload`` to
    upload and store the report artifact server-side.
    """

    run_name: str = Field(min_length=1, max_length=255)
    workflow_name: str = Field(default="fastqc-multiqc", min_length=1, max_length=100)
    workflow_engine: str = Field(default="nextflow", min_length=1, max_length=50)
    workflow_version: str = Field(default="0.1.0", min_length=1, max_length=50)
    status: QcRunStatus = QcRunStatus.COMPLETED
    output_path: str = Field(default=DEFAULT_RUN_DIR, min_length=1)
    multiqc_report_path: str = Field(default=DEFAULT_MULTIQC_REPORT_PATH, min_length=1)
    samplesheet_path: str | None = Field(
        default=DEFAULT_SAMPLESHEET_PATH,
        description="Samplesheet path, stored as the run's input_path.",
    )
    started_at: datetime
    completed_at: datetime

    @field_validator(
        "run_name",
        "workflow_name",
        "workflow_engine",
        "workflow_version",
        "output_path",
        "multiqc_report_path",
    )
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("samplesheet_path")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("workflow_engine")
    @classmethod
    def normalize_workflow_engine(cls, value: str) -> str:
        return value.lower()

    @model_validator(mode="after")
    def validate_completed_run(self) -> Self:
        if self.status != QcRunStatus.COMPLETED:
            raise ValueError("register-local only accepts completed QC runs")
        if self.completed_at < self.started_at:
            raise ValueError("completed_at must be greater than or equal to started_at")
        return self


class QcRunRegisterLocalUpload(BaseModel):
    """Register a completed local QC run and upload its MultiQC report.

    The API stores the uploaded report under ``artifacts/qc-runs/{run_id}/`` and
    records fuller provenance (samplesheet, run directory, sample count). Use
    ``register-local`` for a lightweight path-only record without uploading.
    """

    run_name: str = Field(min_length=1, max_length=255)
    samplesheet_path: str = Field(default=DEFAULT_SAMPLESHEET_PATH, min_length=1)
    run_dir: str = Field(default=DEFAULT_RUN_DIR, min_length=1)
    pipeline_name: str = Field(default="fastqc-multiqc", min_length=1, max_length=100)
    pipeline_version: str = Field(default="0.1.0", min_length=1, max_length=50)
    sample_count: int | None = Field(default=None, ge=0)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @field_validator(
        "run_name",
        "samplesheet_path",
        "run_dir",
        "pipeline_name",
        "pipeline_version",
    )
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("started_at", "completed_at")
    @classmethod
    def ensure_timezone_aware(cls, value: datetime | None) -> datetime | None:
        _reject_naive_datetime(value)
        return value

    @model_validator(mode="after")
    def validate_run_timing(self) -> Self:
        if (
            self.started_at is not None
            and self.completed_at is not None
            and self.completed_at < self.started_at
        ):
            raise ValueError("completed_at must be greater than or equal to started_at")
        return self


class QcRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_name: str
    sample_name: str | None
    workflow_name: str
    workflow_engine: str
    workflow_version: str
    status: QcRunStatus
    input_path: str | None
    output_dir: str | None
    output_path: str | None
    report_filename: str | None
    report_path: str | None
    multiqc_report_filename: str | None
    multiqc_report_path: str | None
    multiqc_report_storage_path: str | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class QcRunSeedResponse(BaseModel):
    created: int
    runs: list[QcRunRead]
