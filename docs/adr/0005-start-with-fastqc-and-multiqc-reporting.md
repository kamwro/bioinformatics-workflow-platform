# ADR-0005: Start with FastQC and MultiQC reporting

## Status

Accepted

## Date

2026-05-09

## Context

The first workflow should be biologically relevant but not too complex. Raw sequencing quality control is a good initial use case because it is common, understandable, and avoids clinical interpretation.

The platform should expose a meaningful report to the user rather than only raw logs or command output.

## Decision

The first pipeline will run **FastQC** on FASTQ files and then aggregate the outputs with **MultiQC**.

The platform API and dashboard will expose the generated MultiQC HTML report and selected metadata from the workflow run.

## Alternatives considered

### Custom React charts

Rejected for MVP. Custom charts would demonstrate frontend skills but would be less recognizable as a bioinformatics workflow output.

### Raw FastQC reports only

Viable but weaker. FastQC creates useful per-sample reports, but MultiQC gives a better multi-sample overview and is easier to present through the platform.

### Jupyter Notebook / Quarto report

Viable for exploratory analysis, but less ideal for an automated workflow platform MVP.

### Variant calling report

Deferred. Variant calling is a more complex second-stage workflow and requires more biological and tooling context.

## Consequences

- The MVP has a clear and recognizable bioinformatics output.
- The project can run on small test FASTQ files.
- MultiQC gives the dashboard a useful artifact without building custom visualization logic.
- Future workflows can reuse the same reporting pattern.

## Sources

- FastQC official page describes FastQC as a quality-control tool for high-throughput sequencing data: https://www.bioinformatics.babraham.ac.uk/projects/fastqc/
- MultiQC GitHub describes MultiQC as a tool that creates a single report with interactive plots for multiple bioinformatics analyses across many samples: https://github.com/MultiQC/MultiQC
- Seqera MultiQC page describes support for many common bioinformatics tools, including FastQC: https://seqera.io/multiqc/
- MultiQC publication: https://pmc.ncbi.nlm.nih.gov/articles/PMC5039924/
