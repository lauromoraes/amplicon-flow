"""Validate the machine-readable contribution emitted by each analytical notebook."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from .preflight import readable_file


def validate_report_contribution(path, schema_path, *, step, run_id, run_root):
    path = readable_file(path).resolve()
    run_root = Path(run_root).resolve()
    if run_root not in path.parents:
        raise ValueError("Report contribution must be inside the run directory")
    document = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(document),
        key=lambda error: tuple(map(str, error.path)),
    )
    if errors:
        raise ValueError(f"Invalid report contribution: {errors[0].message}")
    if document["step"] != step or document["run_id"] != run_id:
        raise ValueError("Report contribution identity does not match the active step/run")
    for output in document["outputs"].values():
        candidate = Path(output)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError("Report outputs must be safe paths relative to the run directory")
        resolved = (run_root / candidate).resolve()
        if run_root not in resolved.parents:
            raise ValueError(f"Reported output does not exist inside the run: {output}")
        readable_file(resolved)
    return document
