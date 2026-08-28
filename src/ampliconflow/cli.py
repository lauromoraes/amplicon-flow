from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import NoReturn

from .config import (
    get_experiment_name,
    get_pipeline_steps,
    load_parameters,
    validate_parameters,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def cmd_validate(args: argparse.Namespace) -> int:
    root = _repo_root()
    schema = root / "schemas" / "parameters.schema.json"

    params = load_parameters(args.parameters)
    validate_parameters(params, schema)

    print(f"Valid configuration: {args.parameters}")
    print(f"Experiment: {get_experiment_name(params)}")
    print("Steps:")
    for step in get_pipeline_steps(params):
        print(f"  - {step}")

    return 0


def cmd_run(args: argparse.Namespace) -> NoReturn:
    root = _repo_root()
    runner = root / "ampliconflow"

    env = os.environ.copy()
    command = [
        "bash",
        str(runner),
        str(Path(args.parameters).expanduser().resolve()),
        args.conda_environment,
    ]
    if args.run_id is not None:
        command.extend(["--run-id", args.run_id])
    # Replace the CLI process so signals reach the runner, not a waiting parent.
    os.execvpe("bash", command, env)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ampliconflow",
        description=("Reproducible, notebook-centered amplicon sequencing analysis."),
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate an experiment YAML configuration.",
    )
    validate_parser.add_argument("parameters")
    validate_parser.set_defaults(func=cmd_validate)

    run_parser = subparsers.add_parser(
        "run",
        help="Execute the configured notebook workflow with Papermill.",
    )
    run_parser.add_argument("parameters")
    run_parser.add_argument("conda_environment")
    run_parser.add_argument(
        "--run-id", help="Optional unique ID; existing run directories are refused."
    )
    run_parser.set_defaults(func=cmd_run)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
