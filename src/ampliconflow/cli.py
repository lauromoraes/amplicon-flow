from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import NoReturn

from .config import (
    effective_parameters,
    get_experiment_name,
    get_pipeline_steps,
    load_parameters,
    validate_parameters,
)
from .planning import build_plan
from .preflight import preflight
from .reference_data import acquire_reference_dataset, load_registry


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


def _configuration(args):
    root = _repo_root()
    source = Path(args.parameters).expanduser().resolve()
    params = load_parameters(source)
    validate_parameters(params, root / "schemas/parameters.schema.json")
    return root, effective_parameters(params, source)


def cmd_plan(args: argparse.Namespace) -> int:
    _root, params = _configuration(args)
    document = build_plan(params)
    print(
        json.dumps(document, indent=2)
        if args.json
        else "\n".join(f"{step['id']}: {step['template']}" for step in document["steps"])
    )
    return 0


def cmd_preflight(args: argparse.Namespace) -> int:
    root, params = _configuration(args)
    report = preflight(params, root)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("Preflight: " + ("ready" if report["ok"] else "not ready"))
        for kind in ("errors", "warnings"):
            for item in report[kind]:
                print(f"  {kind[:-1]} [{item['code']}]: {item['message']}")
    return 0 if report["ok"] else 2


def cmd_reference_list(_args: argparse.Namespace) -> int:
    registry = load_registry(_repo_root() / "validation/reference-datasets.yaml")
    for dataset in registry["datasets"]:
        print(
            f"{dataset['id']}\t{dataset['role']}\t{dataset['read_layout']}\t"
            f"{dataset['sample_count']} samples"
        )
    return 0


def cmd_reference_fetch(args: argparse.Namespace) -> int:
    destination = acquire_reference_dataset(
        _repo_root() / "validation/reference-datasets.yaml",
        args.dataset,
        args.destination,
    )
    print(f"Reference dataset ready: {destination}")
    return 0


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

    plan_parser = subparsers.add_parser("plan", help="Resolve step contracts without execution.")
    plan_parser.add_argument("parameters")
    plan_parser.add_argument("--json", action="store_true")
    plan_parser.set_defaults(func=cmd_plan)

    preflight_parser = subparsers.add_parser(
        "preflight", help="Check inputs and the currently active scientific environment."
    )
    preflight_parser.add_argument("parameters")
    preflight_parser.add_argument("--json", action="store_true")
    preflight_parser.set_defaults(func=cmd_preflight)

    reference_parser = subparsers.add_parser(
        "reference-data", help="List or explicitly acquire scientific reference datasets."
    )
    reference_commands = reference_parser.add_subparsers(dest="reference_command", required=True)
    reference_list = reference_commands.add_parser("list", help="List pinned reference datasets.")
    reference_list.set_defaults(func=cmd_reference_list)
    reference_fetch = reference_commands.add_parser(
        "fetch", help="Download, verify, normalize, and atomically publish one dataset."
    )
    reference_fetch.add_argument("dataset")
    reference_fetch.add_argument("destination")
    reference_fetch.set_defaults(func=cmd_reference_fetch)

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
