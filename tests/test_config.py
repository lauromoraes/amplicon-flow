from pathlib import Path

import pytest

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


@pytest.mark.parametrize(
    "mutation",
    [
        lambda params: params["inputs"].pop("manifest_file"),
        lambda params: params.pop("sequencing"),
        lambda params: params["sequencing"].pop("read_layout"),
        lambda params: params.pop("prepare_data"),
        lambda params: params["prepare_data"].pop("quality_plot_reads"),
        lambda params: params["prepare_data"].update(phred_offset=64),
        lambda params: params["prepare_data"].update(quality_plot_reads=0),
    ],
)
def test_prepare_data_requires_its_explicit_contract(mutation):
    root = Path(__file__).resolve().parents[1]
    params = load_parameters(root / "examples/params-example.yaml")
    mutation(params)
    with pytest.raises(ValueError, match="Invalid parameter"):
        validate_parameters(params, root / "schemas/parameters.schema.json")
