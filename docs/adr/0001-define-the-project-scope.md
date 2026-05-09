# ADR-0001: Position the project as bioinformatics platform engineering

## Status

Proposed

## Date

2026-05-09

## Context

The project is intended to support a career transition from general software engineering into bioinformatics / life sciences technology.

The goal is not to present the author as a wet-lab scientist or clinical bioinformatician. Instead, the project should demonstrate that software engineering practices can be applied to bioinformatics workflows: reproducible execution, workflow tracking, metadata management, reporting, and platform/API design.

## Decision

We will position the project as a **bioinformatics workflow platform** rather than as a biological interpretation project.

The MVP will focus on running and tracking a simple sequencing quality-control workflow. It will not attempt clinical interpretation, diagnosis, variant pathogenicity classification, or any patient-facing use case.

## Alternatives considered

### Build a clinical variant interpretation app

Rejected for MVP. Clinical interpretation requires strong domain expertise, validated reference data, regulatory awareness, and careful handling of medical claims.

### Build a generic CRUD dashboard

Rejected. It would be too close to standard web development and would not demonstrate meaningful understanding of bioinformatics workflows.

### Build a small workflow platform around sequencing QC

Accepted. It is realistic, safer, and aligned with platform/data engineering roles in bioinformatics.

## Consequences

- The project demonstrates engineering maturity without overclaiming biological expertise.
- The project can be discussed honestly in interviews as a platform-engineering portfolio project.
- The first workflow can stay simple while leaving room for future extensions such as alignment, variant calling, or cloud execution.

## Sources

- Nextflow describes itself as enabling scalable, reproducible and portable scientific workflows: https://www.nextflow.io/
- nf-core describes pipelines as end-to-end analysis workflows that combine tools and processes to analyze biological data: https://nf-co.re/docs/specifications/pipelines/overview
