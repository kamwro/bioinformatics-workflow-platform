from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse
from pydantic import ValidationError

from app.api.deps import get_qc_run_service
from app.schemas.qc_run import (
    DEFAULT_RUN_DIR,
    DEFAULT_SAMPLESHEET_PATH,
    QcRunCreate,
    QcRunRead,
    QcRunRegisterLocal,
    QcRunRegisterLocalUpload,
    QcRunSeedResponse,
)
from app.services.qc_runs import QcRunService

router = APIRouter(prefix="/qc-runs", tags=["qc-runs"])

QcRunServiceDep = Annotated[QcRunService, Depends(get_qc_run_service)]


@router.post(
    "/seed",
    response_model=QcRunSeedResponse,
    status_code=status.HTTP_201_CREATED,
)
def seed_qc_runs(service: QcRunServiceDep) -> QcRunSeedResponse:
    runs = service.seed_demo_runs()
    return QcRunSeedResponse(
        created=len(runs),
        runs=[QcRunRead.model_validate(run) for run in runs],
    )


@router.get("", response_model=list[QcRunRead])
def list_qc_runs(service: QcRunServiceDep):
    return service.list_runs()


@router.post("", response_model=QcRunRead, status_code=status.HTTP_201_CREATED)
def create_qc_run(body: QcRunCreate, service: QcRunServiceDep):
    return service.create_run(body)


@router.post(
    "/register-local",
    response_model=QcRunRead,
    status_code=status.HTTP_201_CREATED,
)
def register_local_qc_run(body: QcRunRegisterLocal, service: QcRunServiceDep):
    return service.register_completed_local_run(body)


@router.post(
    "/register-local-upload",
    response_model=QcRunRead,
    status_code=status.HTTP_201_CREATED,
)
async def register_local_qc_run_upload(
    run_name: Annotated[str, Form()],
    multiqc_report: Annotated[UploadFile, File()],
    service: QcRunServiceDep,
    samplesheet_path: Annotated[str, Form()] = DEFAULT_SAMPLESHEET_PATH,
    run_dir: Annotated[str, Form()] = DEFAULT_RUN_DIR,
    pipeline_name: Annotated[str, Form()] = "fastqc-multiqc",
    pipeline_version: Annotated[str, Form()] = "0.1.0",
    sample_count: Annotated[int | None, Form()] = None,
    started_at: Annotated[datetime | None, Form()] = None,
    completed_at: Annotated[datetime | None, Form()] = None,
):
    try:
        body = QcRunRegisterLocalUpload(
            run_name=run_name,
            samplesheet_path=samplesheet_path,
            run_dir=run_dir,
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            sample_count=sample_count,
            started_at=started_at,
            completed_at=completed_at,
        )
    except ValidationError as exc:
        # The body is assembled from individual Form fields, so model-level
        # validation runs here rather than during request parsing. Re-raise as a
        # request validation error so callers get a consistent 422 response.
        raise RequestValidationError(exc.errors()) from exc
    report_content = await multiqc_report.read()
    return service.register_uploaded_local_run(
        body,
        report_filename=multiqc_report.filename,
        report_content=report_content,
    )


@router.get("/{run_id}", response_model=QcRunRead)
def get_qc_run(run_id: str, service: QcRunServiceDep):
    return service.get_run(run_id)


@router.get("/{run_id}/multiqc-report")
def download_multiqc_report(run_id: str, service: QcRunServiceDep) -> FileResponse:
    report_path = service.get_uploaded_report_path(run_id)
    return FileResponse(report_path, media_type="text/html")
