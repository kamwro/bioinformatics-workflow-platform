import csv
from pathlib import Path

from scripts.generate_demo_fastq import SAMPLES, generate_demo_fastq


def test_generate_demo_fastq_creates_expected_files(tmp_path: Path) -> None:
    result = generate_demo_fastq(
        reads=12,
        length=30,
        outdir=tmp_path / "demo_data",
        seed=123,
    )

    assert len(result.fastq_paths) == len(SAMPLES)
    assert all(path.exists() for path in result.fastq_paths)
    assert result.samplesheet_path.exists()

    with result.samplesheet_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert [row["sample"] for row in rows] == [sample.name for sample in SAMPLES]
    assert {row["fastq"] for row in rows} == {
        path.resolve().as_posix() for path in result.fastq_paths
    }


def test_generated_fastq_records_are_valid(tmp_path: Path) -> None:
    result = generate_demo_fastq(
        reads=6,
        length=25,
        outdir=tmp_path / "demo_data",
        seed=321,
    )

    for fastq_path in result.fastq_paths:
        records = read_fastq_records(fastq_path)

        assert len(records) == 6
        for header, sequence, separator, quality in records:
            assert header.startswith("@")
            assert set(sequence) <= {"A", "C", "G", "T"}
            assert separator == "+"
            assert len(sequence) == 25
            assert len(quality) == 25


def test_duplicate_sample_contains_repeated_sequences(tmp_path: Path) -> None:
    result = generate_demo_fastq(
        reads=20,
        length=40,
        outdir=tmp_path / "demo_data",
        seed=999,
    )
    duplicate_fastq = next(
        path for path in result.fastq_paths if path.stem == "sample_duplicates"
    )
    sequences = [record[1] for record in read_fastq_records(duplicate_fastq)]

    assert len(set(sequences)) < len(sequences)


def test_generator_is_deterministic_for_same_seed(tmp_path: Path) -> None:
    first = generate_demo_fastq(
        reads=4,
        length=20,
        outdir=tmp_path / "first",
        seed=77,
    )
    second = generate_demo_fastq(
        reads=4,
        length=20,
        outdir=tmp_path / "second",
        seed=77,
    )

    first_good = next(path for path in first.fastq_paths if path.stem == "sample_good")
    second_good = next(
        path for path in second.fastq_paths if path.stem == "sample_good"
    )

    assert first_good.read_text(encoding="utf-8") == second_good.read_text(
        encoding="utf-8"
    )


def test_gc_bias_and_low_quality_samples_show_expected_patterns(
    tmp_path: Path,
) -> None:
    result = generate_demo_fastq(
        reads=10,
        length=50,
        outdir=tmp_path / "demo_data",
        seed=555,
    )
    gc_fastq = next(
        path for path in result.fastq_paths if path.stem == "sample_gc_bias"
    )
    low_quality_fastq = next(
        path for path in result.fastq_paths if path.stem == "sample_low_quality"
    )

    gc_sequences = [record[1] for record in read_fastq_records(gc_fastq)]
    gc_fraction = sum(
        base in {"G", "C"} for sequence in gc_sequences for base in sequence
    ) / sum(len(sequence) for sequence in gc_sequences)
    quality = read_fastq_records(low_quality_fastq)[0][3]

    assert gc_fraction > 0.75
    assert phred_score(quality[0]) > phred_score(quality[-1])


def read_fastq_records(path: Path) -> list[tuple[str, str, str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) % 4 == 0
    return [
        (lines[index], lines[index + 1], lines[index + 2], lines[index + 3])
        for index in range(0, len(lines), 4)
    ]


def phred_score(character: str) -> int:
    return ord(character) - 33
