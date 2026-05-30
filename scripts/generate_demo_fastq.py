from __future__ import annotations

import argparse
import csv
import random
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTDIR = REPO_ROOT / "pipelines" / "qc" / "demo_data"
DEFAULT_READS = 10_000
DEFAULT_LENGTH = 100
DEFAULT_SEED = 42

BASES = ("A", "C", "G", "T")
ILLUMINA_ADAPTER = "AGATCGGAAGAGCACACGTCTGAACTCCAGTCA"


@dataclass(frozen=True)
class SampleSpec:
    name: str
    behavior: str


@dataclass(frozen=True)
class GeneratedDemoData:
    fastq_paths: list[Path]
    samplesheet_path: Path


SAMPLES = (
    SampleSpec("sample_good", "balanced_high_quality"),
    SampleSpec("sample_low_quality", "declining_quality"),
    SampleSpec("sample_gc_bias", "gc_bias"),
    SampleSpec("sample_duplicates", "duplicates"),
    SampleSpec("sample_adapter_contamination", "adapter_contamination"),
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate deterministic synthetic FASTQ data for demo QC reports.",
    )
    parser.add_argument(
        "--reads",
        type=positive_int,
        default=DEFAULT_READS,
        help=f"Reads per sample. Default: {DEFAULT_READS}",
    )
    parser.add_argument(
        "--length",
        type=positive_int,
        default=DEFAULT_LENGTH,
        help=f"Read length in bases. Default: {DEFAULT_LENGTH}",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=DEFAULT_OUTDIR,
        help=f"Directory for generated FASTQ files. Default: {DEFAULT_OUTDIR}",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Random seed for deterministic output. Default: {DEFAULT_SEED}",
    )
    return parser.parse_args(argv)


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def generate_demo_fastq(
    reads: int = DEFAULT_READS,
    length: int = DEFAULT_LENGTH,
    outdir: Path = DEFAULT_OUTDIR,
    seed: int = DEFAULT_SEED,
) -> GeneratedDemoData:
    outdir = outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    fastq_paths: list[Path] = []
    for sample_index, sample in enumerate(SAMPLES):
        fastq_path = outdir / f"{sample.name}.fastq"
        sample_seed = seed + (sample_index * 10_003)
        write_fastq(
            fastq_path=fastq_path,
            sample=sample,
            reads=reads,
            length=length,
            seed=sample_seed,
        )
        fastq_paths.append(fastq_path)

    samplesheet_path = outdir.parent / "samplesheet.demo.csv"
    write_samplesheet(samplesheet_path, fastq_paths)
    return GeneratedDemoData(fastq_paths=fastq_paths, samplesheet_path=samplesheet_path)


def write_fastq(
    fastq_path: Path,
    sample: SampleSpec,
    reads: int,
    length: int,
    seed: int,
) -> None:
    rng = random.Random(seed)
    duplicate_templates = [
        random_sequence(rng, length, weights=(0.25, 0.25, 0.25, 0.25))
        for _ in range(max(1, min(25, reads // 100)))
    ]

    with fastq_path.open("w", encoding="utf-8", newline="\n") as handle:
        for read_index in range(reads):
            sequence = sequence_for_sample(
                sample=sample,
                length=length,
                rng=rng,
                duplicate_templates=duplicate_templates,
            )
            quality = quality_for_sample(sample=sample, length=length, rng=rng)
            handle.write(f"@{sample.name}_{read_index:06d}\n")
            handle.write(f"{sequence}\n")
            handle.write("+\n")
            handle.write(f"{quality}\n")


def sequence_for_sample(
    sample: SampleSpec,
    length: int,
    rng: random.Random,
    duplicate_templates: Sequence[str],
) -> str:
    if sample.behavior == "gc_bias":
        return random_sequence(rng, length, weights=(0.05, 0.45, 0.45, 0.05))

    if sample.behavior == "duplicates" and rng.random() < 0.9:
        return duplicate_templates[rng.randrange(len(duplicate_templates))]

    if sample.behavior == "adapter_contamination" and rng.random() < 0.65:
        adapter = ILLUMINA_ADAPTER[: min(length, len(ILLUMINA_ADAPTER))]
        insert_length = length - len(adapter)
        insert = random_sequence(rng, insert_length, weights=(0.25, 0.25, 0.25, 0.25))
        return insert + adapter

    return random_sequence(rng, length, weights=(0.25, 0.25, 0.25, 0.25))


def quality_for_sample(sample: SampleSpec, length: int, rng: random.Random) -> str:
    if sample.behavior == "declining_quality":
        return declining_quality(length, rng)

    if sample.behavior == "adapter_contamination":
        return quality_string(rng, length, low=30, high=38)

    return quality_string(rng, length, low=36, high=40)


def random_sequence(
    rng: random.Random,
    length: int,
    weights: tuple[float, float, float, float],
) -> str:
    return "".join(rng.choices(BASES, weights=weights, k=length))


def quality_string(rng: random.Random, length: int, low: int, high: int) -> str:
    return "".join(phred_char(rng.randint(low, high)) for _ in range(length))


def declining_quality(length: int, rng: random.Random) -> str:
    if length == 1:
        return phred_char(20)

    scores: list[str] = []
    for index in range(length):
        fraction = index / (length - 1)
        score = round(38 - (30 * fraction)) + rng.randint(-2, 2)
        scores.append(phred_char(max(5, min(40, score))))
    return "".join(scores)


def phred_char(score: int) -> str:
    return chr(score + 33)


def write_samplesheet(samplesheet_path: Path, fastq_paths: Sequence[Path]) -> None:
    with samplesheet_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["sample", "fastq"])
        for fastq_path in fastq_paths:
            writer.writerow([fastq_path.stem, path_for_samplesheet(fastq_path)])


def path_for_samplesheet(path: Path) -> str:
    resolved_path = path.resolve()
    cwd = Path.cwd().resolve()
    if resolved_path.is_relative_to(cwd):
        return resolved_path.relative_to(cwd).as_posix()
    return resolved_path.as_posix()


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result = generate_demo_fastq(
        reads=args.reads,
        length=args.length,
        outdir=args.outdir,
        seed=args.seed,
    )

    print(f"Wrote {len(result.fastq_paths)} FASTQ files to {args.outdir}")
    print(f"Wrote samplesheet to {result.samplesheet_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
