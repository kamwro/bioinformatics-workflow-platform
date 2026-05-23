from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.qc_runs import QcRunService

DbSessionDep = Annotated[Session, Depends(get_db)]


def get_qc_run_service(db: DbSessionDep) -> QcRunService:
    return QcRunService(db)
