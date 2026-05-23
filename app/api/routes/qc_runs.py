from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import get_qc_run_service
from app.schemas.qc_run import (
    QcRunCreate,
    QcRunRead,
    QcRunRegisterLocal,
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


@router.get("/{run_id}", response_model=QcRunRead)
def get_qc_run(run_id: str, service: QcRunServiceDep):
    return service.get_run(run_id)
