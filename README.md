# BioFlowOps

BioFlowOps is a small, local **bioinformatics QC workflow platform**. It
generates synthetic demo FASTQ data, runs a local Nextflow/MultiQC quality-control
pipeline, then uploads the generated MultiQC report to a FastAPI backend that
stores the run's metadata and the report artifact.

The whole path runs on one machine and is driven by a single command
(`bioqc start`). It is a portfolio MVP, not a clinical tool and not
production-grade bioinformatics software. The goal is an honest, end-to-end slice
that is easy to explain and easy to run.

## What this demonstrates

- A **Python CLI** that drives a real multi-step workflow end to end.
- A **FastAPI** service for QC run metadata, with typed Pydantic schemas and
  PostgreSQL persistence via SQLAlchemy + Alembic.
- **Local artifact upload and storage**: the MultiQC HTML report is uploaded over
  multipart and stored server-side, with its path recorded in the database.
- **Nextflow/MultiQC workflow awareness**: a minimal DSL2 pipeline
  (FASTQ → FastQC → MultiQC) using nf-core-inspired conventions (not full nf-core
  compliance).
- **Clear, testable MVP boundaries** between the API, the CLI, and the workflow
  engine.
- **Scientific-computing-style provenance**: each run records its samplesheet,
  run directory, pipeline name/version, sample count, and the stored report.

## End-to-end flow

```text
generate demo FASTQ
  → validate samplesheet
  → run local Nextflow QC pipeline
  → produce MultiQC report
  → upload/register report via FastAPI
  → store metadata and report artifact
```

The **CLI owns the workflow**: it validates the samplesheet, runs Nextflow,
locates the MultiQC report, and uploads it. The **API owns persistence**: it
accepts the uploaded report, stores it under `artifacts/qc-runs/{run_id}/`, and
records the run metadata in PostgreSQL. The API does **not** execute, schedule, or
monitor Nextflow itself.

## Requirements

The **API and CLI** run on native Windows, macOS, or Linux. The **Nextflow
workflow** runs on Linux or macOS, or on Windows through WSL — so on Windows you
drive `bioqc start` from a WSL shell while the API can stay on native Windows.

| Tool | Used for | Install |
| --- | --- | --- |
| Python 3.13+ | API and CLI | [python.org/downloads](https://www.python.org/downloads/), or `uv python install 3.13` |
| uv | Dependency management | [Install guide](https://docs.astral.sh/uv/getting-started/installation/) |
| Docker | PostgreSQL + workflow containers | [Desktop](https://www.docker.com/products/docker-desktop/) (Windows/macOS) · [Engine](https://docs.docker.com/engine/install/) (Linux) |
| Java 17+ | Required by Nextflow | [Temurin/Adoptium](https://adoptium.net/), `brew install openjdk@17` (macOS), or `apt install openjdk-17-jre` (Linux/WSL) |
| Nextflow | Runs the QC pipeline | See per-OS notes below and the [official install guide](https://nextflow.io/docs/latest/install.html) |

### Installing Nextflow

- **Linux / WSL** — install Java 17+, then `curl -s https://get.nextflow.io | bash`.
  Full step-by-step (Java, Nextflow, Docker, container pre-pull) is in
  [Run the Nextflow QC workflow](#run-the-nextflow-qc-workflow).
- **macOS** — `brew install nextflow` (or the `curl` installer above); needs
  Java 17+ (`brew install openjdk@17`). See the
  [official install guide](https://nextflow.io/docs/latest/install.html).
- **Windows** — Nextflow does **not** run natively on Windows. Run it inside
  [WSL](https://learn.microsoft.com/windows/wsl/install) with Docker Desktop's WSL
  integration enabled. The [Run the Nextflow QC workflow](#run-the-nextflow-qc-workflow)
  section walks through the full WSL setup.

## Full local demo

Make sure the [Requirements](#requirements) are installed first. The fastest way
to see the whole story. In the first terminal:

```bash
uv sync --extra dev
docker compose up -d postgres
uv run alembic upgrade head
uv run python scripts/generate_demo_fastq.py
uv run uvicorn app.main:app --reload
```

In a second terminal, run the local workflow and upload its report:

```bash
uv run bioqc start
```

`bioqc start` prompts for a samplesheet, output directory, API URL, and run name.
Because the demo step above generated synthetic data, enter the demo samplesheet
at the first prompt:

```text
Samplesheet path [pipelines/qc/samplesheet.csv]: pipelines/qc/samplesheet.demo.csv
```

Expected output:

```text
✓ Samplesheet valid
✓ Starting Nextflow QC workflow
✓ Nextflow completed
✓ Found MultiQC report: results/qc/multiqc/multiqc_report.html
✓ Uploaded MultiQC report to BioQC Portal

Run registered successfully.
```

Then confirm the stored metadata:

```bash
curl http://localhost:8000/qc-runs
```

> **Nextflow must be on your PATH** for `bioqc start` (it shells out to
> `nextflow run`). On Windows this means running the CLI from WSL, where Nextflow,
> Java, and Docker are available — see
> [Run the Nextflow QC workflow](#run-the-nextflow-qc-workflow). The API itself can
> be developed and run from native Windows/PowerShell.

## Scope and boundaries

This is deliberately a thin, honest MVP. What it does:

- **The API** stores QC run metadata and the uploaded MultiQC report artifact.
- **The CLI** runs the local workflow (validate → Nextflow → MultiQC) and uploads
  the result to the API.

What it does **not** do yet:

- The API does **not** execute, schedule, or monitor Nextflow. It only registers
  runs that already completed locally.
- The demo data is **synthetic and not biologically meaningful**. It is shaped to
  exercise FastQC/MultiQC metrics (quality, GC, duplication, adapters) and must
  not be used for interpretation.
- The project follows selected **nf-core-inspired conventions** but does **not**
  claim nf-core compliance.

### Deliberately out of scope / Not built yet

- API-driven workflow orchestration (the API does not run Nextflow).
- Remote or cloud execution (no Kubernetes, HPC, or batch backends).
- Raw FASTQ upload or storage (only the generated MultiQC report is uploaded).
- Production-grade artifact storage such as S3-compatible object storage.
- Authentication and authorization.
- A frontend / React UI.

## The two register-local endpoints

Both endpoints record a completed local run; they differ in how the report is
handled:

| Endpoint | Body | Report handling | Used by |
| --- | --- | --- | --- |
| `POST /qc-runs/register-local` | JSON | Records the **client-side report path** only; nothing is copied | Manual / debug escape hatch |
| `POST /qc-runs/register-local-upload` | multipart | **Uploads and stores** the MultiQC report under `artifacts/qc-runs/{run_id}/` and records that backend-owned path | `bioqc start` |

Use `register-local` when a run already completed elsewhere (for example in CI)
and you only want a lightweight, path-based metadata record. Use
`register-local-upload` — the path `bioqc start` takes — when you want the backend
to own and store the report artifact.

## Architecture

FastAPI handles platform/API concerns. PostgreSQL stores metadata only. Nextflow
owns workflow execution. FastQC performs per-sample FASTQ quality assessment, and
MultiQC aggregates FastQC outputs into a combined report.

Generated FASTQ-derived files, FastQC outputs, and MultiQC reports live on the
filesystem (or future artifact storage), not in PostgreSQL. The database stores
structured metadata and the paths that point at those artifacts.

More detail is in [docs/architecture.md](docs/architecture.md) and the ADRs under
[docs/adr](docs/adr).

## Setup

See [Requirements](#requirements) for the tools you need before running these
steps.

Install dependencies:

```bash
uv sync --extra dev
```

Or with standard pip:

```bash
python -m pip install -e ".[dev]"
```

Copy the environment example if you want local overrides:

```bash
cp .env.example .env
```

### Run PostgreSQL

```bash
docker compose up -d postgres
```

The default connection string is:

```text
postgresql+psycopg://bioflowops:bioflowops@localhost:5433/bioflowops
```

Apply migrations before starting the API:

```bash
uv run alembic upgrade head
```

The first migration also adopts the exact pre-Alembic MVP schema created by
SQLAlchemy `create_all()`. Existing rows are preserved: `run_name` is backfilled
from `sample_name` (falling back to the run ID), `workflow_engine` is backfilled
as `nextflow`, and the legacy `sample_name` and `input_path` constraints are
relaxed to match the current model. An existing `qc_runs` table with an unknown
shape is rejected instead of being modified speculatively.

### Run the API

```bash
uv run uvicorn app.main:app --reload
```

Open:

- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

The Swagger UI at `/docs` has a light/dark switch in the top-right corner. It
defaults to your OS color scheme and remembers your choice in the browser.

## Local CLI

The CLI is the main entry point and the reason this project exists: it turns the
multi-step local QC workflow into one command and hands the result to the API.

### Preferred: `bioqc start`

`uv sync --extra dev` installs the `bioqc` command into the project's `.venv`.
Note that `uv sync` does **not** activate that environment or add it to your
`PATH`, so running a bare `bioqc` afterward fails with `command not found`. Run it
through `uv`, which uses the project environment automatically:

```bash
uv run bioqc start
```

Show the quick-start help:

```bash
uv run bioqc help
```

`start` prompts for the samplesheet, output directory, API URL, and an optional
run name, then runs the whole local QC flow: validate the samplesheet, run the
Nextflow QC pipeline, locate the MultiQC report, upload that HTML report to the
API, and register the completed run via `POST /qc-runs/register-local-upload`.

```text
samplesheet.csv → CLI → Nextflow/MultiQC → FastAPI /qc-runs/register-local-upload
```

The QC samplesheet convention is:

```csv
sample,fastq
sample_01,pipelines/qc/testdata/sample_01.fastq
```

If you want a bare `bioqc`, activate the environment first, or run the module
directly without installing the entry point:

```bash
# Linux / macOS / WSL
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
bioqc start

# Or, without activating:
uv run python -m cli start
uv run python -m cli help
```

> A `.venv` created on Windows cannot be reused from WSL or Linux (the script
> shims differ). If you switch shells, recreate it for the current OS with
> `rm -rf .venv && uv sync --extra dev`.

### Advanced: manual / debug commands

The individual commands remain available as escape hatches — for example, when
Nextflow was run separately or from CI.

Validate a samplesheet without running anything else:

```bash
uv run python -m cli validate pipelines/qc/samplesheet.csv
```

Validation checks that the CSV exists, has the required `sample` and `fastq`
columns, has non-empty unique sample IDs, and has non-empty FASTQ paths. It does
not require the FASTQ files to exist.

Register an already-completed local run, skipping the Nextflow step. This uses the
lower-level JSON `register-local` endpoint (path-only, no upload):

```bash
uv run python -m cli register-local \
  --run-dir results/qc \
  --samplesheet pipelines/qc/samplesheet.csv \
  --api-url http://localhost:8000
```

The command validates the samplesheet, searches `--run-dir` for exactly one
`multiqc_report.html`, then posts the run metadata. By default the run name comes
from the run directory name and timestamps use the current UTC time. Override them
with `--run-name`, `--started-at`, and `--completed-at`.

### Optional: shell completion and path hints

Tab completion is optional; the CLI works without it.

On Linux or WSL, the interactive `bioqc start` prompts for **Samplesheet path** and
**Output directory** support `Tab` completion of filesystem paths through the
standard-library `readline` module. Shells without `readline` (for example, stock
Windows Python) fall back to plain input.

Shell completion of subcommands and flags (`bioqc <TAB>`,
`bioqc register-local --<TAB>`) is provided by `argcomplete`, which ships in the
`dev` extra. Enable it in your shell:

```bash
eval "$(register-python-argcomplete bioqc)"
```

Add that line to `~/.bashrc` or `~/.zshrc` to make it persistent.

## Generate demo FASTQ data

The bundled default samplesheet points at tiny synthetic FASTQ fixtures under
`pipelines/qc/testdata/`. They are committed for quick smoke tests and are
intentionally too small to produce visually rich FastQC or MultiQC reports.

For a richer demo report, generate deterministic synthetic demo data:

```bash
uv run python scripts/generate_demo_fastq.py
```

This writes FASTQ files under the ignored `pipelines/qc/demo_data/` directory and
creates `pipelines/qc/samplesheet.demo.csv`. The demo samples (`sample_good`,
`sample_low_quality`, `sample_gc_bias`, `sample_duplicates`,
`sample_adapter_contamination`) are designed to show quality, GC, duplication, and
adapter-like differences in QC reports. They are **synthetic, not biologically
meaningful, and must not be used for interpretation.**

The generator supports local tuning:

```bash
uv run python scripts/generate_demo_fastq.py \
  --reads 10000 \
  --length 100 \
  --seed 42 \
  --outdir pipelines/qc/demo_data
```

## Run the Nextflow QC workflow

`bioqc start` runs Nextflow for you. You can also run the pipeline directly from
WSL/Linux at the repository root. On Windows, use WSL for Nextflow even if you
develop the API from PowerShell.

Install WSL from an elevated PowerShell prompt if needed:

```powershell
wsl --install -d Ubuntu
```

Install Java and basic shell tools inside WSL:

```bash
sudo apt update
sudo apt install -y curl openjdk-17-jre
java -version
```

Download and install Nextflow inside WSL:

```bash
curl -s https://get.nextflow.io | bash
chmod +x nextflow
mkdir -p "$HOME/.local/bin"
mv nextflow "$HOME/.local/bin/"
```

Make sure `~/.local/bin` is on your WSL `PATH`:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
nextflow -version
```

See the official docs for supported Java and install options:
https://nextflow.io/docs/latest/install.html

On Windows with Docker Desktop, enable WSL integration for your Ubuntu
distribution, then confirm Docker works from WSL:

```bash
docker run --rm hello-world
```

Pre-pull the QC workflow containers:

```bash
docker pull quay.io/biocontainers/fastqc:0.12.1--hdfd78af_0
docker pull quay.io/biocontainers/multiqc:1.25.1--pyhdfd78af_0
```

If the MultiQC pull fails with `docker: error getting credentials`, clear the
stale Quay credential entry and pull again:

```bash
docker logout quay.io
docker pull quay.io/biocontainers/multiqc:1.25.1--pyhdfd78af_0
```

Run the workflow:

```bash
nextflow run pipelines/qc/main.nf -profile docker
```

Resume after a failed pull or interrupted run:

```bash
nextflow run pipelines/qc/main.nf -profile docker -resume
```

Run it against the generated demo samplesheet:

```bash
nextflow run pipelines/qc/main.nf \
  -profile docker \
  --input pipelines/qc/samplesheet.demo.csv \
  --outdir results/demo
```

The pipeline accepts `--input` (preferred) or `--samplesheet`, plus `--outdir`.

Expected outputs:

- `results/qc/fastqc/` — per-sample FastQC HTML and ZIP files
- `results/qc/multiqc/` — combined MultiQC report and data directory
- `artifacts/qc-runs/{run_id}/multiqc_report.html` — API-owned uploaded report,
  after `bioqc start` (or `register-local-upload`) registers the run

## Database migrations

Alembic has two separate steps: creating a migration file, then applying it.

After changing SQLAlchemy models, create a new revision:

```bash
uv run alembic revision --autogenerate -m "describe schema change"
```

Review the generated file before applying it — autogeneration is a starting point,
not a substitute for checking the operations. Apply pending migrations:

```bash
uv run alembic upgrade head
```

Check whether the schema still differs from the models:

```bash
uv run alembic check
```

The bootstrap migration supports two starting points:

- an empty database, where it creates the current `qc_runs` schema;
- the exact pre-Alembic `create_all()` schema, where it preserves existing rows,
  adds and backfills `run_name` and `workflow_engine`, and brings constraints and
  indexes in line with the current model.

It intentionally fails for an unrecognized existing `qc_runs` shape. Inspect and
migrate such a database explicitly rather than letting the bootstrap migration
guess how its columns should map.

## Tests

```bash
uv run pytest
```

Ordinary API tests use an in-memory SQLite database override, so PostgreSQL is not
required for local unit tests. Migration regression tests use temporary SQLite
databases to cover both a fresh install and adoption of the pre-Alembic schema,
including row preservation and backfills.

The end-to-end suite runs the CLI and Uvicorn as real subprocesses over loopback
HTTP. A lightweight fake `nextflow` executable produces a deterministic MultiQC
report, so the tests cover CLI prompting, workflow invocation, multipart upload,
database persistence, API serialization, artifact storage, report download, and
the failed-workflow path without requiring Docker or bioinformatics containers:

```bash
uv run pytest -m e2e -v
```

These tests are skipped on native Windows because the project runs Nextflow
through WSL there. They run normally on Linux, macOS, WSL, and GitHub Actions and
remain part of the default `uv run pytest` suite.

API CI additionally starts PostgreSQL 18, applies every Alembic revision, and runs
`alembic check`. CI is triggered by backend, CLI, migration, script, test, and
database-configuration changes, and type-checks `app`, `cli`, and `scripts`. Its
security job uploads the generated SPDX SBOM and an informational Grype JSON
vulnerability report as separate workflow artifacts. Vulnerability findings do
not fail the build; the report is retained for inspection without treating
SBOM-only findings as source-code locations.

## Lint and format

```bash
uv run ruff check .
uv run ruff format .
```

## API reference

The API exposes metadata endpoints only; it records paths and statuses and does
not execute Nextflow.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Health check |
| `POST` | `/qc-runs/seed` | Seed local demo metadata |
| `GET` | `/qc-runs` | List QC runs |
| `GET` | `/qc-runs/{run_id}` | Fetch a single run |
| `POST` | `/qc-runs` | Create a metadata record manually |
| `POST` | `/qc-runs/register-local` | Register a completed run from paths (JSON, no upload) |
| `POST` | `/qc-runs/register-local-upload` | Register a completed run and upload the MultiQC report (multipart) |
| `GET` | `/qc-runs/{run_id}/multiqc-report` | Download a stored MultiQC report (backend-owned uploads only) |

Seed and list:

```bash
curl -X POST http://localhost:8000/qc-runs/seed
curl http://localhost:8000/qc-runs
curl http://localhost:8000/qc-runs/1
```

Register a completed local run and upload the MultiQC report (the `bioqc start`
path):

```bash
curl -X POST http://localhost:8000/qc-runs/register-local-upload \
  -F "run_name=local-qc-2026-05-23" \
  -F "samplesheet_path=pipelines/qc/samplesheet.csv" \
  -F "run_dir=results/qc" \
  -F "pipeline_name=fastqc-multiqc" \
  -F "pipeline_version=0.1.0" \
  -F "sample_count=2" \
  -F "started_at=2026-05-23T10:00:00Z" \
  -F "completed_at=2026-05-23T10:05:00Z" \
  -F "multiqc_report=@results/qc/multiqc/multiqc_report.html;type=text/html"
```

The upload endpoint stores the report under `artifacts/qc-runs/{run_id}/` and
records that backend-owned path in the run metadata. Alongside the path it records
report integrity (`report_size_bytes`, `report_sha256`, both computed server-side)
and the optional `sample_count`, `started_at`, and `completed_at` provenance
fields; the run record then exposes `sample_count` and a derived
`duration_seconds`. Timestamps must be timezone-aware (e.g. end with `Z`).
`bioqc start` sends all of these automatically (it counts the samplesheet rows and
times the Nextflow run) and prints them — including the report URL — in the run
summary.

Retrieve a stored report. Only backend-owned uploads under `artifacts/` are
served; path-only `register-local` records and any path outside the artifact store
return `404`:

```bash
curl -L http://localhost:8000/qc-runs/{run_id}/multiqc-report -o multiqc_report.html
```

The lightweight JSON endpoint records only the client-side report path:

```bash
curl -X POST http://localhost:8000/qc-runs/register-local \
  -H "Content-Type: application/json" \
  -d '{
    "run_name": "local-qc-2026-05-23",
    "workflow_name": "fastqc-multiqc",
    "workflow_engine": "nextflow",
    "status": "COMPLETED",
    "output_path": "results/qc",
    "multiqc_report_path": "results/qc/multiqc/multiqc_report.html",
    "started_at": "2026-05-23T10:00:00Z",
    "completed_at": "2026-05-23T10:05:00Z"
  }'
```

## Next steps

1. Tighten the local demo and provenance story (richer report examples, clearer
   run summaries).
2. Add API polish such as pagination and filtering once the CLI workflow is the
   primary path.
3. Keep workflow execution from the API, cloud, Kubernetes, and HPC execution
   deferred until there is a clear ADR and the MVP boundary is stable.
