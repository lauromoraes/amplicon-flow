from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _command_output(
    command: list[str],
) -> str | None:
    try:
        return subprocess.check_output(
            command,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()

    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
    ):
        return None


def sha256_file(
    path: str | Path,
) -> str:
    digest = hashlib.sha256()

    with Path(path).open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def collect_run_info(
    *,
    experiment: str,
    parameters_file: str | Path,
    status: str,
    project_dir: str | Path | None = None,
) -> dict[str, Any]:
    git = ["git", "-C", str(Path(project_dir or ".").resolve())]
    return {
        "experiment": experiment,
        "status": status,
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "host": platform.node(),
        "python": sys.version.split()[0],
        "qiime2": _command_output(["qiime", "--version"]),
        "papermill": _command_output(
            [
                sys.executable,
                "-c",
                ("import papermill; print(papermill.__version__)"),
            ]
        ),
        "git_commit": _command_output([*git, "rev-parse", "HEAD"]),
        "git_status": _command_output([*git, "status", "--short"]),
        "parameters_file": str(Path(parameters_file).resolve()),
        "parameters_sha256": sha256_file(parameters_file),
        "environment": {
            "CONDA_DEFAULT_ENV": os.getenv("CONDA_DEFAULT_ENV"),
            "TMPDIR": os.getenv("TMPDIR"),
            "JOBLIB_TEMP_FOLDER": os.getenv("JOBLIB_TEMP_FOLDER"),
            "QIIME_CACHE": os.getenv("QIIME_CACHE"),
        },
    }


def write_run_info(
    path: str | Path,
    info: dict[str, Any],
) -> None:
    path = Path(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Atomic replacement keeps readers from observing a partially written status.
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as fh:
        temporary = Path(fh.name)
        try:
            fh.write(json.dumps(info, indent=2) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
