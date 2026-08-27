from __future__ import annotations

import os
import tempfile
from pathlib import Path


def configure_temp_environment(base_dir: str | Path) -> dict[str, Path]:
    base = Path(base_dir).expanduser().resolve()
    paths = {
        "tmp": base / "qiime2",
        "joblib": base / "joblib",
        "qiime_cache": base / "qiime2-cache",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    os.environ["TMPDIR"] = str(paths["tmp"])
    os.environ["TMP"] = str(paths["tmp"])
    os.environ["TEMP"] = str(paths["tmp"])
    os.environ["JOBLIB_TEMP_FOLDER"] = str(paths["joblib"])
    os.environ["QIIME_CACHE"] = str(paths["qiime_cache"])
    tempfile.tempdir = str(paths["tmp"])
    return paths
