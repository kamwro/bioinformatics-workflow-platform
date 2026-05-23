# AGENTS.md

## Project Purpose

BioFlowOps is a portfolio project for bioinformatics platform engineering and
life sciences software. It is a small bioinformatics workflow platform skeleton,
not a production product and not a clinical tool.

The project demonstrates Python API engineering, PostgreSQL metadata storage,
simple workflow metadata seeding, and a minimal Nextflow DSL2 QC workflow using
FastQC and MultiQC.

## Current MVP Scope

- FastAPI API for QC workflow run metadata.
- PostgreSQL for metadata only.
- Local/demo metadata seeding endpoint.
- Completed local Nextflow QC run registration endpoint.
- Minimal Nextflow workflow: FASTQ to FastQC to MultiQC.
- Tiny synthetic FASTQ fixtures for local testing.
- Documentation and ADRs that match the implementation.

## Do Not Build Yet

- React or any frontend.
- Authentication or authorization.
- Cloud/AWS execution.
- Kubernetes or Helm.
- A queue system or scheduler.
- Clinical interpretation or patient-facing claims.
- Storage of FASTQ files, reports, or large artifacts in PostgreSQL.

## Architecture Boundaries

- FastAPI handles platform/API concerns.
- PostgreSQL stores metadata and paths only.
- Nextflow handles workflow execution.
- The API may register metadata for completed local Nextflow runs, but must not
  start, monitor, or parse workflow executions yet.
- FastQC performs per-sample quality assessment.
- MultiQC aggregates FastQC outputs into one report.
- Files and reports live on the filesystem for the MVP and may move to artifact
  storage later.

## Commands

Install dependencies:

```bash
uv sync --extra dev
```

Start PostgreSQL:

```bash
docker compose up -d postgres
```

Run the API:

```bash
uv run uvicorn app.main:app --reload
```

Seed demo metadata:

```bash
curl -X POST http://localhost:8000/qc-runs/seed
```

Register completed local QC run metadata:

```bash
curl -X POST http://localhost:8000/qc-runs/register-local
```

Run tests:

```bash
uv run pytest
```

Run lint/format:

```bash
uv run ruff check .
uv run ruff format .
```

Run the Nextflow workflow from WSL/Linux:

```bash
nextflow run pipelines/qc/main.nf -profile docker
```

## Python and Backend Conventions

- Use Python 3.13+ compatible typing.
- Prefer small modules with clear responsibilities.
- Keep FastAPI route handlers thin.
- Put database access in repository modules.
- Put API-facing behavior in service modules.
- Use Pydantic v2 models for request and response schemas.
- Use SQLAlchemy 2.x typed mappings with `Mapped[]` and `mapped_column`.
- Store enum-like statuses as clear string values: `PENDING`, `RUNNING`,
  `COMPLETED`, `FAILED`.
- Raise HTTP 404 for missing QC run records.
- Do not add authentication or background execution until there is an ADR.

## Nextflow Conventions

- Use standard Nextflow DSL2.
- Keep the QC workflow readable and minimal.
- Accept a samplesheet CSV with `sample` and `fastq` columns.
- Use Docker containers for FastQC and MultiQC.
- Publish outputs under a predictable `results/qc` directory by default.
- Keep bundled FASTQ fixtures tiny, synthetic, and safe to commit.
- Do not claim nf-core compliance. This project uses selected nf-core-inspired
  conventions only.

## ADR Rules

- Check `docs/adr/` before changing architecture, storage, workflow execution,
  or scope.
- If implementation contradicts an ADR, update the ADR or add a new one.
- ADRs should be professional, concise, and non-defensive.
- Keep ADR status aligned with implementation reality.

## Testing Expectations

- Add or update pytest coverage for API behavior.
- Tests should not require PostgreSQL unless the behavior specifically needs it.
- Use SQLite overrides for ordinary API tests.
- Cover health, seeding, listing, get-by-id, create behavior, and status
  serialization/model behavior.
- Cover completed local QC run registration behavior when changing that
  endpoint, schema, or service.
- Run `uv run pytest` before finishing when possible.
