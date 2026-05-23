# ADR-0002: Use Nextflow DSL2 as the workflow engine

## Status

Accepted

## Date

2026-05-09

## Context

Bioinformatics workflows should be reproducible, modular, and portable across local, HPC, and cloud execution environments.

A custom scheduler built in Python or TypeScript would add complexity and would not reflect how many real bioinformatics teams structure workflow execution.

There is also a possible question about Viash / VDSL3. VDSL3 is useful to know about, but it is a Viash abstraction layer on top of Nextflow rather than the mainstream baseline syntax expected in most Nextflow projects.

## Decision

We will use **standard Nextflow DSL2** for the MVP workflow.

We will not use Viash / VDSL3 in the first implementation. VDSL3 can be evaluated later as a separate ADR if the project grows toward reusable module generation.

## Alternatives considered

### Custom Python orchestration

Rejected. It would hide the bioinformatics workflow-engineering skill that the project should demonstrate.

### Snakemake

Viable alternative. It is widely used in bioinformatics, but for this project we choose Nextflow because it is strongly associated with portable, scalable workflow execution and cloud/HPC deployment patterns.

### Viash / VDSL3

Deferred. It offers useful abstractions such as standardized module interfaces, generated documentation, reduced Groovy usage, and standalone modules. However, it adds another toolchain and may make the MVP harder to evaluate for reviewers expecting standard Nextflow DSL2.

## Consequences

- The project shows direct familiarity with modern Nextflow.
- The workflow can later be extended toward cloud executors such as AWS Batch.
- The author must learn Nextflow concepts directly: processes, channels, workflow blocks, modules, inputs, outputs, and configuration.
- VDSL3 remains a possible future improvement, not an MVP dependency.

## Sources

- Nextflow main documentation: https://www.nextflow.io/
- Nextflow DSL1 migration notes state that DSL2 became the default and DSL1 support was removed: https://github.com/nextflow-io/nextflow/blob/master/docs/migrations/dsl1.md
- Nextflow training explains that modern Nextflow code uses DSL2 and describes the DSL2 migration: https://training.nextflow.io/3.2/ca/info/nxf_versions/
- Viash documentation describes VDSL3 as a separate DSL layer on top of Nextflow enabled by Viash: https://viash.io/guide/nextflow_vdsl3/
