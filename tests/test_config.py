from pathlib import Path

from ampliconflow.config import (
    get_experiment_name,
    get_pipeline_steps,
    load_parameters,
    validate_parameters,
)


def test_example_parameters_are_valid():
    root = Path(__file__).resolve().parents[1]
    params = load_parameters(root / "examples/params-example.yaml")
    validate_parameters(params, root / "schemas/parameters.schema.json")
    assert get_experiment_name(params) == "example-study"
    assert get_pipeline_steps(params) == ["prepare-data", "quality-control"]
