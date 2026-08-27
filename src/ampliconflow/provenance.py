from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
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
) -> dict[str, Any]:
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
        "git_commit": _command_output(["git", "rev-parse", "HEAD"]),
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

    path.write_text(
        json.dumps(info, indent=2) + "\n",
        encoding="utf-8",
    )
