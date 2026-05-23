# ADR-0001: Define the project scope as a bioinformatics workflow platform

## Status

Accepted

## Date

2026-05-09

## Context

Bioinformatics workflows often require reproducible execution, clear metadata tracking, structured outputs, and accessible reports. This project explores how software engineering practices can be applied to a small bioinformatics workflow platform.

The MVP should demonstrate platform-engineering concerns around workflow execution, run tracking, metadata management, reporting, and future extensibility.

The project is intentionally limited to sequencing quality-control workflows. It does not aim to provide clinical interpretation, diagnosis, wet-lab protocol design, or variant pathogenicity classification.

## Decision

We will build a small bioinformatics workflow platform focused on running, tracking, and reporting reproducible sequencing quality-control workflows.

The initial workflow will prioritize a simple and understandable use case over biological complexity.

## Alternatives considered

### Build a clinical variant interpretation app

Rejected for MVP. Clinical interpretation requires strong domain expertise, validated reference data, regulatory awareness, and careful handling of medical claims.

### Build a generic CRUD dashboard

Rejected. It would be too close to standard web development and would not demonstrate meaningful understanding of bioinformatics workflows.

### Build a small workflow platform around sequencing QC

Accepted. It is realistic, focused, technically relevant, and aligned with bioinformatics platform/data engineering roles.

## Consequences

- The project has a clear and honest technical scope.
- The MVP can demonstrate reproducibility, workflow tracking, reporting, and platform design without overclaiming biological or clinical expertise.
- The first workflow can stay simple while leaving room for future extensions such as alignment, variant calling, cloud execution, or more advanced reporting.
- The project can be discussed in interviews as a platform-engineering portfolio project applied to bioinformatics workflows.

## Sources

- Nextflow describes itself as enabling scalable, reproducible and portable scientific workflows: https://www.nextflow.io/
- nf-core describes pipelines as end-to-end analysis workflows that combine tools and processes to analyze biological data: https://nf-co.re/docs/specifications/pipelines/overview
