from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.qc_run import QcRunStatus
from app.schemas.qc_run import QcRunCreate, QcRunRead, QcRunRegisterLocal
from app.services.qc_runs import QcRunService


def test_seed_qc_runs(client: TestClient) -> None:
    response = client.post("/qc-runs/seed")

    assert response.status_code == 201
    body = response.json()
    assert body["created"] == 2
    assert {run["sample_name"] for run in body["runs"]} == {"sample_01", "sample_02"}
    assert body["runs"][0]["status"] in {"COMPLETED", "PENDING"}


def test_list_qc_runs_after_seed(client: TestClient) -> None:
    client.post("/qc-runs/seed")

    response = client.get("/qc-runs")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert all(run["workflow_name"] == "fastqc-multiqc" for run in body)


def test_get_qc_run_by_id(client: TestClient) -> None:
    seeded = client.post("/qc-runs/seed").json()
    run_id = seeded["runs"][0]["id"]

    response = client.get(f"/qc-runs/{run_id}")

    assert response.status_code == 200
    assert response.json()["id"] == run_id


def test_get_qc_run_not_found(client: TestClient) -> None:
    response = client.get("/qc-runs/not-a-real-id")

    assert response.status_code == 404
    assert response.json()["detail"] == "QC run not found"


def test_create_qc_run(client: TestClient) -> None:
    response = client.post(
        "/qc-runs",
        json={
            "sample_name": "sample_03",
            "workflow_name": "fastqc-multiqc",
            "workflow_version": "0.1.0",
            "status": "RUNNING",
            "input_path": "pipelines/qc/testdata/sample_03.fastq",
            "output_dir": "results/qc",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["sample_name"] == "sample_03"
    assert body["run_name"] == "sample_03"
    assert body["workflow_engine"] == "nextflow"
    assert body["status"] == "RUNNING"


def test_register_completed_local_qc_run_endpoint(client: TestClient) -> None:
    response = client.post(
        "/qc-runs/register-local",
        json={
            "run_name": "local-qc-2026-05-23",
            "workflow_name": "fastqc-multiqc",
            "status": "COMPLETED",
            "output_path": "results/qc",
            "multiqc_report_path": "results/qc/multiqc/multiqc_report.html",
            "started_at": "2026-05-23T08:00:00Z",
            "completed_at": "2026-05-23T08:07:00Z",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["run_name"] == "local-qc-2026-05-23"
    assert body["sample_name"] is None
    assert body["workflow_engine"] == "nextflow"
    assert body["status"] == "COMPLETED"
    assert body["input_path"] is None
    assert body["output_path"] == "results/qc"
    assert body["multiqc_report_path"] == "results/qc/multiqc/multiqc_report.html"
    assert body["completed_at"].startswith("2026-05-23T08:07:00")


def test_register_local_qc_run_requires_completed_status(
    client: TestClient,
) -> None:
    response = client.post(
        "/qc-runs/register-local",
        json={
            "run_name": "local-qc-running",
            "workflow_name": "fastqc-multiqc",
            "status": "RUNNING",
            "output_path": "results/qc",
            "multiqc_report_path": "results/qc/multiqc/multiqc_report.html",
            "started_at": "2026-05-23T08:00:00Z",
            "completed_at": "2026-05-23T08:07:00Z",
        },
    )

    assert response.status_code == 422


def test_database_service_creates_run(db: Session) -> None:
    service = QcRunService(db)

    run = service.create_run(
        QcRunCreate(
            sample_name="db_sample",
            status=QcRunStatus.PENDING,
            input_path="pipelines/qc/testdata/sample_01.fastq",
        )
    )

    assert run.id is not None
    assert service.get_run(run.id).sample_name == "db_sample"


def test_service_registers_completed_local_qc_run(db: Session) -> None:
    service = QcRunService(db)
    started_at = datetime(2026, 5, 23, 8, 0, tzinfo=UTC)
    completed_at = started_at + timedelta(minutes=7)

    run = service.register_completed_local_run(
        QcRunRegisterLocal(
            run_name="service-local-qc",
            workflow_name="fastqc-multiqc",
            output_path="results/qc",
            multiqc_report_path="results/qc/multiqc/multiqc_report.html",
            started_at=started_at,
            completed_at=completed_at,
        )
    )

    assert run.id is not None
    assert run.run_name == "service-local-qc"
    assert run.sample_name is None
    assert run.workflow_engine == "nextflow"
    assert run.status == QcRunStatus.COMPLETED
    assert run.output_dir == "results/qc"
    assert run.report_path == "results/qc/multiqc/multiqc_report.html"
    assert run.finished_at is not None
    assert run.finished_at.replace(tzinfo=UTC) == completed_at


def test_status_serialization_from_model(db: Session) -> None:
    service = QcRunService(db)
    run = service.create_run(
        QcRunCreate(
            sample_name="serialized_sample",
            status=QcRunStatus.COMPLETED,
            input_path="pipelines/qc/testdata/sample_01.fastq",
            output_dir="results/qc",
            report_path="results/qc/multiqc/multiqc_report.html",
        )
    )

    payload = QcRunRead.model_validate(run).model_dump(mode="json")

    assert payload["status"] == "COMPLETED"
    assert payload["report_path"] == "results/qc/multiqc/multiqc_report.html"
    assert payload["multiqc_report_path"] == "results/qc/multiqc/multiqc_report.html"
