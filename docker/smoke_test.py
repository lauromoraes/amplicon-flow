#!/usr/bin/env python
"""Fail the image build unless its analytical/development runtime is coherent."""

from __future__ import annotations

import json
import sys
from importlib import import_module, metadata

from qiime2.sdk import PluginManager

EXPECTED_DISTRIBUTIONS = (
    "biom-format",
    "biopython",
    "jupyterlab",
    "papermill",
    "statannotations",
)
EXPECTED_PLUGINS = {"dada2", "demux"}


def main():
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError(f"Expected the QIIME 2 Python 3.12 runtime, found {sys.version}")

    # Distribution and import names are intentionally different for two packages.
    for module in ("ampliconflow", "Bio", "biom", "jupyterlab", "papermill", "statannotations"):
        import_module(module)

    plugins = set(PluginManager().plugins)
    missing = EXPECTED_PLUGINS - plugins
    if missing:
        raise RuntimeError(f"Missing required QIIME 2 plugins: {sorted(missing)}")

    result = {
        "python": sys.version.split()[0],
        "distributions": {name: metadata.version(name) for name in EXPECTED_DISTRIBUTIONS},
        "qiime2": metadata.version("qiime2"),
        "required_qiime_plugins": sorted(EXPECTED_PLUGINS),
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
