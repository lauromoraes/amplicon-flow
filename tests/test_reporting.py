import json
from pathlib import Path

import pytest

from ampliconflow.reporting import validate_report_contribution

ROOT = Path(__file__).resolve().parents[1]


def contribution(run, **updates):
    document = {
        "schema_version": 1,
        "step": "prepare-data",
        "run_id": "attempt-1",
        "created_at": "2026-08-29T00:00:00+00:00",
        "objective": "Import demultiplexed reads.",
        "methods": {"semantic_type": "SampleData[SequencesWithQuality]"},
        "outputs": {"artifact": "artifacts/prepare-data/demultiplexed_sequences.qza"},
        "limitations": [],
        "references": ["https://doi.org/10.1038/s41587-019-0209-9"],
    }
    document.update(updates)
    path = run / "reports/contributions/prepare-data.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def validate(path, run):
    return validate_report_contribution(
        path,
        ROOT / "schemas/report-contribution.schema.json",
        step="prepare-data",
        run_id="attempt-1",
        run_root=run,
    )


def test_report_contribution_binds_identity_and_existing_outputs(tmp_path):
    run = tmp_path / "run"
    artifact = run / "artifacts/prepare-data/demultiplexed_sequences.qza"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"fixture")
    document = validate(contribution(run), run)
    assert document["step"] == "prepare-data"


@pytest.mark.parametrize(
    "updates, message",
    [
        ({"run_id": "other"}, "identity"),
        ({"outputs": {"artifact": "/tmp/outside.qza"}}, "safe paths"),
        ({"outputs": {"artifact": "../../outside.qza"}}, "safe paths"),
        ({"references": []}, "Invalid report contribution"),
    ],
)
def test_report_contribution_rejects_invalid_or_unbound_evidence(tmp_path, updates, message):
    run = tmp_path / "run"
    run.mkdir()
    with pytest.raises(ValueError, match=message):
        validate(contribution(run, **updates), run)
