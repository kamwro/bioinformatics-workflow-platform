# ADR-0003: Follow nf-core-inspired structure without full nf-core compliance

## Status

Proposed

## Date

2026-05-09

## Context

The project should look familiar to bioinformatics engineers who have seen production-quality Nextflow pipelines. However, full nf-core compliance can be too heavy for an MVP portfolio project.

We want to borrow practical conventions: clear parameters, samplesheet-based input, predictable output directories, modular workflow structure, containerized tools, and good documentation.

## Decision

We will follow **nf-core-inspired patterns** but will not claim full nf-core compliance in the MVP.

The README and documentation should explicitly say that the project is "nf-core-inspired" rather than "an nf-core pipeline".

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
