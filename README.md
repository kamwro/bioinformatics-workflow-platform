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
- Nextflow and a Linux/WSL shell for running the QC workflow

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

Tables are created on FastAPI startup for this MVP. Alembic is intentionally
deferred until schema evolution becomes meaningful.

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

From WSL/Linux at the repository root:

```bash
nextflow run pipelines/qc/main.nf -profile docker
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
paths such as `results/qc/multiqc/multiqc_report.html`.

## Known limitations

This is an MVP skeleton. It intentionally uses startup table creation instead of
Alembic migrations, does not execute Nextflow from the API yet, has no frontend,
no authentication, no cloud/Kubernetes deployment, and stores only metadata in
PostgreSQL.

The next best step is to add a small endpoint or command for registering a
completed local workflow run before adding any UI.

## Next Steps

1. Add Alembic once schema changes start accumulating.
2. Add a small service that registers a completed local Nextflow run.
3. Add pagination/filtering for QC run metadata.
4. Add a minimal frontend only after the API and workflow boundary are stable.
