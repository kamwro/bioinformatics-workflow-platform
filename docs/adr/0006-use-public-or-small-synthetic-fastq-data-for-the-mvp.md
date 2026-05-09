# ADR-0006: Use public or small synthetic FASTQ data for the MVP

## Status

Proposed

## Date

2026-05-09

## Context

A portfolio project should be easy to run, legally safe, and reproducible.

Using patient data or private clinical datasets would create unnecessary ethical, legal, and privacy risks. The MVP does not need sensitive data to demonstrate workflow execution, metadata tracking, and reporting.

## Decision

The MVP will use either:

1. very small synthetic FASTQ fixtures stored in the repository, or
2. small public sequencing datasets downloaded from public repositories such as NCBI SRA.

For default local demos and CI, synthetic or tiny bundled test data is preferred to keep the project fast and deterministic.

## Alternatives considered

### Private or clinical data

Rejected. It is unnecessary and creates privacy/compliance risk.

### Large public datasets

Rejected for MVP defaults. Large datasets make the project slower, harder to run, and less suitable for local CI.

### Small public or synthetic FASTQ data

Accepted. This is enough to demonstrate the workflow without operational overhead.

## Consequences

- The project can be run by reviewers locally.
- CI can execute quickly using tiny fixture data.
- The project avoids patient privacy concerns.
- Documentation should explain that the dataset is intentionally small and not biologically meaningful.

## Sources

- NCBI describes its mission as providing access to biomedical and genomic information: https://www.ncbi.nlm.nih.gov/
- NCBI SRA Toolkit documentation describes `fasterq-dump` as a tool that extracts FASTQ/FASTA data from SRA accessions: https://github.com/ncbi/sra-tools/wiki/HowTo%3A-fasterq-dump
- NCBI SRA data formats documentation: https://www.ncbi.nlm.nih.gov/sra/docs/sra-data-formats
