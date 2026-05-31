# PYTHON_ARGCOMPLETE_OK
from __future__ import annotations

import argparse
import csv
import glob
import importlib
import json
import os
import subprocess
import sys
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

REQUIRED_SAMPLESHEET_COLUMNS = ("sample", "fastq")
MULTIQC_REPORT_NAME = "multiqc_report.html"

DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_SAMPLESHEET = "pipelines/qc/samplesheet.csv"
DEFAULT_RUN_DIR = "results/qc"
QC_PIPELINE = "pipelines/qc/main.nf"
NEXTFLOW_PROFILE = "docker"
WORKFLOW_NAME = "fastqc-multiqc"
WORKFLOW_VERSION = "0.1.0"
SUCCESS_MARK = "✓"
ABORT_EXIT_CODE = 130  # 128 + SIGINT, the conventional exit code for Ctrl+C


class CliError(Exception):
    """Expected CLI failure with a human-readable message."""


@dataclass(frozen=True)
class SamplesheetValidationResult:
    path: Path
    sample_count: int
    columns: tuple[str, ...]


def validate_samplesheet(path: Path) -> SamplesheetValidationResult:
    if not path.exists():
        raise CliError(f"Samplesheet not found: {path}")
    if not path.is_file():
        raise CliError(f"Samplesheet path is not a file: {path}")

    errors: list[str] = []
    sample_ids: set[str] = set()
    sample_count = 0

    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, strict=True)
            fieldnames = tuple(reader.fieldnames or ())

            if not fieldnames:
                raise CliError(f"Samplesheet has no CSV header: {path}")

            missing_columns = [
                column
                for column in REQUIRED_SAMPLESHEET_COLUMNS
                if column not in fieldnames
            ]
            if missing_columns:
                missing = ", ".join(missing_columns)
                required = ", ".join(REQUIRED_SAMPLESHEET_COLUMNS)
                raise CliError(
                    f"Samplesheet is missing required column(s): {missing}. "
                    f"Required columns: {required}."
                )

            for line_number, row in enumerate(reader, start=2):
                if None in row:
                    errors.append(
                        f"line {line_number}: row has more values than CSV columns"
                    )
                    continue

                sample = (row.get("sample") or "").strip()
                fastq = (row.get("fastq") or "").strip()
                sample_count += 1

                if not sample:
                    errors.append(f"line {line_number}: sample is empty")
                elif sample in sample_ids:
                    errors.append(f"line {line_number}: duplicate sample '{sample}'")
                else:
                    sample_ids.add(sample)

                if not fastq:
                    errors.append(f"line {line_number}: fastq path is empty")

    except csv.Error as exc:
        raise CliError(f"Samplesheet is not valid CSV: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise CliError(f"Samplesheet is not valid UTF-8 text: {path}") from exc
    except OSError as exc:
        raise CliError(f"Could not read samplesheet {path}: {exc}") from exc

    if sample_count == 0:
        errors.append("samplesheet has no sample rows")

    if errors:
        joined = "\n- ".join(errors)
        raise CliError(f"Samplesheet validation failed:\n- {joined}")

    return SamplesheetValidationResult(
        path=path,
        sample_count=sample_count,
        columns=fieldnames,
    )


def find_multiqc_report(run_dir: Path) -> Path:
    if not run_dir.exists():
        raise CliError(f"Run directory not found: {run_dir}")
    if not run_dir.is_dir():
        raise CliError(f"Run directory path is not a directory: {run_dir}")

    candidates = sorted(
        path for path in run_dir.rglob(MULTIQC_REPORT_NAME) if path.is_file()
    )

    if not candidates:
        raise CliError(f"No {MULTIQC_REPORT_NAME} found under run directory: {run_dir}")

    if len(candidates) > 1:
        listed = "\n- ".join(str(candidate) for candidate in candidates)
        raise CliError(
            f"Multiple {MULTIQC_REPORT_NAME} files found. "
            f"Please use a run directory with exactly one report:\n- {listed}"
        )

    return candidates[0]


def register_local_run(
    *,
    api_url: str,
    run_dir: Path,
    samplesheet: Path,
    run_name: str | None,
    started_at: str | None,
    completed_at: str | None,
    workflow_name: str,
    workflow_version: str,
) -> dict[str, Any]:
    validate_samplesheet(samplesheet)
    multiqc_report = find_multiqc_report(run_dir)
    timestamp = current_utc_timestamp()

    payload = {
        "run_name": run_name or default_run_name(run_dir),
        "workflow_name": workflow_name,
        "workflow_engine": "nextflow",
        "workflow_version": workflow_version,
        "status": "COMPLETED",
        "output_path": str(run_dir),
        "multiqc_report_path": str(multiqc_report),
        "samplesheet_path": str(samplesheet),
        "started_at": started_at or timestamp,
        "completed_at": completed_at or timestamp,
    }

    endpoint = f"{api_url.rstrip('/')}/qc-runs/register-local"
    return post_json(endpoint, payload)


def register_local_run_upload(
    *,
    api_url: str,
    run_dir: Path,
    samplesheet: Path,
    multiqc_report: Path,
    run_name: str | None,
    workflow_name: str,
    workflow_version: str,
    sample_count: int | None = None,
    started_at: str | None = None,
    completed_at: str | None = None,
) -> dict[str, Any]:
    if not multiqc_report.exists():
        raise CliError(f"MultiQC report not found: {multiqc_report}")
    if not multiqc_report.is_file():
        raise CliError(f"MultiQC report path is not a file: {multiqc_report}")
    try:
        if multiqc_report.stat().st_size == 0:
            raise CliError(f"MultiQC report is empty: {multiqc_report}")
    except OSError as exc:
        raise CliError(
            f"Could not inspect MultiQC report {multiqc_report}: {exc}"
        ) from exc

    fields = {
        "run_name": run_name or default_run_name(run_dir),
        "samplesheet_path": str(samplesheet),
        "run_dir": str(run_dir),
        "pipeline_name": workflow_name,
        "pipeline_version": workflow_version,
    }
    if sample_count is not None:
        fields["sample_count"] = str(sample_count)
    if started_at is not None:
        fields["started_at"] = started_at
    if completed_at is not None:
        fields["completed_at"] = completed_at

    endpoint = f"{api_url.rstrip('/')}/qc-runs/register-local-upload"
    return post_multipart(
        endpoint,
        fields=fields,
        file_field_name="multiqc_report",
        file_path=multiqc_report,
    )


def post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
            status = response.status
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise CliError(
            f"Backend returned HTTP {exc.code} for {url}:\n{format_response_body(body)}"
        ) from exc
    except URLError as exc:
        raise CliError(f"Could not connect to backend at {url}: {exc.reason}") from exc

    if status < 200 or status >= 300:
        raise CliError(
            f"Backend returned HTTP {status} for {url}:\n{format_response_body(body)}"
        )

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise CliError(f"Backend response was not valid JSON:\n{body}") from exc

    if not isinstance(parsed, dict):
        raise CliError(f"Backend response was JSON, but not an object:\n{body}")

    return parsed


def post_multipart(
    url: str,
    *,
    fields: dict[str, str],
    file_field_name: str,
    file_path: Path,
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    try:
        body, content_type = encode_multipart_form_data(
            fields=fields,
            file_field_name=file_field_name,
            file_path=file_path,
        )
    except OSError as exc:
        raise CliError(f"Could not read file for upload {file_path}: {exc}") from exc

    request = Request(
        url,
        data=body,
        headers={
            "Content-Type": content_type,
            "Content-Length": str(len(body)),
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with opener(request, timeout=30) as response:
            response_body = response.read().decode("utf-8")
            status = response.status
    except HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        raise CliError(
            f"Backend returned HTTP {exc.code} for {url}:\n"
            f"{format_response_body(response_body)}"
        ) from exc
    except URLError as exc:
        raise CliError(f"Could not connect to backend at {url}: {exc.reason}") from exc

    if status < 200 or status >= 300:
        raise CliError(
            f"Backend returned HTTP {status} for {url}:\n"
            f"{format_response_body(response_body)}"
        )

    try:
        parsed = json.loads(response_body)
    except json.JSONDecodeError as exc:
        raise CliError(
            f"Backend response was not valid JSON:\n{response_body}"
        ) from exc

    if not isinstance(parsed, dict):
        raise CliError(
            f"Backend response was JSON, but not an object:\n{response_body}"
        )

    return parsed


def encode_multipart_form_data(
    *,
    fields: dict[str, str],
    file_field_name: str,
    file_path: Path,
) -> tuple[bytes, str]:
    boundary = f"----bioflowops-{uuid4().hex}"
    body = bytearray()

    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(
            (
                "Content-Disposition: form-data; "
                f'name="{escape_multipart_header(name)}"'
                "\r\n\r\n"
            ).encode()
        )
        body.extend(str(value).encode("utf-8"))
        body.extend(b"\r\n")

    body.extend(f"--{boundary}\r\n".encode())
    body.extend(
        (
            "Content-Disposition: form-data; "
            f'name="{escape_multipart_header(file_field_name)}"; '
            f'filename="{escape_multipart_header(file_path.name)}"\r\n'
            "Content-Type: text/html\r\n\r\n"
        ).encode()
    )
    body.extend(file_path.read_bytes())
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode())

    return bytes(body), f"multipart/form-data; boundary={boundary}"


def escape_multipart_header(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def current_utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_run_name(run_dir: Path) -> str:
    name = run_dir.resolve().name
    return name or "local-qc-run"


def format_response_body(body: str) -> str:
    try:
        return json.dumps(json.loads(body), indent=2, sort_keys=True)
    except json.JSONDecodeError:
        return body


@dataclass(frozen=True)
class StartInputs:
    samplesheet: Path
    run_dir: Path
    api_url: str
    run_name: str


def prompt_with_default(
    label: str,
    default: str,
    *,
    input_fn: Callable[[str], str] = input,
) -> str:
    response = input_fn(f"{label} [{default}]: ").strip()
    return response or default


class _PathCompleter:
    """readline completer that suggests filesystem paths for the current token."""

    def __init__(self) -> None:
        self._matches: list[str] = []

    def complete(self, text: str, state: int) -> str | None:
        if state == 0:
            self._matches = _glob_path_matches(text)
        if 0 <= state < len(self._matches):
            return self._matches[state]
        return None


def _glob_path_matches(text: str) -> list[str]:
    expanded = os.path.expanduser(text)
    matches = [
        match + os.sep if os.path.isdir(match) else match
        for match in glob.glob(expanded + "*")
    ]
    return sorted(matches)


@contextmanager
def path_completion() -> Iterator[None]:
    """Enable readline Tab completion of filesystem paths within the block.

    Falls back to a no-op when readline is unavailable (for example on stock
    Windows Python), so the interactive prompts never crash.
    """
    try:
        readline = importlib.import_module("readline")
    except ImportError:
        yield
        return

    completer = _PathCompleter()
    previous_completer = readline.get_completer()
    previous_delims = readline.get_completer_delims()
    readline.set_completer(completer.complete)
    readline.set_completer_delims(" \t\n")
    readline.parse_and_bind("tab: complete")
    try:
        yield
    finally:
        readline.set_completer(previous_completer)
        readline.set_completer_delims(previous_delims)


def collect_start_inputs(*, input_fn: Callable[[str], str] = input) -> StartInputs:
    with path_completion():
        samplesheet = Path(
            prompt_with_default(
                "Samplesheet path (use pipelines/qc/samplesheet.demo.csv "
                "if you generated demo data)",
                DEFAULT_SAMPLESHEET,
                input_fn=input_fn,
            )
        )
        run_dir = Path(
            prompt_with_default("Output directory", DEFAULT_RUN_DIR, input_fn=input_fn)
        )
    api_url = prompt_with_default("API URL", DEFAULT_API_URL, input_fn=input_fn)
    run_name = prompt_with_default(
        "Run name", default_run_name(run_dir), input_fn=input_fn
    )
    return StartInputs(
        samplesheet=samplesheet,
        run_dir=run_dir,
        api_url=api_url,
        run_name=run_name,
    )


def run_nextflow_qc(
    *,
    samplesheet: Path,
    run_dir: Path,
    pipeline: str = QC_PIPELINE,
    profile: str = NEXTFLOW_PROFILE,
    executable: str = "nextflow",
    runner: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
) -> None:
    command = [
        executable,
        "run",
        pipeline,
        "-profile",
        profile,
        "--input",
        str(samplesheet),
        "--outdir",
        str(run_dir),
    ]
    try:
        completed = runner(command)
    except FileNotFoundError as exc:
        raise CliError(
            f"Could not find the '{executable}' executable. "
            "Install Nextflow and ensure it is on your PATH."
        ) from exc

    if completed.returncode != 0:
        raise CliError(
            f"Nextflow QC workflow failed (exit code {completed.returncode}). "
            "See the Nextflow output above for details."
        )


def format_duration(seconds: float) -> str:
    total = int(round(seconds))
    minutes, secs = divmod(total, 60)
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def build_report_url(api_url: str, run_id: str) -> str:
    return f"{api_url.rstrip('/')}/qc-runs/{run_id}/multiqc-report"


def print_run_summary(
    response: dict[str, Any],
    *,
    api_url: str | None = None,
    output_fn: Callable[[str], None] = print,
) -> None:
    summary_fields = (
        ("Run ID", "id"),
        ("Run name", "run_name"),
        ("Status", "status"),
        ("Samples", "sample_count"),
        ("MultiQC report", "multiqc_report_path"),
    )
    for label, key in summary_fields:
        value = response.get(key)
        if value is not None:
            output_fn(f"  {label}: {value}")

    duration = response.get("duration_seconds")
    if duration is not None:
        output_fn(f"  Duration: {format_duration(duration)}")

    run_id = response.get("id")
    if api_url and run_id:
        output_fn(f"  Report URL: {build_report_url(api_url, run_id)}")


def bioqc_help_text() -> str:
    return """BioQC local CLI

Preferred command:
  bioqc start

Manual commands:
  bioqc validate pipelines/qc/samplesheet.csv
  bioqc register-local \\
    --run-dir results/qc \\
    --samplesheet pipelines/qc/samplesheet.csv \\
    --api-url http://localhost:8000

Module form:
  python -m cli start
  python -m cli validate pipelines/qc/samplesheet.csv
  python -m cli register-local \\
    --run-dir results/qc \\
    --samplesheet pipelines/qc/samplesheet.csv \\
    --api-url http://localhost:8000

Local flow:
  samplesheet.csv -> CLI -> Nextflow/MultiQC -> FastAPI /qc-runs/register-local-upload

Before registration:
  1. Start the API with: uv run uvicorn app.main:app --reload
  2. Make sure the run directory contains exactly one multiqc_report.html
"""


def print_bioqc_help(*, output_fn: Callable[[str], None] = print) -> None:
    output_fn(bioqc_help_text())


def enable_unicode_output() -> None:
    """Best-effort UTF-8 output so status marks render on Windows consoles."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8")
        except (ValueError, OSError):
            pass


def start_workflow(
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> int:
    enable_unicode_output()
    output_fn("BioQC Portal CLI")
    output_fn("")

    output_fn("Press Ctrl+C to cancel.")
    output_fn("")

    output_fn("Leave input empty to use a default value.")
    output_fn("")

    inputs = collect_start_inputs(input_fn=input_fn)
    output_fn("")

    validation = validate_samplesheet(inputs.samplesheet)
    output_fn(f"{SUCCESS_MARK} Samplesheet valid")

    output_fn(f"{SUCCESS_MARK} Starting Nextflow QC workflow")
    started_at = current_utc_timestamp()
    run_nextflow_qc(samplesheet=inputs.samplesheet, run_dir=inputs.run_dir)
    completed_at = current_utc_timestamp()
    output_fn(f"{SUCCESS_MARK} Nextflow completed")

    report = find_multiqc_report(inputs.run_dir)
    output_fn(f"{SUCCESS_MARK} Found MultiQC report: {report}")

    response = register_local_run_upload(
        api_url=inputs.api_url,
        run_dir=inputs.run_dir,
        samplesheet=inputs.samplesheet,
        multiqc_report=report,
        run_name=inputs.run_name,
        workflow_name=WORKFLOW_NAME,
        workflow_version=WORKFLOW_VERSION,
        sample_count=validation.sample_count,
        started_at=started_at,
        completed_at=completed_at,
    )
    output_fn(f"{SUCCESS_MARK} Uploaded MultiQC report to BioQC Portal")
    output_fn("")
    output_fn("Run registered successfully.")
    print_run_summary(response, api_url=inputs.api_url, output_fn=output_fn)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cli",
        description="Local BioFlowOps QC workflow helpers.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "start",
        help="Interactively run the local QC workflow and register the run.",
    )

    subparsers.add_parser(
        "help",
        help="Show the BioQC quick-start help.",
    )

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate a local QC samplesheet CSV.",
    )
    validate_parser.add_argument("samplesheet", type=Path)

    register_parser = subparsers.add_parser(
        "register-local",
        help="Register a completed local QC workflow run with the FastAPI backend.",
    )
    register_parser.add_argument("--run-dir", type=Path, required=True)
    register_parser.add_argument("--samplesheet", type=Path, required=True)
    register_parser.add_argument("--api-url", default=DEFAULT_API_URL)
    register_parser.add_argument(
        "--run-name",
        help="Run name to store in the backend. Defaults to the run directory name.",
    )
    register_parser.add_argument(
        "--started-at",
        help="ISO timestamp for the run start. Defaults to the current UTC time.",
    )
    register_parser.add_argument(
        "--completed-at",
        help="ISO timestamp for completion. Defaults to the current UTC time.",
    )
    register_parser.add_argument("--workflow-name", default=WORKFLOW_NAME)
    register_parser.add_argument("--workflow-version", default=WORKFLOW_VERSION)

    return parser


def enable_argcomplete(parser: argparse.ArgumentParser) -> None:
    """Enable shell tab-completion when argcomplete is installed; no-op otherwise.

    This only does work when invoked by the shell completion mechanism (which
    sets ``_ARGCOMPLETE``), so it is safe and silent during normal execution.
    """
    try:
        import argcomplete
    except ImportError:
        return
    argcomplete.autocomplete(parser)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    enable_argcomplete(parser)
    args = parser.parse_args(argv)

    try:
        if args.command == "start":
            return start_workflow()

        if args.command == "help":
            print_bioqc_help()
            return 0

        if args.command == "validate":
            result = validate_samplesheet(args.samplesheet)
            columns = ", ".join(result.columns)
            print(
                f"Samplesheet OK: {result.path} "
                f"({result.sample_count} samples; columns: {columns})"
            )
            return 0

        if args.command == "register-local":
            validation = validate_samplesheet(args.samplesheet)
            multiqc_report = find_multiqc_report(args.run_dir)
            print(
                f"Samplesheet OK: {validation.path} ({validation.sample_count} samples)"
            )
            print(f"MultiQC report found: {multiqc_report}")

            response = register_local_run(
                api_url=args.api_url,
                run_dir=args.run_dir,
                samplesheet=args.samplesheet,
                run_name=args.run_name,
                started_at=args.started_at,
                completed_at=args.completed_at,
                workflow_name=args.workflow_name,
                workflow_version=args.workflow_version,
            )
            print("Registered local QC run:")
            print(json.dumps(response, indent=2, sort_keys=True))
            return 0

    except CliError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nAborted.", file=sys.stderr)
        return ABORT_EXIT_CODE

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
