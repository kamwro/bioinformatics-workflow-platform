# ADR-0009: Generate synthetic demo FASTQ data

## Status

Accepted

## Date

2026-05-25

## Context

The committed FASTQ fixtures are intentionally tiny so smoke tests and local
pipeline checks run quickly. They are useful for verifying that FastQC and
MultiQC execute, but they produce sparse reports with little visual contrast.

The project also needs demo data that makes local FastQC and MultiQC reports
more useful during portfolio walkthroughs without committing large generated
FASTQ files.

## Decision

We will keep the tiny committed synthetic FASTQ fixtures for quick smoke tests.

For richer local reports, we will provide a deterministic script that generates
synthetic FASTQ files under `pipelines/qc/demo_data/` and writes
`pipelines/qc/samplesheet.demo.csv`.

The generated demo data will include samples with intentionally different QC
profiles, such as balanced high-quality reads, declining quality, GC bias,
duplicates, and adapter-like contamination. The generated FASTQ directory will
be ignored by git.

## Alternatives considered

### Commit larger demo FASTQ files

Rejected. Larger FASTQ files would make the repository heavier and slow down
normal clone and review workflows.

### Use only the tiny committed fixtures

Rejected. The tiny fixtures are good smoke tests, but they do not create
visually useful QC reports.

### Generate deterministic synthetic demo data locally

Accepted. This keeps the repository small while allowing local demos to produce
more realistic-looking QC variation.

## Consequences

- Reviewers can run quick smoke tests with committed fixtures.
- Local demos can generate richer reports on demand.
- Generated FASTQ files remain disposable and are not committed.
- Documentation must state that the generated data is synthetic and not for
  biological interpretation.
