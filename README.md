# BioFlowOps

BioFlowOps is a bioinformatics workflow platform skeleton built as a portfolio
project. It demonstrates Python backend/API engineering, PostgreSQL metadata
tracking, and a small Nextflow DSL2 QC workflow around FastQC and MultiQC.

This is not a clinical tool and not production-grade bioinformatics software.
The goal is a small, honest first milestone that is easy to explain in an
interview.

## MVP Scope

The current MVP does four things:

1. Runs a FastAPI service for QC run metadata.
2. Stores workflow metadata and report paths in PostgreSQL.
3. Provides a demo seeding endpoint for local development.
4. Includes a minimal Nextflow workflow: FASTQ to FastQC to MultiQC.

It intentionally does not include React, authentication, cloud execution,
Kubernetes, workflow queues, or clinical interpretation.

## Architecture

FastAPI handles platform/API concerns. PostgreSQL stores metadata only.
Nextflow handles workflow execution. FastQC performs per-sample FASTQ quality
assessment. MultiQC aggregates FastQC outputs into a combined report.

Generated FASTQ-derived files, FastQC outputs, MultiQC reports, and workflow
logs live on the filesystem or future artifact storage, not in PostgreSQL.

More detail is in [docs/architecture.md](docs/architecture.md).

## Main commands

```bash
uv sync --extra dev
docker compose up -d postgres
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
uv run pytest
nextflow run pipelines/qc/main.nf -profile docker
```

Seed demo metadata:

```bash
curl -X POST http://localhost:8000/qc-runs/seed
curl http://localhost:8000/qc-runs
```

## Prerequisites

- Python 3.13+ or Python 3.14
- uv for Python dependency management
- Docker Desktop or Docker Engine
- Nextflow and Java 17+ in a Linux/WSL shell for running the QC workflow

The API can be developed on Windows. The Nextflow command is documented for
WSL/Linux because Docker path handling is much more predictable there.

## Setup

Install Python dependencies:

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

## Run PostgreSQL

```bash
docker compose up -d postgres
```

The default connection string is:

```text
postgresql+psycopg://bioflowops:bioflowops@localhost:5433/bioflowops
```

Run database migrations before starting the API:

```bash
uv run alembic upgrade head
```

The first migration also upgrades older local MVP databases that already have a
`qc_runs` table but are missing newer columns such as `run_name`.

## Create Database Migrations

Alembic has two separate steps:

1. Create a migration file under `migrations/versions`.
2. Apply migration files to the database.

After changing SQLAlchemy models, create a new migration revision:

```bash
uv run alembic revision --autogenerate -m "describe schema change"
```

Review the generated file before applying it. Autogeneration is a starting
point, not a substitute for checking the operations.

Apply pending migrations:

```bash
uv run alembic upgrade head
```

Check whether the current database schema still differs from the SQLAlchemy
models:

```bash
uv run alembic check
```

Use `upgrade head` to run existing migration files. It does not create new files
in `migrations/versions`.

## Run the API

```bash
uv run uvicorn app.main:app --reload
```

Open:

- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## API Examples

Seed local demo metadata:

```bash
curl -X POST http://localhost:8000/qc-runs/seed
```

List QC runs:

```bash
curl http://localhost:8000/qc-runs
```

Fetch a single run:

```bash
curl http://localhost:8000/qc-runs/1
```

Create a metadata record manually:

```bash
curl -X POST http://localhost:8000/qc-runs \
  -H "Content-Type: application/json" \
  -d '{
    "sample_name": "sample_01",
    "workflow_name": "fastqc-multiqc",
    "workflow_version": "0.1.0",
    "status": "PENDING",
    "input_path": "pipelines/qc/testdata/sample_01.fastq",
    "output_dir": "results/qc",
    "report_path": null
  }'
```

The API records paths and statuses only. It does not execute Nextflow yet.

Register a completed local Nextflow QC run:

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

This endpoint only stores metadata for a run that already completed outside
the API. It does not start, monitor, or parse a Nextflow execution.

## Run Tests

```bash
uv run pytest
```

Tests use an in-memory SQLite database override, so PostgreSQL is not required
for the test suite.

## Lint and Format

```bash
uv run ruff check .
uv run ruff format .
```

## Run the Nextflow QC Workflow

Run the workflow from WSL/Linux at the repository root. On Windows, use WSL for
Nextflow even if you develop the API from PowerShell.

Install WSL from an elevated PowerShell prompt if it is not installed yet:

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

Make sure `~/.local/bin` is on your WSL `PATH`. If needed, add it:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
nextflow -version
```

See the official Nextflow installation docs for the latest supported Java and
installation options: https://nextflow.io/docs/latest/install.html

On Windows with Docker Desktop, enable WSL integration for your Ubuntu
distribution in Docker Desktop settings. Then confirm Docker works from WSL:

```bash
docker run --rm hello-world
```

Pre-pull the QC workflow containers:

```bash
docker pull quay.io/biocontainers/fastqc:0.12.1--hdfd78af_0
docker pull quay.io/biocontainers/multiqc:1.25.1--pyhdfd78af_0
```

If the MultiQC image pull fails with `docker: error getting credentials`, clear
the stale Quay credential entry and pull again:

```bash
docker logout quay.io
docker pull quay.io/biocontainers/multiqc:1.25.1--pyhdfd78af_0
```

Run the workflow:

```bash
nextflow run pipelines/qc/main.nf -profile docker
```

Resume after fixing a failed container pull or interrupted run:

```bash
nextflow run pipelines/qc/main.nf -profile docker -resume
```

Useful parameters:

```bash
nextflow run pipelines/qc/main.nf \
  -profile docker \
  --samplesheet pipelines/qc/samplesheet.csv \
  --outdir results/qc
```

The bundled samplesheet points at tiny synthetic FASTQ fixtures under
`pipelines/qc/testdata/`. These files are intentionally small and not
biologically meaningful.

Expected outputs:

- `results/qc/fastqc/` - per-sample FastQC HTML and ZIP files
- `results/qc/multiqc/` - combined MultiQC report and data directory

After running the workflow, metadata can be registered through the API with
paths such as `results/qc/multiqc/multiqc_report.html`:

```bash
curl -X POST http://localhost:8000/qc-runs/register-local \
  -H "Content-Type: application/json" \
  -d '{
    "run_name": "local-qc-demo",
    "workflow_name": "fastqc-multiqc",
    "output_path": "results/qc",
    "multiqc_report_path": "results/qc/multiqc/multiqc_report.html",
    "started_at": "2026-05-23T10:00:00Z",
    "completed_at": "2026-05-23T10:05:00Z"
  }'
```

## Known limitations

This is an MVP skeleton. It does not execute Nextflow from the API yet, has no
frontend, no authentication, no cloud/Kubernetes deployment, and stores only
metadata in PostgreSQL.

The API can register completed local workflow runs, but it intentionally does
not execute or monitor Nextflow yet.

## Next Steps

1. Add pagination/filtering for QC run metadata.
2. Consider a small CLI helper for registering local runs after Nextflow exits.
3. Add a minimal frontend only after the API and workflow boundary are stable.
