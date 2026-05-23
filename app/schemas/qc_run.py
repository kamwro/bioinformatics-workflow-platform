from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.qc_run import QcRunStatus


class QcRunCreate(BaseModel):
    sample_name: str = Field(min_length=1, max_length=255)
    workflow_name: str = Field(default="fastqc-multiqc", min_length=1, max_length=100)
    workflow_version: str = Field(default="0.1.0", min_length=1, max_length=50)
    status: QcRunStatus = QcRunStatus.PENDING
    input_path: str = Field(min_length=1)
    output_dir: str | None = None
    report_path: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class QcRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sample_name: str
    workflow_name: str
    workflow_version: str
    status: QcRunStatus
    input_path: str
    output_dir: str | None
    report_path: str | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


class QcRunSeedResponse(BaseModel):
    created: int
    runs: list[QcRunRead]
