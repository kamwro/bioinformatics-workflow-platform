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
2. Stores workflow metadata and uploaded report artifact paths in PostgreSQL.
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
uv run python scripts/generate_demo_fastq.py
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

The Swagger UI at `/docs` has a light/dark switch in the top-right corner. It
defaults to your OS color scheme and remembers your choice in the browser.

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

Register a completed local Nextflow QC run and upload the generated MultiQC
HTML report:

```bash
curl -X POST http://localhost:8000/qc-runs/register-local-upload \
  -F "run_name=local-qc-2026-05-23" \
  -F "samplesheet_path=pipelines/qc/samplesheet.csv" \
  -F "run_dir=results/qc" \
  -F "pipeline_name=fastqc-multiqc" \
  -F "pipeline_version=0.1.0" \
  -F "multiqc_report=@results/qc/multiqc/multiqc_report.html;type=text/html"
```

The upload endpoint stores the report under `artifacts/qc-runs/{run_id}/` and
records that backend-owned artifact path in the QC run metadata.

The older JSON endpoint remains available as a lower-level path-only escape
hatch for already-completed local runs:

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

This endpoint only stores metadata for a run that is already completed outside
the API. It records the client-side report path instead of uploading the report
artifact. It does not start, monitor, or parse a Nextflow execution.

## Local CLI Usage

The local CLI drives the full local QC workflow: validate the samplesheet, run
the Nextflow QC pipeline, locate the MultiQC report, upload that HTML report to
FastAPI, and register the completed run metadata.

```text
samplesheet.csv -> CLI -> Nextflow/MultiQC -> FastAPI register-local-upload endpoint
```

### Preferred: `bioqc start`

Install the project into its virtual environment at once:

```bash
uv sync --extra dev
```

This installs the `bioqc` command into the project's `.venv`. Note that
`uv sync` does **not** activate that environment or add it to your `PATH`, so
running `bioqc` directly afterward fails with `bioqc: command not found`. Run
it through `uv`, which uses the project environment automatically:

```bash
uv run bioqc start
```

Show the BioQC quick-start help:

```bash
uv run bioqc help
```

If you want a bare `bioqc`, activate the environment first:

```bash
# Linux / macOS / WSL
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

bioqc start
```

You can also run the workflow without installing anything, straight from the
module:

```bash
uv run python -m cli help
uv run python -m cli start
```

> A `.venv` created on Windows cannot be reused from WSL or Linux (the script
> shims differ). If you switch between shells, recreate it for the current OS
> with `rm -rf .venv && uv sync --extra dev`.

`start` prompts for the samplesheet, output directory, API URL, and an optional
run name, then runs the whole local QC flow end to end:

```text
$ uv run bioqc start

BioQC Portal CLI
Press Ctrl+C to cancel.

Samplesheet path [pipelines/qc/samplesheet.csv] (use pipelines/qc/samplesheet.demo.csv if you generated demo data):
Output directory [results/qc]:
API URL [http://localhost:8000]:
Run name [qc]:

✓ Samplesheet valid
✓ Starting Nextflow QC workflow
✓ Nextflow completed
✓ Found MultiQC report: results/qc/multiqc/multiqc_report.html
✓ Uploaded MultiQC report to BioQC Portal

Run registered successfully.
```

`start` requires `nextflow` to be on your PATH (see the Nextflow setup section
above). The QC workflow samplesheet convention is:

```csv
sample,fastq
sample_01,pipelines/qc/testdata/sample_01.fastq
```

### Optional: shell completion and path hints

Tab completion is optional; the CLI works without it.

On Linux or WSL, the interactive `bioqc start` prompts for **Samplesheet path**
and **Output directory** support `Tab` completion of filesystem paths through the
standard-library `readline` module. Shells without `readline` (for example, stock
Windows Python) fall back to plain input.

Shell completion of subcommands and flags (`bioqc <TAB>`,
`bioqc register-local --<TAB>`) is provided by `argcomplete`, which ships in the
`dev` extra (`uv sync --extra dev`). Enable it in your shell:

```bash
eval "$(register-python-argcomplete bioqc)"
```

Add that line to `~/.bashrc` or `~/.zshrc` to make it persistent.

### Advanced: manual validation and registration

The individual commands remain available as manual escape hatches, for example,
when Nextflow was run separately or from CI.

Validate a samplesheet without running anything else:

```bash
uv run python -m cli validate pipelines/qc/samplesheet.csv
```

The CLI checks that the CSV exists, has the required `sample` and `fastq`
columns, has non-empty unique sample IDs, and has non-empty FASTQ paths. It
does not require FASTQ files to exist during validation.

Register an already-completed local run, skipping the Nextflow step:

```bash
uv run python -m cli register-local \
  --run-dir results/qc \
  --samplesheet pipelines/qc/samplesheet.csv \
  --api-url http://localhost:8000
```

The command validates the samplesheet, searches `--run-dir` for exactly one
`multiqc_report.html`, then posts run metadata to
`/qc-runs/register-local`. This manual command keeps the older JSON/path-based
behavior; `bioqc start` uses the upload endpoint instead. By default, the run
name comes from the run directory name and timestamps use the current UTC time.
You can override them:

```bash
uv run python -m cli register-local \
  --run-dir results/qc \
  --samplesheet pipelines/qc/samplesheet.csv \
  --api-url http://localhost:8000 \
  --run-name local-qc-demo \
  --started-at 2026-05-23T10:00:00Z \
  --completed-at 2026-05-23T10:05:00Z
```

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

The bundled default samplesheet points at tiny synthetic FASTQ fixtures under
`pipelines/qc/testdata/`. These files are committed to the repository for quick
pipeline smoke tests. They are intentionally too small to produce visually rich
FastQC or MultiQC reports.

For a richer local demo report, generate deterministic synthetic demo data:

```bash
uv run python scripts/generate_demo_fastq.py
```

This writes FASTQ files under the ignored `pipelines/qc/demo_data/` directory
and creates `pipelines/qc/samplesheet.demo.csv`. The demo samples are synthetic
and designed to show quality, GC, duplication, and adapter-like differences in
QC reports. They are not biologically meaningful and should not be used for
interpretation.

The generator supports local tuning:

```bash
uv run python scripts/generate_demo_fastq.py \
  --reads 10000 \
  --length 100 \
  --seed 42 \
  --outdir pipelines/qc/demo_data
```

Run the workflow with the generated demo samplesheet:

```bash
nextflow run pipelines/qc/main.nf \
  -profile docker \
  --input pipelines/qc/samplesheet.demo.csv \
  --outdir results/demo
```

Expected outputs:

- `results/qc/fastqc/` - per-sample FastQC HTML and ZIP files
- `results/qc/multiqc/` - combined MultiQC report and data directory
- `artifacts/qc-runs/{run_id}/multiqc_report.html` - API-owned uploaded report
  after `bioqc start` registers the run

After running the workflow separately, the lower-level JSON endpoint can still
register metadata with paths such as `results/qc/multiqc/multiqc_report.html`:

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

1. Tighten the scientific-computing story:
   - document the full local path from demo FASTQ generation to Nextflow output
     to API registration,
   - include an example report path and known-good demo command sequence,
   - keep the README honest about the API/workflow boundary.
2. Expand the local CLI only where it improves the demo:
   - add optional samplesheet path existence checks,
   - add a dry-run mode that prints the register-local payload,
   - add a short-run summary command if it stays simple.
3. Prepare the project for external review:
   - open focused GitHub issues for CLI polish and samplesheet validation,
   - add a short portfolio summary once the CLI slice is working,
   - prepare a LinkedIn/GitHub feedback post aimed at bioinformatics and
     scientific-computing people.
4. Keep pagination/filtering as the next API polish item after the CLI workflow
   is useful.
5. Keep frontend, workflow execution from the API, cloud, Kubernetes, and HPC
   execution deferred until there is a clear ADR and the MVP boundary is stable.
