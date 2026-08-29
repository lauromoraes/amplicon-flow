import json
import zipfile
from pathlib import Path
from uuid import uuid4

import pytest

from ampliconflow.planning import PlanningError, build_plan
from ampliconflow.preflight import inspect_artifact, preflight


def parameters(tmp_path, steps=("prepare-data", "quality-control")):
    metadata = tmp_path / "metadata.tsv"
    metadata.write_text("sample-id\tgroup\ns1\ta\n", encoding="utf-8")
    forward, reverse = tmp_path / "forward.fastq.gz", tmp_path / "reverse.fastq.gz"
    forward.write_bytes(b"forward")
    reverse.write_bytes(b"reverse")
    manifest = tmp_path / "manifest.csv"
    manifest.write_text(
        f"sample-id,absolute-filepath,direction\ns1,{forward},forward\ns1,{reverse},reverse\n",
        encoding="utf-8",
    )
    return {
        "experiment_name": "study",
        "base_dir": str(tmp_path),
        "inputs": {"metadata_file": str(metadata), "manifest_file": str(manifest)},
        "sequencing": {"read_layout": "paired-end"},
        "pipeline": {"steps": list(steps)},
    }


def artifact(path, semantic_type):
    identifier = str(uuid4())
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            f"{identifier}/metadata.yaml",
            f"uuid: {identifier}\ntype: {semantic_type}\nformat: FixtureFormat\n",
        )


def install_templates(project):
    folder = project / "notebooks/templates"
    folder.mkdir(parents=True)
    notebook = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {},
        "cells": [
            {
                "id": "parameters",
                "cell_type": "code",
                "execution_count": None,
                "outputs": [],
                "metadata": {"tags": ["parameters"]},
                "source": "value = None",
            }
        ],
    }
    for name in ("01-prepare-data.ipynb", "02-quality-control.ipynb"):
        (folder / name).write_text(json.dumps(notebook), encoding="utf-8")


def test_plan_reorders_dependencies_without_adding_steps(tmp_path):
    document = build_plan(parameters(tmp_path, ("quality-control", "prepare-data")))
    assert document["requested_steps"] == ["quality-control", "prepare-data"]
    assert [step["id"] for step in document["steps"]] == ["prepare-data", "quality-control"]
    assert document["steps"][1]["depends_on"] == ["prepare-data"]


def test_isolated_qc_requires_explicit_artifact(tmp_path):
    with pytest.raises(PlanningError) as caught:
        build_plan(parameters(tmp_path, ("quality-control",)))
    assert caught.value.code == "missing_dependency"


def test_external_artifact_binding_and_ambiguity(tmp_path):
    params = parameters(tmp_path, ("quality-control",))
    params["inputs"].pop("manifest_file")
    params["inputs"]["artifacts"] = {
        "demultiplexed_sequences": {"path": "/store/demux.qza", "sha256": "a" * 64}
    }
    document = build_plan(params)
    binding = document["steps"][0]["inputs"]["demultiplexed_sequences"]
    assert binding["source"] == "external"
    params["pipeline"]["steps"] = ["prepare-data", "quality-control"]
    with pytest.raises(PlanningError) as caught:
        build_plan(params)
    assert caught.value.code == "ambiguous_provider"


def test_artifact_checksum_and_semantic_type(tmp_path):
    path = tmp_path / "demux.qza"
    semantic_type = "SampleData[PairedEndSequencesWithQuality]"
    artifact(path, semantic_type)
    from ampliconflow.provenance import sha256_file

    result = inspect_artifact(path, semantic_type, sha256_file(path))
    assert result["type"] == semantic_type
    with pytest.raises(ValueError, match="SHA-256"):
        inspect_artifact(path, semantic_type, "0" * 64)
    with pytest.raises(ValueError, match="semantic type"):
        inspect_artifact(path, "FeatureTable[Frequency]")


def test_preflight_checks_samples_templates_environment_and_storage(tmp_path, monkeypatch):
    project = tmp_path / "application"
    project.mkdir()
    install_templates(project)
    monkeypatch.setattr(
        "ampliconflow.preflight.probe_environment",
        lambda needs_dada2: {"qiime2": "fixture", "dada2": needs_dada2},
    )
    report = preflight(parameters(tmp_path), project)
    assert report["ok"]
    assert report["checks"]["metadata_sample_count"] == 1
    assert report["checks"]["environment"]["dada2"] is True
    assert [step["id"] for step in report["plan"]["steps"]] == ["prepare-data", "quality-control"]


def test_preflight_reports_sample_mismatch_without_allocating_run(tmp_path, monkeypatch):
    project = tmp_path / "application"
    project.mkdir()
    install_templates(project)
    params = parameters(tmp_path, ("prepare-data",))
    Path(params["inputs"]["metadata_file"]).write_text(
        "sample-id\tgroup\nother\ta\n", encoding="utf-8"
    )
    monkeypatch.setattr("ampliconflow.preflight.probe_environment", lambda _: {})
    report = preflight(params, project)
    assert not report["ok"]
    assert "sample_mismatch" in {error["code"] for error in report["errors"]}
    assert not (project / "experiments").exists()
