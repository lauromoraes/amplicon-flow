import csv
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
from uuid import uuid4

import pytest
import yaml

from ampliconflow import reference_data


def source(path, role, name=None, **extra):
    return {
        "role": role,
        "name": name or path.name,
        "url": f"https://fixture.invalid/{name or path.name}",
        "size_bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        **extra,
    }


def registry(path, dataset):
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "verified_on": "2026-08-28",
                "distribution": {"license": "BSD-3-Clause"},
                "datasets": [dataset],
            }
        ),
        encoding="utf-8",
    )


def local_download(files):
    def download(source_record, target):
        shutil.copyfile(files[source_record["name"]], target)

    return download


def read_tsv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.reader(handle, delimiter="\t"))


def test_acquire_pd_mice_normalizes_and_publishes_atomically(tmp_path, monkeypatch):
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    archive = fixture / "seqs.zip"
    names = ["one_1_L001_R1_001.fastq.gz", "two_2_L001_R1_001.fastq.gz"]
    with zipfile.ZipFile(archive, "w") as bundle:
        for name in names:
            bundle.writestr(f"demultiplexed_seqs/{name}", name.encode())
    metadata = fixture / "metadata-source.tsv"
    metadata.write_text(
        "sample_name\tgroup\n#q2:types\tcategorical\none\ta\ntwo\tb\n", encoding="utf-8"
    )
    manifest = fixture / "manifest-source.tsv"
    manifest.write_text(
        "sample-id\tabsolute-filepath\n"
        f"one\t$PWD/demultiplexed_seqs/{names[0]}\n"
        f"two\t$PWD/demultiplexed_seqs/{names[1]}\n",
        encoding="utf-8",
    )
    files = {"demultiplexed_seqs.zip": archive, "sample_metadata.tsv": metadata,
             "manifest.tsv": manifest}
    dataset = {
        "id": "pd-mice-2024.10", "sample_count": 2,
        "files": [
            source(archive, "sequences_archive", "demultiplexed_seqs.zip"),
            source(metadata, "metadata_source", "sample_metadata.tsv"),
            source(manifest, "manifest_source", "manifest.tsv"),
        ],
    }
    registry_path = tmp_path / "registry.yaml"
    registry(registry_path, dataset)
    monkeypatch.setattr(reference_data, "_download", local_download(files))

    destination = tmp_path / "ready/pd-mice"
    result = reference_data.acquire_reference_dataset(registry_path, dataset["id"], destination)

    assert result == destination
    assert read_tsv(result / "metadata.tsv")[0][0] == "sample-id"
    normalized = read_tsv(result / "manifest.tsv")
    assert [row[0] for row in normalized[1:]] == ["one", "two"]
    assert all(Path(row[1]).is_absolute() and Path(row[1]).is_file() for row in normalized[1:])
    report = json.loads((result / "acquisition.json").read_text())
    assert report["dataset_id"] == dataset["id"]
    assert report["inventory"]
    assert not list(result.parent.glob(".*.staging-*"))
    with pytest.raises(FileExistsError):
        reference_data.acquire_reference_dataset(registry_path, dataset["id"], destination)


def test_acquire_atacama_exports_pairs_and_subsets_metadata(tmp_path, monkeypatch):
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    artifact = fixture / "demux.qza"
    identifier = str(uuid4())
    with zipfile.ZipFile(artifact, "w") as bundle:
        bundle.writestr(
            f"{identifier}/metadata.yaml",
            f"uuid: {identifier}\ntype: SampleData[PairedEndSequencesWithQuality]\n"
            "format: SingleLanePerSamplePairedEndFastqDirFmt\n",
        )
        for sample, index in (("one", 1), ("two", 2)):
            for direction in (1, 2):
                bundle.writestr(
                    f"{identifier}/data/{sample}_{index}_L001_R{direction}_001.fastq.gz",
                    f"{sample}-{direction}".encode(),
                )
    metadata = fixture / "metadata-source.tsv"
    metadata.write_text(
        "sample-id\tgroup\n#q2:types\tcategorical\none\ta\ntwo\tb\nunused\tc\n",
        encoding="utf-8",
    )
    artifact_source = source(
        artifact, "demultiplexed_sequences", "demux.qza",
        semantic_type="SampleData[PairedEndSequencesWithQuality]",
    )
    files = {"demux.qza": artifact, "sample_metadata.tsv": metadata}
    dataset = {
        "id": "atacama-demux-2024.10", "sample_count": 2,
        "files": [artifact_source, source(metadata, "metadata_source", "sample_metadata.tsv")],
    }
    registry_path = tmp_path / "registry.yaml"
    registry(registry_path, dataset)
    monkeypatch.setattr(reference_data, "_download", local_download(files))

    result = reference_data.acquire_reference_dataset(
        registry_path, dataset["id"], tmp_path / "ready/atacama"
    )

    manifest = read_tsv(result / "manifest.tsv")
    assert len(manifest) == 3
    assert all(Path(value).is_file() for row in manifest[1:] for value in row[1:])
    assert [row[0] for row in read_tsv(result / "metadata.tsv")[2:]] == ["one", "two"]
    assert (result / "sources/demux.qza").is_file()


def test_archive_traversal_is_rejected(tmp_path):
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("../escape.fastq.gz", b"payload")

    with pytest.raises(reference_data.AcquisitionError, match="Unsafe archive path"):
        reference_data._extract_members(archive, tmp_path / "output")
    assert not (tmp_path / "escape.fastq.gz").exists()


def test_download_postcondition_removes_failed_staging(tmp_path, monkeypatch):
    payload = tmp_path / "payload"
    payload.write_bytes(b"wrong")
    dataset = {
        "id": "pd-mice-2024.10", "sample_count": 1,
        "files": [{
            "role": "sequences_archive", "name": "demultiplexed_seqs.zip",
            "url": "https://fixture.invalid/data", "size_bytes": 999, "sha256": "0" * 64,
        }],
    }
    registry_path = tmp_path / "registry.yaml"
    registry(registry_path, dataset)
    monkeypatch.setattr(
        reference_data, "_download", lambda _source, target: shutil.copyfile(payload, target)
    )
    destination = tmp_path / "ready/dataset"

    with pytest.raises(reference_data.AcquisitionError, match="size mismatch"):
        reference_data.acquire_reference_dataset(registry_path, dataset["id"], destination)
    assert not destination.exists()
    assert not list(destination.parent.glob(".*.staging-*"))
