from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.qc_run import QcRunStatus


class QcRunCreate(BaseModel):
    run_name: str | None = Field(default=None, min_length=1, max_length=255)
    sample_name: str = Field(min_length=1, max_length=255)
    workflow_name: str = Field(default="fastqc-multiqc", min_length=1, max_length=100)
    workflow_engine: str = Field(default="nextflow", min_length=1, max_length=50)
    workflow_version: str = Field(default="0.1.0", min_length=1, max_length=50)
    status: QcRunStatus = QcRunStatus.PENDING
    input_path: str = Field(min_length=1)
    output_dir: str | None = None
    report_path: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @model_validator(mode="after")
    def default_run_name(self) -> Self:
        if self.run_name is None:
            self.run_name = self.sample_name
        return self


class QcRunRegisterLocal(BaseModel):
    run_name: str = Field(min_length=1, max_length=255)
    workflow_name: str = Field(default="fastqc-multiqc", min_length=1, max_length=100)
    workflow_engine: str = Field(default="nextflow", min_length=1, max_length=50)
    workflow_version: str = Field(default="0.1.0", min_length=1, max_length=50)
    status: QcRunStatus = QcRunStatus.COMPLETED
    output_path: str = Field(min_length=1)
    multiqc_report_path: str = Field(min_length=1)
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
    report_path: str | None
    multiqc_report_path: str | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class QcRunSeedResponse(BaseModel):
    created: int
    runs: list[QcRunRead]
