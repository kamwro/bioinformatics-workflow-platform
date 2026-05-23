# ADR-0003: Use selected nf-core conventions without claiming nf-core compliance

## Status

Accepted

## Date

2026-05-09

## Context

The project should look familiar to bioinformatics engineers who have seen production-quality Nextflow pipelines. However, full nf-core compliance can be too heavy for an MVP portfolio project.

We want to borrow practical conventions: clear parameters, samplesheet-based input, predictable output directories, modular workflow structure, containerized tools, and good documentation.

## Decision

We will follow selected nf-core conventions where they improve readability, reproducibility, and maintainability.

The project will not claim to be an official nf-core pipeline or fully nf-core compliant in the MVP.

## Alternatives considered

### Full nf-core pipeline compliance from the start

Rejected for MVP. It would create too much process overhead before proving the end-to-end workflow.

### Completely custom structure

Rejected. It would reduce the project's relevance to real-world Nextflow/bioinformatics practices.

### nf-core-inspired structure

Accepted. It gives the project professional shape while keeping the scope achievable.

## Consequences

- The project can evolve toward stricter nf-core conventions later.
- Reviewers can see that the project follows recognized workflow design principles.
- Documentation must be clear about what is and is not implemented.

## Sources

- nf-core pipeline specifications define standards for high-quality, reproducible pipelines: https://nf-co.re/docs/specifications/pipelines/overview
- nf-core specifications describe best practices for robust, reproducible, and maintainable Nextflow components and pipelines: https://nf-co.re/docs/specifications/overview
- nf-core documentation: https://nf-co.re/docs/
