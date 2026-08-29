import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SHA256 = re.compile(r"[0-9a-f]{64}")


def test_reference_dataset_registry_is_pinned_and_complementary():
    registry = yaml.safe_load(
        (ROOT / "validation/reference-datasets.yaml").read_text(encoding="utf-8")
    )
    datasets = registry["datasets"]

    assert registry["schema_version"] == 1
    assert registry["distribution"]["license"] == "BSD-3-Clause"
    assert {dataset["role"] for dataset in datasets} == {"primary", "secondary"}
    assert {dataset["read_layout"] for dataset in datasets} == {"single-end", "paired-end"}
    assert all(dataset["sample_count"] > 0 for dataset in datasets)

    files = [file for dataset in datasets for file in dataset["files"]]
    assert files
    assert all(file["url"].startswith("https://") for file in files)
    assert all(file["size_bytes"] > 0 for file in files)
    assert all(SHA256.fullmatch(file["sha256"]) for file in files)
    assert len({file["url"] for file in files}) == len(files)
