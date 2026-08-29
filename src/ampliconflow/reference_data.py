"""Explicit, checksum-pinned acquisition of scientific acceptance datasets."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import stat
import urllib.parse
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from uuid import uuid4

import yaml

from .preflight import inspect_artifact
from .provenance import sha256_file

MAX_ARCHIVE_ENTRIES = 1000
MAX_ENTRY_BYTES = 512 * 1024 * 1024
MAX_TOTAL_UNPACKED_BYTES = 2 * 1024 * 1024 * 1024
PAIRED_FASTQ = re.compile(
    r"^(?P<sample>.+)_\d+_L\d+_R(?P<direction>[12])_\d+\.fastq\.gz$"
)


class AcquisitionError(ValueError):
    """A source or transformation violated the pinned acquisition contract."""


def load_registry(path):
    registry = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(registry, dict) or registry.get("schema_version") != 1:
        raise AcquisitionError("Unsupported reference dataset registry")
    datasets = registry.get("datasets")
    if not isinstance(datasets, list) or not datasets:
        raise AcquisitionError("Reference dataset registry is empty")
    return registry


def dataset_by_id(registry, dataset_id):
    matches = [item for item in registry["datasets"] if item.get("id") == dataset_id]
    if len(matches) != 1:
        raise AcquisitionError(f"Unknown or duplicate reference dataset: {dataset_id}")
    return matches[0]


def _download(source, target):
    url = source["url"]
    if urllib.parse.urlsplit(url).scheme != "https":
        raise AcquisitionError("Reference dataset sources must use HTTPS")
    request = urllib.request.Request(url, headers={"User-Agent": "AmpliconFlow/2 reference-data"})
    digest = hashlib.sha256()
    size = 0
    try:
        with urllib.request.urlopen(request, timeout=60) as response, target.open("xb") as output:
            if urllib.parse.urlsplit(response.geturl()).scheme != "https":
                raise AcquisitionError("Reference dataset redirect left HTTPS")
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > source["size_bytes"]:
                    raise AcquisitionError(f"Downloaded file exceeds pinned size: {source['name']}")
                digest.update(chunk)
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
    except OSError as error:
        raise AcquisitionError(f"Could not download {source['name']}: {error}") from error
    if size != source["size_bytes"]:
        raise AcquisitionError(f"Downloaded size mismatch: {source['name']}")
    if digest.hexdigest() != source["sha256"]:
        raise AcquisitionError(f"Downloaded SHA-256 mismatch: {source['name']}")


def _verify_source(source, target):
    if target.stat().st_size != source["size_bytes"]:
        raise AcquisitionError(f"Downloaded size mismatch: {source['name']}")
    if sha256_file(target) != source["sha256"]:
        raise AcquisitionError(f"Downloaded SHA-256 mismatch: {source['name']}")


def _safe_member(info, seen):
    path = PurePosixPath(info.filename)
    if path.is_absolute() or not path.parts or any(part in ("", ".", "..") for part in path.parts):
        raise AcquisitionError(f"Unsafe archive path: {info.filename}")
    key = "/".join(path.parts).casefold()
    if key in seen:
        raise AcquisitionError(f"Duplicate archive path: {info.filename}")
    seen.add(key)
    mode = info.external_attr >> 16
    kind = stat.S_IFMT(mode)
    if kind not in (0, stat.S_IFREG, stat.S_IFDIR):
        raise AcquisitionError(f"Archive links or special files are refused: {info.filename}")
    if info.file_size > MAX_ENTRY_BYTES:
        raise AcquisitionError(f"Archive member is too large: {info.filename}")
    return path


def _extract_members(archive_path, destination, select=None, flatten=False):
    destination.mkdir(parents=True, exist_ok=False)
    extracted = []
    seen = set()
    total = 0
    try:
        archive = zipfile.ZipFile(archive_path)
    except zipfile.BadZipFile as error:
        raise AcquisitionError(f"Invalid ZIP archive: {archive_path.name}") from error
    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_ARCHIVE_ENTRIES:
            raise AcquisitionError("Archive contains too many entries")
        for info in infos:
            member = _safe_member(info, seen)
            if info.is_dir() or (select is not None and not select(member)):
                continue
            total += info.file_size
            if total > MAX_TOTAL_UNPACKED_BYTES:
                raise AcquisitionError("Archive expands beyond the safety limit")
            relative = Path(member.name) if flatten else Path(*member.parts)
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                raise AcquisitionError(f"Archive extraction would overwrite: {relative}")
            written = 0
            with archive.open(info) as source, target.open("xb") as output:
                while chunk := source.read(1024 * 1024):
                    written += len(chunk)
                    if written > info.file_size:
                        raise AcquisitionError(f"Archive member exceeded declared size: {relative}")
                    output.write(chunk)
            if written != info.file_size:
                raise AcquisitionError(f"Archive member size mismatch: {relative}")
            extracted.append(target)
    return extracted


def _read_tsv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.reader(handle, delimiter="\t"))


def _write_tsv(path, rows):
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerows(rows)


def _data_rows(rows, label):
    data = [row for row in rows if row and not row[0].startswith("#")]
    if any(not row[0] for row in data):
        raise AcquisitionError(f"Empty sample ID in {label}")
    identifiers = [row[0] for row in data]
    if len(identifiers) != len(set(identifiers)):
        raise AcquisitionError(f"Duplicate sample ID in {label}")
    return data


def _source_by_role(dataset, role):
    matches = [source for source in dataset["files"] if source.get("role") == role]
    if len(matches) != 1:
        raise AcquisitionError(f"Dataset must define exactly one source with role {role}")
    return matches[0]


def _normalize_pd_mice(stage, final_root, dataset):
    sources = stage / "sources"
    inputs = stage / "inputs"
    files = _extract_members(sources / "demultiplexed_seqs.zip", inputs)
    fastqs = {file.name: file for file in files if file.name.endswith(".fastq.gz")}
    if len(fastqs) != dataset["sample_count"]:
        raise AcquisitionError("Parkinson's archive sample count mismatch")

    metadata = _read_tsv(sources / "sample_metadata.tsv")
    if not metadata or metadata[0][0] != "sample_name":
        raise AcquisitionError("Unexpected Parkinson's metadata identifier header")
    metadata[0][0] = "sample-id"
    metadata_rows = _data_rows(metadata[1:], "Parkinson's metadata")
    metadata_ids = {row[0] for row in metadata_rows}

    source_manifest = _read_tsv(sources / "manifest.tsv")
    if not source_manifest or source_manifest[0] != ["sample-id", "absolute-filepath"]:
        raise AcquisitionError("Unexpected Parkinson's manifest header")
    manifest = [source_manifest[0]]
    manifest_ids = set()
    final_fastq_root = final_root / "inputs/demultiplexed_seqs"
    for row in source_manifest[1:]:
        if len(row) != 2 or row[0] in manifest_ids:
            raise AcquisitionError("Malformed or duplicate Parkinson's manifest row")
        filename = PurePosixPath(row[1]).name
        if filename not in fastqs:
            raise AcquisitionError("Parkinson's manifest references a missing FASTQ")
        manifest_ids.add(row[0])
        manifest.append([row[0], str(final_fastq_root / filename)])
    if metadata_ids != manifest_ids or len(manifest_ids) != dataset["sample_count"]:
        raise AcquisitionError("Parkinson's metadata/manifest sample sets differ")
    _write_tsv(stage / "metadata.tsv", metadata)
    _write_tsv(stage / "manifest.tsv", manifest)


def _atacama_fastq_member(path):
    return len(path.parts) == 3 and path.parts[1] == "data" and path.name.endswith(".fastq.gz")


def _normalize_atacama(stage, final_root, dataset):
    sources = stage / "sources"
    artifact_source = _source_by_role(dataset, "demultiplexed_sequences")
    inspect_artifact(
        sources / artifact_source["name"],
        artifact_source["semantic_type"],
        artifact_source["sha256"],
    )
    fastq_root = stage / "inputs/demultiplexed_seqs"
    files = _extract_members(
        sources / artifact_source["name"], fastq_root, select=_atacama_fastq_member, flatten=True
    )
    pairs = {}
    for file in files:
        match = PAIRED_FASTQ.fullmatch(file.name)
        if not match:
            raise AcquisitionError(f"Unexpected Atacama FASTQ filename: {file.name}")
        sample = match.group("sample")
        direction = match.group("direction")
        if direction in pairs.setdefault(sample, {}):
            raise AcquisitionError(f"Duplicate Atacama read direction: {sample}")
        pairs[sample][direction] = file.name
    if len(pairs) != dataset["sample_count"] or any(set(reads) != {"1", "2"} for reads in pairs.values()):
        raise AcquisitionError("Atacama paired sample count or pairing mismatch")

    final_fastq_root = final_root / "inputs/demultiplexed_seqs"
    manifest = [["sample-id", "forward-absolute-filepath", "reverse-absolute-filepath"]]
    for sample in sorted(pairs):
        manifest.append(
            [sample, str(final_fastq_root / pairs[sample]["1"]), str(final_fastq_root / pairs[sample]["2"])]
        )
    _write_tsv(stage / "manifest.tsv", manifest)

    metadata = _read_tsv(sources / "sample_metadata.tsv")
    if not metadata or metadata[0][0] != "sample-id":
        raise AcquisitionError("Unexpected Atacama metadata identifier header")
    types = [row for row in metadata[1:] if row and row[0].startswith("#")]
    metadata_rows = _data_rows(metadata[1:], "Atacama metadata")
    selected = [row for row in metadata_rows if row[0] in pairs]
    if {row[0] for row in selected} != set(pairs):
        raise AcquisitionError("Atacama artifact samples are missing from metadata")
    _write_tsv(stage / "metadata.tsv", [metadata[0], *types, *selected])


NORMALIZERS = {
    "pd-mice-2024.10": _normalize_pd_mice,
    "atacama-demux-2024.10": _normalize_atacama,
}


def _inventory(root):
    return [
        {
            "path": str(path.relative_to(root)),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != "acquisition.json"
    ]


def acquire_reference_dataset(registry_path, dataset_id, destination):
    registry = load_registry(registry_path)
    dataset = dataset_by_id(registry, dataset_id)
    if dataset_id not in NORMALIZERS:
        raise AcquisitionError(f"No normalizer implemented for {dataset_id}")

    requested = Path(destination).expanduser().absolute()
    parent = requested.parent.resolve()
    final_root = parent / requested.name
    if final_root.exists() or final_root.is_symlink():
        raise FileExistsError(f"Destination already exists: {final_root}")
    parent.mkdir(parents=True, exist_ok=True)
    stage = parent / f".{requested.name}.staging-{uuid4().hex}"
    stage.mkdir(exist_ok=False)
    try:
        sources = stage / "sources"
        sources.mkdir()
        for source in dataset["files"]:
            name = source["name"]
            if Path(name).name != name:
                raise AcquisitionError(f"Unsafe registry filename: {name}")
            print(f"Downloading {name}", flush=True)
            _download(source, sources / name)
            _verify_source(source, sources / name)
        NORMALIZERS[dataset_id](stage, final_root, dataset)
        report = {
            "schema_version": 1,
            "dataset_id": dataset_id,
            "registry": str(Path(registry_path).resolve()),
            "registry_verified_on": registry["verified_on"],
            "acquired_at": datetime.now(UTC).isoformat(),
            "destination": str(final_root),
            "inventory": _inventory(stage),
        }
        with (stage / "acquisition.json").open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        stage.rename(final_root)
    except BaseException:
        if stage.exists() and not stage.is_symlink() and stage.parent == parent:
            shutil.rmtree(stage)
        raise
    return final_root
