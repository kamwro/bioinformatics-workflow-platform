from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.qc_run import QcRunStatus
from app.schemas.qc_run import QcRunCreate, QcRunRead
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
    assert body["status"] == "RUNNING"


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
