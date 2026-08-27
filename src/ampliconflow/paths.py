from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExperimentPaths:
    root: Path
    parameters: Path
    provenance: Path
    notebooks: Path
    artifacts: Path
    figures: Path
    reports: Path


def create_experiment_paths(project_dir, experiment):
    root = Path(project_dir).resolve() / "experiments" / experiment
    paths = ExperimentPaths(
        root,
        root / "parameters",
        root / "provenance",
        root / "notebooks",
        root / "artifacts",
        root / "figures",
        root / "reports",
    )
    for p in paths.__dict__.values():
        p.mkdir(parents=True, exist_ok=True)
    return paths
