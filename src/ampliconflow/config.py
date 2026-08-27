from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


def load_parameters(path: str | Path) -> dict[str, Any]:
    path = Path(path).expanduser().resolve()

    if not path.is_file():
        raise FileNotFoundError(f"Parameter file not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    if not isinstance(data, dict):
        raise TypeError("The parameter file must contain a YAML mapping.")

    return data


def validate_parameters(
    parameters: dict[str, Any],
    schema_path: str | Path,
) -> None:
    schema_path = Path(schema_path).expanduser().resolve()

    with schema_path.open("r", encoding="utf-8") as handle:
        schema = json.load(handle)

    validator = Draft202012Validator(schema)

    errors = sorted(
        validator.iter_errors(parameters),
        key=lambda error: list(error.path),
    )

    if errors:
        formatted = []

        for error in errors:
            location = ".".join(map(str, error.path)) or "<root>"

            formatted.append(f"{location}: {error.message}")

        raise ValueError("Invalid parameter file:\n  - " + "\n  - ".join(formatted))


def get_experiment_name(
    parameters: dict[str, Any],
) -> str:
    return str(parameters["experiment_name"])


def get_pipeline_steps(
    parameters: dict[str, Any],
) -> list[str]:
    return list(parameters["pipeline"]["steps"])


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("parameters")
    parser.add_argument("--schema", required=True)

    parser.add_argument(
        "--field",
        choices=("experiment", "steps", "json"),
        default="json",
    )

    args = parser.parse_args()

    parameters = load_parameters(args.parameters)
    validate_parameters(parameters, args.schema)

    if args.field == "experiment":
        print(get_experiment_name(parameters))

    elif args.field == "steps":
        print("\n".join(get_pipeline_steps(parameters)))

    else:
        print(json.dumps(parameters, indent=2))


if __name__ == "__main__":
    main()
