from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_CONTENT = b"<html><body>BioFlowOps E2E report</body></html>"

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        os.name == "nt",
        reason="The local Nextflow workflow is supported through WSL on Windows.",
    ),
]


def test_cli_start_runs_workflow_and_registers_report_end_to_end(
    tmp_path: Path,
) -> None:
    samplesheet = _write_samplesheet(tmp_path)
    run_dir = tmp_path / "results"
    invocation_path = tmp_path / "nextflow-invocation.json"
    fake_bin = _write_fake_nextflow(tmp_path, exit_code=0)

    with _running_api(tmp_path) as api_url:
        completed = _run_cli_start(
            api_url=api_url,
            samplesheet=samplesheet,
            run_dir=run_dir,
            fake_bin=fake_bin,
            invocation_path=invocation_path,
        )

        assert completed.returncode == 0, completed.stderr
        assert "Run registered successfully." in completed.stdout
        assert "Samples: 2" in completed.stdout

        runs = _get_json(f"{api_url}/qc-runs")
        assert isinstance(runs, list)
        assert len(runs) == 1
        run = runs[0]

        assert run["run_name"] == "e2e-run"
        assert run["status"] == "COMPLETED"
        assert run["workflow_name"] == "fastqc-multiqc"
        assert run["workflow_engine"] == "nextflow"
        assert run["sample_count"] == 2
        assert run["input_path"] == str(samplesheet)
        assert run["output_dir"] == str(run_dir)
        assert run["report_filename"] == "multiqc_report.html"
        assert run["report_size_bytes"] == len(REPORT_CONTENT)
        assert run["report_sha256"] == hashlib.sha256(REPORT_CONTENT).hexdigest()
        assert run["duration_seconds"] is not None

        with urlopen(  # noqa: S310 - the test controls the loopback URL
            f"{api_url}/qc-runs/{run['id']}/multiqc-report",
            timeout=5,
        ) as response:
            assert response.headers.get_content_type() == "text/html"
            assert response.read() == REPORT_CONTENT

    invocation = json.loads(invocation_path.read_text(encoding="utf-8"))
    assert invocation == [
        "run",
        "pipelines/qc/main.nf",
        "-profile",
        "docker",
        "--input",
        str(samplesheet),
        "--outdir",
        str(run_dir),
    ]

    stored_reports = list((tmp_path / "artifacts" / "qc-runs").rglob("*.html"))
    assert len(stored_reports) == 1
    assert stored_reports[0].read_bytes() == REPORT_CONTENT


def test_cli_start_does_not_register_run_when_nextflow_fails(tmp_path: Path) -> None:
    samplesheet = _write_samplesheet(tmp_path)
    run_dir = tmp_path / "failed-results"
    fake_bin = _write_fake_nextflow(tmp_path, exit_code=17)

    with _running_api(tmp_path) as api_url:
        completed = _run_cli_start(
            api_url=api_url,
            samplesheet=samplesheet,
            run_dir=run_dir,
            fake_bin=fake_bin,
        )

        assert completed.returncode == 1
        assert "Nextflow QC workflow failed (exit code 17)" in completed.stderr
        assert _get_json(f"{api_url}/qc-runs") == []

    artifact_root = tmp_path / "artifacts"
    assert not artifact_root.exists() or not any(artifact_root.rglob("*.html"))


def _write_samplesheet(tmp_path: Path) -> Path:
    samplesheet = tmp_path / "samplesheet.csv"
    samplesheet.write_text(
        "sample,fastq\n"
        "sample_01,data/sample_01.fastq\n"
        "sample_02,data/sample_02.fastq\n",
        encoding="utf-8",
    )
    return samplesheet


def _write_fake_nextflow(
    tmp_path: Path,
    *,
    exit_code: int,
) -> Path:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    executable = fake_bin / "nextflow"
    executable.write_text(
        "#!/usr/bin/env python3\n"
        "import json\n"
        "import os\n"
        "import sys\n"
        "from pathlib import Path\n"
        "\n"
        "args = sys.argv[1:]\n"
        "invocation_path = os.environ.get('FAKE_NEXTFLOW_INVOCATION')\n"
        "if invocation_path:\n"
        "    Path(invocation_path).write_text(json.dumps(args), encoding='utf-8')\n"
        f"if {exit_code}:\n"
        f"    raise SystemExit({exit_code})\n"
        "outdir = Path(args[args.index('--outdir') + 1])\n"
        "report = outdir / 'multiqc' / 'multiqc_report.html'\n"
        "report.parent.mkdir(parents=True, exist_ok=True)\n"
        f"report.write_bytes({REPORT_CONTENT!r})\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    return fake_bin


def _run_cli_start(
    *,
    api_url: str,
    samplesheet: Path,
    run_dir: Path,
    fake_bin: Path,
    invocation_path: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"
    if invocation_path is not None:
        env["FAKE_NEXTFLOW_INVOCATION"] = str(invocation_path)
    answers = f"{samplesheet}\n{run_dir}\n{api_url}\ne2e-run\n"
    return subprocess.run(
        [sys.executable, "-m", "cli", "start"],
        cwd=PROJECT_ROOT,
        env=env,
        input=answers,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


@contextmanager
def _running_api(tmp_path: Path) -> Iterator[str]:
    port = _unused_loopback_port()
    api_url = f"http://127.0.0.1:{port}"
    log_path = tmp_path / "uvicorn.log"
    env = os.environ.copy()
    env.update(
        {
            "DATABASE_URL": f"sqlite:///{tmp_path / 'e2e.db'}",
            "AUTO_CREATE_TABLES": "true",
            "ARTIFACT_ROOT": str(tmp_path / "artifacts"),
        }
    )

    with log_path.open("w", encoding="utf-8") as log_handle:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=PROJECT_ROOT,
            env=env,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            _wait_until_healthy(api_url, process, log_path)
            yield api_url
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def _unused_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_until_healthy(
    api_url: str,
    process: subprocess.Popen[str],
    log_path: Path,
) -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process.poll() is not None:
            break
        try:
            if _get_json(f"{api_url}/health") == {"status": "ok"}:
                return
        except (URLError, TimeoutError):
            time.sleep(0.05)

    process.terminate()
    process.wait(timeout=5)
    pytest.fail(f"API did not become healthy:\n{log_path.read_text(encoding='utf-8')}")


def _get_json(url: str) -> object:
    with urlopen(url, timeout=1) as response:  # noqa: S310 - controlled loopback URL
        return json.loads(response.read().decode("utf-8"))
