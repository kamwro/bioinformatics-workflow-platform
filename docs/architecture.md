# Architecture

BioFlowOps is a small bioinformatics workflow platform skeleton. It separates
platform metadata concerns from workflow execution and generated artifacts.

## Components

### FastAPI API

The API exposes metadata endpoints for QC workflow runs:

- `GET /health`
- `POST /qc-runs/seed`
- `GET /qc-runs`
- `POST /qc-runs`
- `GET /qc-runs/{run_id}`

It does not execute Nextflow in this MVP. It registers and exposes metadata
records that point to inputs, output directories, and reports.

### PostgreSQL

PostgreSQL stores structured metadata:

- sample name
- workflow name and version
- status
- input path
- output directory
- report path
- error message
- timestamps

It does not store FASTQ files, FastQC outputs, MultiQC reports, logs, or large
workflow artifacts.

### Nextflow

Nextflow owns workflow execution. The current workflow is a minimal DSL2
pipeline in `pipelines/qc`:

```text
FASTQ -> FastQC -> MultiQC
```

The workflow reads a samplesheet, runs FastQC for each FASTQ, and aggregates
FastQC outputs with MultiQC.

### Filesystem Artifacts

For the MVP, workflow artifacts live under `results/qc` by default. A future
version could move artifacts to S3-compatible object storage without changing
the basic rule: PostgreSQL stores metadata and paths, not generated files.

## Data and Artifact Flow

1. A samplesheet references one or more FASTQ files.
2. Nextflow runs FastQC per sample.
3. Nextflow runs MultiQC over FastQC outputs.
4. Reports are published to `results/qc`.
5. The API stores metadata that points at the input and report paths.
6. Clients query the API for run status and metadata.

## Why Metadata Is Separate From Artifacts

Bioinformatics workflows can generate many files, and future workflows may
produce large BAM, VCF, HTML, JSON, or log artifacts. Relational databases are
well suited for structured metadata and querying run history. They are not the
right default place for large generated files.

Keeping artifacts outside PostgreSQL makes the MVP simpler and leaves a clean
path to local filesystem storage, object storage, or managed artifact storage
later.
