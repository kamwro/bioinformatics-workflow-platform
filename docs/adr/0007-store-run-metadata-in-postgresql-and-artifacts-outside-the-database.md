# ADR-0007: Store run metadata in PostgreSQL and artifacts outside the database

## Status

Accepted

## Date

2026-05-09

## Context

Bioinformatics workflows generate different kinds of data:

- metadata about the run,
- workflow logs,
- quality-control outputs,
- HTML reports,
- possible future large files such as BAM, VCF, or intermediate files.

Relational databases are useful for structured metadata and querying run history. Large workflow artifacts are better kept in filesystem or object storage.

## Decision

We will store **run metadata** in PostgreSQL and **workflow artifacts** outside the database.

PostgreSQL will store structured metadata such as:

- run ID,
- sample ID,
- workflow name and version,
- status,
- timestamps,
- input metadata,
- output paths,
- report path,
- selected QC summary fields.

Pipeline outputs, logs, and reports will be stored on local filesystem for the MVP and behind an S3-compatible storage abstraction in a later phase.

## Alternatives considered

### Store everything in PostgreSQL

Rejected. Large files and generated reports should not be stored directly in relational tables for this MVP.

### Store only files and no database

Rejected. It would make run history, filtering, status tracking, and API design weaker.

### Store metadata in PostgreSQL and artifacts externally

Accepted. This mirrors a common platform pattern: database for metadata, object/file storage for artifacts.

## Consequences

- The API can query runs efficiently.
- Large files do not bloat the database.
- The storage strategy can evolve from local filesystem to S3-compatible object storage.
- The project can demonstrate clean separation between metadata and artifacts.

## Sources

- PostgreSQL official documentation: https://www.postgresql.org/docs/
- Nextflow documentation emphasizes workflows and execution outputs rather than using a relational database as an artifact store: https://www.nextflow.io/
- AWS S3 documentation describes S3 as object storage for data retrieval at any scale: https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html
