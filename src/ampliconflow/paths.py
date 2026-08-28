from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class RunPaths:
    run_id: str
    root: Path
    parameters: Path
    provenance: Path
    notebooks: Path
    artifacts: Path
    figures: Path
    reports: Path


def validate_identifier(value: str) -> str:
    if value in {".", ".."} or not re.fullmatch(r"[A-Za-z0-9._-]+", value):
        raise ValueError(f"Unsafe experiment/run identifier: {value!r}")
    return value


def owned_child(parent: Path, name: str, *, exclusive: bool = False) -> Path:
    """Create a direct directory without following an existing child symlink."""
    validate_identifier(name)
    child = parent / name
    if child.is_symlink() or child.resolve().parent != parent.resolve():
        raise ValueError(f"Unsafe directory: {child}")
    child.mkdir(exist_ok=not exclusive)
    return child


def create_run_paths(project_dir, experiment, run_id=None) -> RunPaths:
    validate_identifier(experiment)
    run_id = validate_identifier(
        run_id
        if run_id is not None
        else datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ-") + uuid4().hex
    )
    project = Path(project_dir).expanduser().resolve(strict=True)
    experiments = owned_child(project, "experiments")
    study = owned_child(experiments, experiment)
    runs = owned_child(study, "runs")
    root = owned_child(runs, run_id, exclusive=True)
    paths = RunPaths(
        run_id,
        root,
        root / "parameters",
        root / "provenance",
        root / "notebooks",
        root / "artifacts",
        root / "figures",
        root / "reports",
    )
    for name in ("parameters", "provenance", "notebooks", "artifacts", "figures", "reports"):
        owned_child(root, name, exclusive=True)
    return paths
