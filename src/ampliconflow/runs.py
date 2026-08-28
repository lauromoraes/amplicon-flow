"""Run ownership and temporary lifecycle, independent of scientific tools."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from .paths import RunPaths, owned_child


@dataclass(frozen=True)
class RunTemporary:
    root: Path
    owner: str
    run_root: Path

    def cleanup(self) -> None:
        if self.root.is_symlink() or self.root.resolve() != self.root:
            raise ValueError("Temporary directory ownership changed; refusing cleanup")
        marker = self.root / ".ampliconflow-owner.json"
        if marker.is_symlink() or json.loads(marker.read_text()) != {
            "owner": self.owner,
            "run_root": str(self.run_root),
        }:
            raise ValueError("Temporary directory ownership mismatch; refusing cleanup")
        shutil.rmtree(self.root)


def reserve_temporary(base: Path, experiment: str, paths: RunPaths) -> RunTemporary:
    base = base.expanduser().resolve()
    experiments = paths.root.parents[2]
    if base == experiments or base in experiments.parents or experiments in base.parents:
        raise ValueError("Temporary storage must not overlap experiment output storage")
    base.mkdir(parents=True, exist_ok=True)
    study = owned_child(base, experiment)
    root = owned_child(study, paths.run_id, exclusive=True)
    temporary = RunTemporary(root, uuid4().hex, paths.root)
    with (root / ".ampliconflow-owner.json").open("x", encoding="utf-8") as handle:
        json.dump({"owner": temporary.owner, "run_root": str(paths.root)}, handle)
    for name in ("qiime2", "joblib", "qiime2-cache"):
        owned_child(root, name, exclusive=True)
    return temporary
