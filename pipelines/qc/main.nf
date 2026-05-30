nextflow.enable.dsl = 2

workflow {
    def selected_samplesheet = params.input ?: params.samplesheet

    Channel
        .fromPath(selected_samplesheet, checkIfExists: true)
        .splitCsv(header: true)
        .map { row -> tuple(row.sample, file(row.fastq)) }
        .set { reads_ch }

    FASTQC(reads_ch)

    FASTQC.out
        .map { sample, zip_file, html_file -> zip_file }
        .collect()
        .set { fastqc_archives_ch }

    MULTIQC(fastqc_archives_ch)
}

process FASTQC {
    tag "$sample"
    publishDir "${params.outdir}/fastqc", mode: "copy"

    input:
    tuple val(sample), path(fastq)

    output:
    tuple val(sample), path("*_fastqc.zip"), path("*_fastqc.html")

    script:
    """
    fastqc --quiet --threads ${task.cpus} --outdir . ${fastq}
    """
}

process MULTIQC {
    publishDir "${params.outdir}/multiqc", mode: "copy"

    input:
    path fastqc_archives

    output:
    path "multiqc_report.html"
    path "multiqc_data"

    script:
    """
    multiqc --force --outdir . .
    """
}
