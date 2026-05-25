from sqlalchemy.engine import Engine

from app.db.base import Base
from app.db.session import engine
from app.models import QcRun  # noqa: F401


def init_db(db_engine: Engine = engine) -> None:
    Base.metadata.create_all(bind=db_engine)
