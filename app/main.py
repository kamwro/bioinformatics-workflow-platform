from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.qc_runs import router as qc_runs_router
from app.core.config import settings
from app.db.init_db import init_db


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if settings.AUTO_CREATE_TABLES:
        init_db()
    yield


app = FastAPI(
    title="BioFlowOps API",
    version="0.1.0",
    description="Metadata API for a small bioinformatics QC workflow platform.",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(qc_runs_router)
