"""Read-only readiness checks. No notebooks, installation, downloads, or run allocation."""

from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from uuid import UUID

import nbformat
import yaml

from .planning import PlanningError, build_plan
from .provenance import sha256_file


class PreflightError(ValueError):
    def __init__(self, report):
        self.report = report
        super().__init__(
            "Preflight failed:\n"
            + "\n".join(f"  [{item['code']}] {item['message']}" for item in report["errors"])
        )


def readable_file(path):
    path = Path(path)
    if not path.is_file() or not os.access(path, os.R_OK) or not path.stat().st_size:
        raise ValueError("Expected a readable, nonempty regular file")
    return path


def inspect_artifact(path, expected_type, expected_sha256=None):
    """Check checksum and archive identity/type; not full QIIME data validation."""
    path = readable_file(path)
    before = path.stat()
    digest = sha256_file(path)
    if expected_sha256 and digest != expected_sha256:
        raise ValueError("Artifact SHA-256 mismatch")
    with zipfile.ZipFile(path) as archive:
        metadata = [
            n for n in archive.namelist() if n.count("/") == 1 and n.endswith("/metadata.yaml")
        ]
        if len(metadata) != 1:
            raise ValueError("Expected one QIIME artifact metadata record")
        name = metadata[0]
        identifier = str(UUID(name.split("/")[0]))
        if archive.getinfo(name).file_size > 65536:
            raise ValueError("Artifact metadata exceeds the supported size")
        record = yaml.safe_load(archive.read(name))
        if not isinstance(record, dict) or record.get("uuid") != identifier:
            raise ValueError("Artifact UUID does not match its archive")
        if record.get("type") != expected_type:
            raise ValueError(f"Artifact must have semantic type {expected_type}")
        if not record.get("format"):
            raise ValueError("Expected a data artifact, not a visualization")
    after = path.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise ValueError("Artifact changed while being inspected")
    return {"sha256": digest, "uuid": identifier, "type": record["type"]}


def metadata_samples(path):
    with readable_file(path).open(encoding="utf-8-sig", newline="") as handle:
        rows = csv.reader(handle, delimiter="\t")
        header = next(rows, [])
        if not header or header[0].lower() not in (
            "sample-id",
            "sampleid",
            "sample id",
            "#sampleid",
            "#sample id",
            "id",
            "#id",
        ):
            raise ValueError("Metadata must be TSV with a QIIME sample-ID header")
        if len(set(header)) != len(header) or any(not value.strip() for value in header):
            raise ValueError("Metadata column names must be nonempty and unique")
        samples = set()
        for row in rows:
            if not row or row[0].startswith("#"):
                continue
            if len(row) != len(header) or not row[0].strip() or row[0] in samples:
                raise ValueError("Metadata contains malformed rows or empty/duplicate sample IDs")
            samples.add(row[0])
        if not samples:
            raise ValueError("Metadata contains no samples")
        return samples


def manifest_samples(path, layout):
    """Support V1 CSV and V2 TSV, requiring literal absolute FASTQ paths."""
    with readable_file(path).open(encoding="utf-8-sig", newline="") as handle:
        first = handle.readline()
        handle.seek(0)
        reader = csv.DictReader(handle, delimiter="\t" if "\t" in first else ",")
        header = reader.fieldnames
        v1 = header == ["sample-id", "absolute-filepath", "direction"]
        expected = (
            ["sample-id", "absolute-filepath"]
            if layout == "single-end"
            else ["sample-id", "forward-absolute-filepath", "reverse-absolute-filepath"]
        )
        if not v1 and header != expected:
            raise ValueError("Manifest columns do not match the sequencing layout (V1/V2)")
        samples, files = {}, set()
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError("Malformed manifest row")
            sample = row["sample-id"]
            if not sample.strip():
                raise ValueError("Manifest has an empty sample ID")
            if v1:
                reads = [(row["direction"], row["absolute-filepath"])]
            elif layout == "single-end":
                reads = [("forward", row["absolute-filepath"])]
            else:
                reads = [(d, row[f"{d}-absolute-filepath"]) for d in ("forward", "reverse")]
            for direction, raw in reads:
                directions = samples.setdefault(sample, set())
                if direction not in ("forward", "reverse") or direction in directions:
                    raise ValueError("Manifest has invalid or duplicate read directions")
                path = Path(raw)
                if not path.is_absolute():
                    raise ValueError("Manifest FASTQ paths must be literal absolute paths")
                resolved = readable_file(path).resolve()
                identity = (resolved.stat().st_dev, resolved.stat().st_ino)
                if identity in files:
                    raise ValueError("Manifest reuses a FASTQ file for multiple entries")
                files.add(identity)
                directions.add(direction)
        wanted = {"forward"} if layout == "single-end" else {"forward", "reverse"}
        if not samples or any(directions != wanted for directions in samples.values()):
            raise ValueError("Manifest has missing reads or inconsistent pairing")
        return set(samples)


def probe_environment(needs_dada2):
    # Probe imports and the actual kernel interpreter in the activated environment.
    # Fixed source only: no commands from YAML are executed.
    code = """
import json, pathlib, sys
import papermill, ipykernel, qiime2
from jupyter_client.kernelspec import KernelSpecManager
from qiime2.sdk import PluginManager
kernel = KernelSpecManager().get_kernel_spec('python3')
if pathlib.Path(kernel.argv[0]).resolve() != pathlib.Path(sys.executable).resolve():
    raise ValueError('python3 kernel does not use the activated Python interpreter')
plugins = PluginManager().plugins
if sys.argv[1] == 'yes' and 'dada2' not in plugins:
    raise ValueError('QIIME dada2 plugin is unavailable')
print(json.dumps({'python': sys.version.split()[0], 'executable': sys.executable,
 'qiime2': qiime2.__version__, 'papermill': papermill.__version__,
 'kernel': 'python3', 'dada2': 'dada2' in plugins}))
"""
    try:
        result = subprocess.run(
            [sys.executable, "-c", code, "yes" if needs_dada2 else "no"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        return json.loads(result.stdout)
    except (subprocess.SubprocessError, OSError, ValueError) as error:
        raise ValueError(
            "Active environment needs importable Papermill, ipykernel, QIIME 2, a python3 "
            "kernel using this interpreter, and DADA2 when QC is selected"
        ) from error


def check_storage(path, minimum):
    path = Path(path).absolute()
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink():
            raise ValueError("Output/temporary ancestors must not be symlinks")
    existing = path
    while not existing.exists():
        existing = existing.parent
    if not existing.is_dir() or not os.access(existing, os.W_OK | os.X_OK):
        raise ValueError("Storage ancestor is not a writable/searchable directory")
    free = shutil.disk_usage(existing).free
    if free < minimum:
        raise ValueError("Storage has less than resources.min_free_bytes available")
    return {"path": str(path), "free_bytes": free}


def preflight(parameters, project, *, temp_base=None):
    project = Path(project).resolve()
    report = {"ok": False, "errors": [], "warnings": [], "plan": None, "checks": {}}

    def check(code, function):
        try:
            return function()
        except (
            ValueError,
            OSError,
            csv.Error,
            nbformat.ValidationError,
            zipfile.BadZipFile,
            yaml.YAMLError,
        ) as error:
            report["errors"].append({"code": code, "message": str(error)})
            return None

    try:
        plan = build_plan(parameters)
    except PlanningError as error:
        report["errors"].append({"code": error.code, "message": str(error)})
        return report
    report["plan"] = plan
    samples = check("metadata", lambda: metadata_samples(parameters["inputs"]["metadata_file"]))
    if samples is not None:
        report["checks"]["metadata_sample_count"] = len(samples)
    if "prepare-data" in [step["id"] for step in plan["steps"]]:
        manifest = parameters["inputs"].get("manifest_file")
        if not manifest:
            report["errors"].append(
                {"code": "manifest", "message": "Prepare Data needs manifest_file"}
            )
        else:
            reads = check(
                "manifest",
                lambda: manifest_samples(manifest, parameters["sequencing"]["read_layout"]),
            )
            if reads is not None and samples is not None and reads != samples:
                report["errors"].append(
                    {
                        "code": "sample_mismatch",
                        "message": "Manifest and metadata sample sets differ",
                    }
                )
    external_checks = {}
    for step in plan["steps"]:
        template = project / "notebooks/templates" / step["template"]

        def check_notebook(template=template):
            notebook = nbformat.read(readable_file(template), as_version=4)
            nbformat.validate(notebook)
            cells = [c for c in notebook.cells if "parameters" in c.metadata.get("tags", [])]
            if len(cells) != 1 or cells[0].cell_type != "code":
                raise ValueError("Notebook must have exactly one parameters code cell")

        check(f"template:{step['id']}", check_notebook)
        for role, binding in step["inputs"].items():
            if binding["source"] == "external":
                result = check(
                    f"artifact:{role}",
                    lambda binding=binding: inspect_artifact(
                        binding["path"], binding["type"], binding["sha256"]
                    ),
                )
                if result:
                    external_checks[role] = result
    report["checks"]["external_artifacts"] = external_checks
    report["checks"]["environment"] = check(
        "environment",
        lambda: probe_environment(any(step["id"] == "quality-control" for step in plan["steps"])),
    )
    outputs = project / "experiments"
    temporary = Path(temp_base or os.environ.get("AMPLICONFLOW_TEMP_DIR", project / ".tmp"))
    temporary = temporary.expanduser().absolute()
    if (
        temporary.resolve() == outputs
        or outputs in temporary.resolve().parents
        or temporary.resolve() in outputs.parents
    ):
        report["errors"].append({"code": "storage_overlap", "message": "Output/temp roots overlap"})
    minimum = parameters.get("resources", {}).get("min_free_bytes", 0)
    for name, path in (
        ("outputs", outputs / parameters["experiment_name"] / "runs"),
        ("temporary", temporary / parameters["experiment_name"]),
    ):
        report["checks"][name] = check(
            f"storage:{name}", lambda path=path: check_storage(path, minimum)
        )
    report["warnings"].extend(
        [
            {
                "code": "structural_only",
                "message": "FASTQ contents and QIIME payloads are not scientifically validated",
            },
            {
                "code": "space_estimate",
                "message": "Free space and permissions are advisory snapshots, not reservations",
            },
        ]
    )
    if external_checks:
        report["warnings"].append(
            {
                "code": "artifact_samples",
                "message": "External artifact sample IDs are not compared with metadata yet",
            }
        )
    report["ok"] = not report["errors"]
    return report


def require_preflight(parameters, project, *, temp_base=None):
    report = preflight(parameters, project, temp_base=temp_base)
    if not report["ok"]:
        raise PreflightError(report)
    return report


def verify_bindings(bindings, run_root):
    """Recheck consumers and validate producer archive contracts before marking success."""
    result = {}
    for role, binding in bindings.items():
        path = Path(binding["path"])
        if binding.get("source") != "external":
            path = run_root / path
            if not path.resolve().is_relative_to(run_root.resolve()):
                raise ValueError("Produced artifact escapes its run directory")
        result[role] = inspect_artifact(path, binding["type"], binding.get("sha256"))
    return result
