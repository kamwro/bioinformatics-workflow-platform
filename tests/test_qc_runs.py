import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.qc_run import QcRun, QcRunStatus
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


def test_create_qc_run_uses_default_paths(client: TestClient) -> None:
    response = client.post("/qc-runs", json={"sample_name": "sample_defaults"})

    assert response.status_code == 201
    body = response.json()
    assert body["input_path"] == "pipelines/qc/testdata/sample_01.fastq"
    assert body["output_dir"] == "results/qc"
    assert body["report_path"] == "results/qc/multiqc/multiqc_report.html"


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
    assert body["input_path"] == "pipelines/qc/samplesheet.csv"
    assert body["output_path"] == "results/qc"
    assert body["multiqc_report_path"] == "results/qc/multiqc/multiqc_report.html"
    assert body["completed_at"].startswith("2026-05-23T08:07:00")


def test_register_completed_local_qc_run_with_samplesheet_path(
    client: TestClient,
) -> None:
    response = client.post(
        "/qc-runs/register-local",
        json={
            "run_name": "local-qc-with-samplesheet",
            "workflow_name": "fastqc-multiqc",
            "status": "COMPLETED",
            "output_path": "results/qc",
            "multiqc_report_path": "results/qc/multiqc/multiqc_report.html",
            "samplesheet_path": "custom/run_samplesheet.csv",
            "started_at": "2026-05-23T08:00:00Z",
            "completed_at": "2026-05-23T08:07:00Z",
        },
    )

    assert response.status_code == 201
    assert response.json()["input_path"] == "custom/run_samplesheet.csv"


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


def test_register_local_upload_accepts_and_stores_multiqc_report(
    client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    artifact_root = tmp_path / "artifacts"
    monkeypatch.setattr(settings, "ARTIFACT_ROOT", str(artifact_root))

    response = client.post(
        "/qc-runs/register-local-upload",
        data={
            "run_name": "uploaded-local-qc",
            "samplesheet_path": "pipelines/qc/samplesheet.csv",
            "run_dir": "results/qc",
            "pipeline_name": "fastqc-multiqc",
            "pipeline_version": "0.1.0",
            "sample_count": "2",
        },
        files={
            "multiqc_report": (
                "multiqc_report.html",
                b"<html><body>MultiQC</body></html>",
                "application/octet-stream",
            )
        },
    )

    assert response.status_code == 201
    body = response.json()
    stored_path = Path(body["multiqc_report_storage_path"])
    assert body["run_name"] == "uploaded-local-qc"
    assert body["status"] == "COMPLETED"
    assert body["sample_count"] == 2
    assert body["report_size_bytes"] == len(b"<html><body>MultiQC</body></html>")
    assert (
        body["report_sha256"]
        == hashlib.sha256(b"<html><body>MultiQC</body></html>").hexdigest()
    )
    assert body["input_path"] == "pipelines/qc/samplesheet.csv"
    assert body["output_path"] == "results/qc"
    assert body["report_filename"] == "multiqc_report.html"
    assert body["multiqc_report_filename"] == "multiqc_report.html"
    assert body["report_path"] == stored_path.as_posix()
    assert body["multiqc_report_path"] == stored_path.as_posix()
    assert stored_path == artifact_root / "qc-runs" / body["id"] / "multiqc_report.html"
    assert stored_path.read_bytes() == b"<html><body>MultiQC</body></html>"

    db_run = db.get(QcRun, body["id"])
    assert db_run is not None
    assert db_run.report_filename == "multiqc_report.html"
    assert db_run.report_path == stored_path.as_posix()
    assert db_run.sample_count == 2
    assert db_run.report_size_bytes == len(b"<html><body>MultiQC</body></html>")
    assert (
        db_run.report_sha256
        == hashlib.sha256(b"<html><body>MultiQC</body></html>").hexdigest()
    )


def test_register_local_upload_persists_sample_count_and_timing(
    client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(settings, "ARTIFACT_ROOT", str(tmp_path / "artifacts"))

    response = client.post(
        "/qc-runs/register-local-upload",
        data={
            "run_name": "timed-run",
            "sample_count": "3",
            "started_at": "2026-05-23T08:00:00Z",
            "completed_at": "2026-05-23T08:07:30Z",
        },
        files={
            "multiqc_report": (
                "multiqc_report.html",
                b"<html></html>",
                "text/html",
            )
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["sample_count"] == 3
    assert body["started_at"].startswith("2026-05-23T08:00:00")
    assert body["completed_at"].startswith("2026-05-23T08:07:30")
    assert body["duration_seconds"] == 450.0

    db_run = db.get(QcRun, body["id"])
    assert db_run is not None
    assert db_run.started_at is not None
    assert db_run.finished_at is not None


def test_register_local_upload_rejects_completed_before_started(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(settings, "ARTIFACT_ROOT", str(tmp_path / "artifacts"))

    response = client.post(
        "/qc-runs/register-local-upload",
        data={
            "run_name": "backwards-timing",
            "started_at": "2026-05-23T08:07:30Z",
            "completed_at": "2026-05-23T08:00:00Z",
        },
        files={
            "multiqc_report": (
                "multiqc_report.html",
                b"<html></html>",
                "text/html",
            )
        },
    )

    assert response.status_code == 422


def test_register_local_upload_rejects_missing_multiqc_report(
    client: TestClient,
) -> None:
    response = client.post(
        "/qc-runs/register-local-upload",
        data={
            "run_name": "missing-report",
            "samplesheet_path": "pipelines/qc/samplesheet.csv",
            "run_dir": "results/qc",
        },
    )

    assert response.status_code == 422


def test_register_local_upload_rejects_empty_multiqc_report(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(settings, "ARTIFACT_ROOT", str(tmp_path / "artifacts"))

    response = client.post(
        "/qc-runs/register-local-upload",
        data={
            "run_name": "empty-report",
            "samplesheet_path": "pipelines/qc/samplesheet.csv",
            "run_dir": "results/qc",
        },
        files={
            "multiqc_report": (
                "multiqc_report.html",
                b"",
                "text/html",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "multiqc_report must not be empty"


def test_register_local_upload_uses_default_paths(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(settings, "ARTIFACT_ROOT", str(tmp_path / "artifacts"))

    response = client.post(
        "/qc-runs/register-local-upload",
        data={"run_name": "defaults-run"},
        files={
            "multiqc_report": (
                "multiqc_report.html",
                b"<html></html>",
                "text/html",
            )
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["input_path"] == "pipelines/qc/samplesheet.csv"
    assert body["output_path"] == "results/qc"


def test_register_local_upload_rejects_naive_timestamps(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(settings, "ARTIFACT_ROOT", str(tmp_path / "artifacts"))

    response = client.post(
        "/qc-runs/register-local-upload",
        data={"run_name": "naive-ts", "started_at": "2026-05-23T08:00:00"},
        files={
            "multiqc_report": ("multiqc_report.html", b"<html></html>", "text/html")
        },
    )

    assert response.status_code == 422


def test_register_local_rejects_naive_timestamps(client: TestClient) -> None:
    response = client.post(
        "/qc-runs/register-local",
        json={
            "run_name": "naive-json",
            "status": "COMPLETED",
            "output_path": "results/qc",
            "multiqc_report_path": "results/qc/multiqc/multiqc_report.html",
            "started_at": "2026-05-23T08:00:00",
            "completed_at": "2026-05-23T08:07:00",
        },
    )

    assert response.status_code == 422


def test_download_multiqc_report_returns_uploaded_report(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(settings, "ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    content = b"<html><body>QC</body></html>"

    created = client.post(
        "/qc-runs/register-local-upload",
        data={"run_name": "downloadable"},
        files={"multiqc_report": ("multiqc_report.html", content, "text/html")},
    ).json()

    response = client.get(f"/qc-runs/{created['id']}/multiqc-report")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.content == content


def test_download_multiqc_report_404_for_unknown_run(client: TestClient) -> None:
    response = client.get("/qc-runs/not-a-real-id/multiqc-report")

    assert response.status_code == 404


def test_download_multiqc_report_404_for_path_only_registration(
    client: TestClient,
) -> None:
    created = client.post(
        "/qc-runs/register-local",
        json={
            "run_name": "path-only",
            "status": "COMPLETED",
            "output_path": "results/qc",
            "multiqc_report_path": "results/qc/multiqc/multiqc_report.html",
            "started_at": "2026-05-23T08:00:00Z",
            "completed_at": "2026-05-23T08:07:00Z",
        },
    ).json()

    response = client.get(f"/qc-runs/{created['id']}/multiqc-report")

    assert response.status_code == 404


def test_download_multiqc_report_404_when_stored_file_missing(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(settings, "ARTIFACT_ROOT", str(tmp_path / "artifacts"))

    created = client.post(
        "/qc-runs/register-local-upload",
        data={"run_name": "vanishing"},
        files={
            "multiqc_report": ("multiqc_report.html", b"<html></html>", "text/html")
        },
    ).json()
    Path(created["multiqc_report_storage_path"]).unlink()

    response = client.get(f"/qc-runs/{created['id']}/multiqc-report")

    assert response.status_code == 404


def test_download_multiqc_report_refuses_path_outside_artifact_root(
    client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(settings, "ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    # A real, correctly named report file that lives outside the artifact store.
    outside = tmp_path / "outside" / "multiqc_report.html"
    outside.parent.mkdir(parents=True)
    outside.write_text("<html>secret</html>", encoding="utf-8")

    run = QcRun(
        run_name="sneaky-path",
        status=QcRunStatus.COMPLETED,
        report_filename="multiqc_report.html",
        report_path=str(outside),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    response = client.get(f"/qc-runs/{run.id}/multiqc-report")

    # The file exists and is named correctly, but it is outside ARTIFACT_ROOT.
    assert response.status_code == 404


def test_download_multiqc_report_404_for_path_only_pointing_into_artifact_root(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(settings, "ARTIFACT_ROOT", str(tmp_path / "artifacts"))

    # A genuine upload creates a real report file under ARTIFACT_ROOT.
    uploaded = client.post(
        "/qc-runs/register-local-upload",
        data={"run_name": "real-upload"},
        files={
            "multiqc_report": ("multiqc_report.html", b"<html>real</html>", "text/html")
        },
    ).json()

    # A path-only record points its report path straight at that real file.
    path_only = client.post(
        "/qc-runs/register-local",
        json={
            "run_name": "path-only-pointer",
            "status": "COMPLETED",
            "output_path": "results/qc",
            "multiqc_report_path": uploaded["multiqc_report_storage_path"],
            "started_at": "2026-05-23T08:00:00Z",
            "completed_at": "2026-05-23T08:07:00Z",
        },
    ).json()

    # The path-only record must 404 (it owns no uploaded artifact), even though
    # the file it points at exists under ARTIFACT_ROOT...
    assert client.get(f"/qc-runs/{path_only['id']}/multiqc-report").status_code == 404
    # ...while the real upload still serves correctly.
    assert client.get(f"/qc-runs/{uploaded['id']}/multiqc-report").status_code == 200


def test_download_multiqc_report_requires_this_runs_canonical_path(
    client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    artifact_root = tmp_path / "artifacts"
    monkeypatch.setattr(settings, "ARTIFACT_ROOT", str(artifact_root))

    uploaded = client.post(
        "/qc-runs/register-local-upload",
        data={"run_name": "tamper"},
        files={
            "multiqc_report": ("multiqc_report.html", b"<html>x</html>", "text/html")
        },
    ).json()

    # Repoint this run at a different, real report under ARTIFACT_ROOT.
    other = artifact_root / "qc-runs" / "some-other-id" / "multiqc_report.html"
    other.parent.mkdir(parents=True)
    other.write_text("<html>other</html>", encoding="utf-8")
    run = db.get(QcRun, uploaded["id"])
    assert run is not None
    run.report_path = str(other)
    db.commit()

    # The stored path is under ARTIFACT_ROOT and correctly named, but it is not
    # this run's canonical location, so it must still 404.
    response = client.get(f"/qc-runs/{uploaded['id']}/multiqc-report")
    assert response.status_code == 404


def test_duration_seconds_normalizes_naive_timestamps() -> None:
    run = QcRun(
        run_name="tz-mix",
        status=QcRunStatus.COMPLETED,
        started_at=datetime(2026, 5, 23, 8, 0, 0),
        finished_at=datetime(2026, 5, 23, 8, 7, 30, tzinfo=UTC),
    )

    assert run.duration_seconds == 450.0


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
    assert run.input_path == "pipelines/qc/samplesheet.csv"
    assert run.output_dir == "results/qc"
    assert run.report_path == "results/qc/multiqc/multiqc_report.html"
    assert run.finished_at is not None
    assert run.finished_at.replace(tzinfo=UTC) == completed_at


def test_service_registers_completed_local_qc_run_with_samplesheet(
    db: Session,
) -> None:
    service = QcRunService(db)
    started_at = datetime(2026, 5, 23, 8, 0, tzinfo=UTC)

    run = service.register_completed_local_run(
        QcRunRegisterLocal(
            run_name="service-local-qc-samplesheet",
            output_path="results/qc",
            multiqc_report_path="results/qc/multiqc/multiqc_report.html",
            samplesheet_path="custom/run_samplesheet.csv",
            started_at=started_at,
            completed_at=started_at + timedelta(minutes=7),
        )
    )

    assert run.input_path == "custom/run_samplesheet.csv"


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
