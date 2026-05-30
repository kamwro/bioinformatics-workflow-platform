import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from cli import cli
from cli.cli import CliError, find_multiqc_report, main, validate_samplesheet


def test_validate_samplesheet_accepts_project_columns(tmp_path: Path) -> None:
    samplesheet = tmp_path / "samplesheet.csv"
    samplesheet.write_text(
        "sample,fastq\n"
        "sample_01,data/sample_01.fastq\n"
        "sample_02,data/sample_02.fastq\n",
        encoding="utf-8",
    )

    result = validate_samplesheet(samplesheet)

    assert result.sample_count == 2
    assert result.columns == ("sample", "fastq")


def test_validate_samplesheet_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(CliError, match="Samplesheet not found"):
        validate_samplesheet(tmp_path / "missing.csv")


def test_validate_command_returns_nonzero_for_missing_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["validate", str(tmp_path / "missing.csv")])

    assert exit_code == 1
    assert "Samplesheet not found" in capsys.readouterr().err


def test_help_command_prints_bioqc_quick_start(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["help"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "BioQC local CLI" in captured.out
    assert "bioqc start" in captured.out
    assert "bioqc register-local" in captured.out


def test_validate_samplesheet_rejects_missing_required_column(
    tmp_path: Path,
) -> None:
    samplesheet = tmp_path / "samplesheet.csv"
    samplesheet.write_text(
        "sample,path\nsample_01,data/sample_01.fastq\n",
        encoding="utf-8",
    )

    with pytest.raises(CliError, match="missing required column"):
        validate_samplesheet(samplesheet)


def test_validate_samplesheet_rejects_duplicate_sample_ids(
    tmp_path: Path,
) -> None:
    samplesheet = tmp_path / "samplesheet.csv"
    samplesheet.write_text(
        "sample,fastq\n"
        "sample_01,data/sample_01.fastq\n"
        "sample_01,data/sample_01_repeat.fastq\n",
        encoding="utf-8",
    )

    with pytest.raises(CliError, match="duplicate sample 'sample_01'"):
        validate_samplesheet(samplesheet)


def test_find_multiqc_report_rejects_missing_report(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    with pytest.raises(CliError, match="No multiqc_report.html found"):
        find_multiqc_report(run_dir)


def test_find_multiqc_report_rejects_multiple_reports(tmp_path: Path) -> None:
    first = tmp_path / "run" / "multiqc"
    second = tmp_path / "run" / "nested" / "multiqc"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    (first / "multiqc_report.html").write_text("<html></html>", encoding="utf-8")
    (second / "multiqc_report.html").write_text("<html></html>", encoding="utf-8")

    with pytest.raises(CliError, match="Multiple multiqc_report.html files found"):
        find_multiqc_report(tmp_path / "run")


def test_collect_start_inputs_uses_defaults_when_blank() -> None:
    answers = iter(["", "", "", ""])
    inputs = cli.collect_start_inputs(input_fn=lambda _prompt: next(answers))

    assert inputs.samplesheet == Path("pipelines/qc/samplesheet.csv")
    assert inputs.run_dir == Path("results/qc")
    assert inputs.api_url == "http://localhost:8000"
    assert inputs.run_name == "qc"


def test_collect_start_inputs_uses_provided_values() -> None:
    answers = iter(["my/samplesheet.csv", "out/run", "http://host:9000", "demo-run"])
    inputs = cli.collect_start_inputs(input_fn=lambda _prompt: next(answers))

    assert inputs.samplesheet == Path("my/samplesheet.csv")
    assert inputs.run_dir == Path("out/run")
    assert inputs.api_url == "http://host:9000"
    assert inputs.run_name == "demo-run"


def test_run_nextflow_qc_builds_expected_command() -> None:
    captured: dict[str, list[str]] = {}

    def fake_runner(command: list[str]) -> SimpleNamespace:
        captured["command"] = command
        return SimpleNamespace(returncode=0)

    cli.run_nextflow_qc(
        samplesheet=Path("sheet.csv"),
        run_dir=Path("out"),
        runner=fake_runner,
    )

    assert captured["command"] == [
        "nextflow",
        "run",
        "pipelines/qc/main.nf",
        "-profile",
        "docker",
        "--input",
        "sheet.csv",
        "--outdir",
        "out",
    ]


def test_run_nextflow_qc_raises_on_nonzero_exit() -> None:
    def fake_runner(command: list[str]) -> SimpleNamespace:
        return SimpleNamespace(returncode=2)

    with pytest.raises(CliError, match="Nextflow QC workflow failed"):
        cli.run_nextflow_qc(
            samplesheet=Path("sheet.csv"),
            run_dir=Path("out"),
            runner=fake_runner,
        )


def test_run_nextflow_qc_raises_when_executable_missing() -> None:
    def fake_runner(command: list[str]) -> SimpleNamespace:
        raise FileNotFoundError("nextflow")

    with pytest.raises(CliError, match="Could not find the 'nextflow' executable"):
        cli.run_nextflow_qc(
            samplesheet=Path("sheet.csv"),
            run_dir=Path("out"),
            runner=fake_runner,
        )


def test_post_multipart_sends_expected_request(tmp_path: Path) -> None:
    report = tmp_path / "multiqc_report.html"
    report.write_text("<html>report</html>", encoding="utf-8")
    captured: dict[str, Any] = {}

    class FakeResponse:
        status = 201

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"id": "run-123", "status": "COMPLETED"}'

    def fake_opener(request: Any, timeout: int) -> FakeResponse:
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse()

    response = cli.post_multipart(
        "http://host:9000/qc-runs/register-local-upload",
        fields={
            "run_name": "demo-run",
            "samplesheet_path": "pipelines/qc/samplesheet.csv",
            "run_dir": "results/qc",
        },
        file_field_name="multiqc_report",
        file_path=report,
        opener=fake_opener,
    )

    request = captured["request"]
    body = request.data
    content_type = request.get_header("Content-type") or request.get_header(
        "Content-Type"
    )
    assert response == {"id": "run-123", "status": "COMPLETED"}
    assert captured["timeout"] == 30
    assert request.full_url == "http://host:9000/qc-runs/register-local-upload"
    assert request.get_method() == "POST"
    assert content_type.startswith("multipart/form-data; boundary=")
    assert b'name="run_name"\r\n\r\ndemo-run' in body
    assert b'name="samplesheet_path"\r\n\r\npipelines/qc/samplesheet.csv' in body
    assert b'name="multiqc_report"; filename="multiqc_report.html"' in body
    assert b"Content-Type: text/html" in body
    assert b"<html>report</html>" in body


def test_register_local_run_upload_posts_expected_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = tmp_path / "multiqc_report.html"
    report.write_text("<html>report</html>", encoding="utf-8")
    calls: dict[str, Any] = {}

    def fake_post_multipart(url: str, **kwargs: Any) -> dict[str, Any]:
        calls["multipart"] = {"url": url, **kwargs}
        return {"id": "run-123", "status": "COMPLETED"}

    monkeypatch.setattr(cli, "post_multipart", fake_post_multipart)

    response = cli.register_local_run_upload(
        api_url="http://host:9000/",
        run_dir=Path("results/qc"),
        samplesheet=Path("pipelines/qc/samplesheet.csv"),
        multiqc_report=report,
        run_name="demo-run",
        workflow_name="fastqc-multiqc",
        workflow_version="0.1.0",
        sample_count=2,
    )

    assert response == {"id": "run-123", "status": "COMPLETED"}
    assert calls["multipart"]["url"] == (
        "http://host:9000/qc-runs/register-local-upload"
    )
    assert calls["multipart"]["fields"] == {
        "run_name": "demo-run",
        "samplesheet_path": "pipelines/qc/samplesheet.csv",
        "run_dir": "results/qc",
        "pipeline_name": "fastqc-multiqc",
        "pipeline_version": "0.1.0",
        "sample_count": "2",
    }
    assert calls["multipart"]["file_field_name"] == "multiqc_report"
    assert calls["multipart"]["file_path"] == report


def test_register_local_run_upload_rejects_empty_report(tmp_path: Path) -> None:
    report = tmp_path / "multiqc_report.html"
    report.write_bytes(b"")

    with pytest.raises(CliError, match="MultiQC report is empty"):
        cli.register_local_run_upload(
            api_url="http://host:9000/",
            run_dir=Path("results/qc"),
            samplesheet=Path("pipelines/qc/samplesheet.csv"),
            multiqc_report=report,
            run_name="demo-run",
            workflow_name="fastqc-multiqc",
            workflow_version="0.1.0",
        )


def test_register_local_run_includes_samplesheet_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    samplesheet = tmp_path / "samplesheet.csv"
    samplesheet.write_text(
        "sample,fastq\nsample_01,data/sample_01.fastq\n",
        encoding="utf-8",
    )
    run_dir = tmp_path / "results"
    report_dir = run_dir / "multiqc"
    report_dir.mkdir(parents=True)
    (report_dir / "multiqc_report.html").write_text("<html></html>", encoding="utf-8")

    captured: dict[str, Any] = {}

    def fake_post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
        captured["url"] = url
        captured["payload"] = payload
        return {"id": "run-1"}

    monkeypatch.setattr(cli, "post_json", fake_post_json)

    cli.register_local_run(
        api_url="http://host:9000",
        run_dir=run_dir,
        samplesheet=samplesheet,
        run_name="local-qc",
        started_at=None,
        completed_at=None,
        workflow_name="fastqc-multiqc",
        workflow_version="0.1.0",
    )

    assert captured["url"].endswith("/qc-runs/register-local")
    assert captured["payload"]["samplesheet_path"] == str(samplesheet)


def test_start_workflow_runs_end_to_end(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    samplesheet = tmp_path / "samplesheet.csv"
    samplesheet.write_text(
        "sample,fastq\nsample_01,data/sample_01.fastq\n",
        encoding="utf-8",
    )
    run_dir = tmp_path / "results"
    report_dir = run_dir / "multiqc"
    report_dir.mkdir(parents=True)
    (report_dir / "multiqc_report.html").write_text("<html></html>", encoding="utf-8")

    calls: dict[str, Any] = {}

    def fake_run_nextflow_qc(*, samplesheet: Path, run_dir: Path) -> None:
        calls["nextflow"] = {"samplesheet": samplesheet, "run_dir": run_dir}

    def fake_register_local_run_upload(**kwargs: Any) -> dict[str, Any]:
        calls["register"] = kwargs
        return {
            "id": "run-123",
            "run_name": kwargs["run_name"],
            "status": "COMPLETED",
            "multiqc_report_path": "artifacts/qc-runs/run-123/multiqc_report.html",
        }

    monkeypatch.setattr(cli, "run_nextflow_qc", fake_run_nextflow_qc)
    monkeypatch.setattr(
        cli,
        "register_local_run_upload",
        fake_register_local_run_upload,
    )

    answers = iter([str(samplesheet), str(run_dir), "http://host:9000", "demo-run"])
    outputs: list[str] = []
    exit_code = cli.start_workflow(
        input_fn=lambda _prompt: next(answers),
        output_fn=outputs.append,
    )

    assert exit_code == 0
    assert calls["nextflow"] == {"samplesheet": samplesheet, "run_dir": run_dir}
    assert calls["register"]["api_url"] == "http://host:9000"
    assert calls["register"]["run_name"] == "demo-run"
    assert calls["register"]["run_dir"] == run_dir
    assert calls["register"]["samplesheet"] == samplesheet
    assert calls["register"]["multiqc_report"] == report_dir / "multiqc_report.html"
    assert calls["register"]["sample_count"] == 1

    printed = "\n".join(outputs)
    assert "Samplesheet valid" in printed
    assert "Nextflow completed" in printed
    assert "Found MultiQC report" in printed
    assert "Uploaded MultiQC report to BioQC Portal" in printed
    assert "Run registered successfully." in printed
    assert "run-123" in printed


def test_main_start_dispatches_to_start_workflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, bool] = {}

    def fake_start_workflow() -> int:
        calls["ran"] = True
        return 0

    monkeypatch.setattr(cli, "start_workflow", fake_start_workflow)

    assert main(["start"]) == 0
    assert calls["ran"] is True


def test_main_aborts_cleanly_on_keyboard_interrupt(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def interrupt() -> int:
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "start_workflow", interrupt)

    exit_code = main(["start"])

    assert exit_code == 130
    assert "Aborted" in capsys.readouterr().err


def test_main_aborts_cleanly_on_eof(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def end_of_input() -> int:
        raise EOFError

    monkeypatch.setattr(cli, "start_workflow", end_of_input)

    exit_code = main(["start"])

    assert exit_code == 130
    assert "Aborted" in capsys.readouterr().err


def test_enable_argcomplete_is_noop_without_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "argcomplete", None)
    parser = cli.build_parser()

    # Must not raise even though argcomplete cannot be imported.
    cli.enable_argcomplete(parser)


def test_main_executes_with_argcomplete_hook(tmp_path: Path) -> None:
    samplesheet = tmp_path / "samplesheet.csv"
    samplesheet.write_text(
        "sample,fastq\nsample_01,data/sample_01.fastq\n",
        encoding="utf-8",
    )

    # main() runs enable_argcomplete(); normal execution must be unaffected.
    assert main(["validate", str(samplesheet)]) == 0


def test_path_completion_is_noop_without_readline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "readline", None)

    with cli.path_completion():
        pass  # must not raise when readline is unavailable


def test_collect_start_inputs_without_readline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "readline", None)
    answers = iter(["data/sheet.csv", "out/run", "http://host:8000", "demo"])

    inputs = cli.collect_start_inputs(input_fn=lambda _prompt: next(answers))

    assert inputs.samplesheet == Path("data/sheet.csv")
    assert inputs.run_dir == Path("out/run")
    assert inputs.api_url == "http://host:8000"
    assert inputs.run_name == "demo"


def test_glob_path_matches_lists_files_and_dirs(tmp_path: Path) -> None:
    (tmp_path / "alpha.csv").write_text("x", encoding="utf-8")
    (tmp_path / "alps").mkdir()

    matches = cli._glob_path_matches(str(tmp_path / "al"))

    assert str(tmp_path / "alpha.csv") in matches
    assert str(tmp_path / "alps") + os.sep in matches


def test_path_completer_returns_matches_then_none(tmp_path: Path) -> None:
    (tmp_path / "alpha.csv").write_text("x", encoding="utf-8")
    completer = cli._PathCompleter()
    prefix = str(tmp_path / "alph")

    assert completer.complete(prefix, 0) == str(tmp_path / "alpha.csv")
    assert completer.complete(prefix, 1) is None
