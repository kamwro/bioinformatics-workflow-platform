from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.qc_run import QcRun
from app.schemas.qc_run import QcRunCreate


class QcRunRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_runs(self) -> list[QcRun]:
        stmt = select(QcRun).order_by(QcRun.created_at.desc(), QcRun.sample_name.asc())
        return list(self.db.scalars(stmt).all())

    def get(self, run_id: str) -> QcRun | None:
        stmt = select(QcRun).where(QcRun.id == run_id)
        return self.db.scalars(stmt).first()

    def save(self, run: QcRun) -> QcRun:
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def create(self, data: QcRunCreate) -> QcRun:
        run = QcRun(**data.model_dump())
        return self.save(run)

    def create_many(self, records: list[QcRunCreate]) -> list[QcRun]:
        runs = [QcRun(**record.model_dump()) for record in records]
        self.db.add_all(runs)
        self.db.commit()
        for run in runs:
            self.db.refresh(run)
        return runs
