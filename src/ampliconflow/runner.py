"""Orchestrate isolated Papermill runs after the shell activates Conda."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

from .config import effective_parameters, get_experiment_name, validate_parameters
from .paths import create_run_paths
from .preflight import require_preflight, verify_bindings
from .provenance import collect_run_info, sha256_file, write_run_info
from .runs import reserve_temporary


class RunCancelled(Exception):
    def __init__(self, signum):
        super().__init__(f"Run interrupted by signal {signum}")
        self.signum = signum


def utc_now():
    return datetime.now(UTC).isoformat()


def execute_notebook(command, *, cwd, env):
    # A separate process group lets cancellation terminate the notebook kernel too.
    process = subprocess.Popen(command, cwd=cwd, env=env, start_new_session=True)
    try:
        code = process.wait()
        if code:
            raise subprocess.CalledProcessError(code, command)
    except BaseException:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        # The parent may exit before a kernel that ignores SIGTERM. Kill any
        # remaining members of this owned group before returning cancellation.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        raise


def run_pipeline(parameters_file, project_dir, *, run_id=None, temp_base=None):
    project = Path(project_dir).expanduser().resolve()
    source = Path(parameters_file).expanduser().resolve(strict=True)
    original = source.read_bytes()
    parameters = yaml.safe_load(original)
    validate_parameters(parameters, project / "schemas/parameters.schema.json")
    experiment = get_experiment_name(parameters)
    effective = effective_parameters(parameters, source)
    preflight = require_preflight(effective, project, temp_base=temp_base)
    plan = preflight["plan"]
    paths = create_run_paths(project, experiment, run_id)
    steps = [{"id": item["id"], "status": "planned"} for item in plan["steps"]]
    state = {
        "run_id": paths.run_id,
        "experiment": experiment,
        "run_dir": str(paths.root),
        "status": "planned",
        "created_at": utc_now(),
        "steps": steps,
        "parameters_source": str(source),
        "temporary_cleanup": "not_allocated",
    }
    temporary = None
    active = None
    print(f"AmpliconFlow | Run: {paths.run_id} | Directory: {paths.root}", flush=True)
    try:
        with (paths.parameters / "original.yaml").open("xb") as handle:
            handle.write(original)
        effective_file = paths.parameters / "effective.yaml"
        with effective_file.open("x", encoding="utf-8") as handle:
            yaml.safe_dump(effective, handle, sort_keys=True)
        state["original_parameters_sha256"] = sha256_file(paths.parameters / "original.yaml")
        state["effective_parameters_sha256"] = sha256_file(effective_file)
        write_run_info(paths.provenance / "plan.json", plan)
        write_run_info(paths.provenance / "preflight.json", preflight)
        state["provenance"] = collect_run_info(
            experiment=experiment,
            parameters_file=effective_file,
            status="running",
            project_dir=project,
        )
        # Include exact scientific source fingerprints, including uncommitted files.
        sources = [project / "ampliconflow", project / "pyproject.toml"]
        for folder, pattern in (
            ("src/ampliconflow", "*.py"),
            ("notebooks/templates", "*.ipynb"),
            ("schemas", "*.json"),
        ):
            sources.extend((project / folder).rglob(pattern))
        state["source_sha256"] = {
            str(path.relative_to(project)): sha256_file(path) for path in sources if path.is_file()
        }
        base = Path(temp_base or os.environ.get("AMPLICONFLOW_TEMP_DIR", project / ".tmp"))
        temporary = reserve_temporary(base, experiment, paths)
        state.update(
            status="running",
            started_at=utc_now(),
            temporary_dir=str(temporary.root),
            temporary_cleanup="preserved",
        )
        env = os.environ.copy()
        env.update(
            {
                "AMPLICONFLOW_RUN_ID": paths.run_id,
                "AMPLICONFLOW_RUN_DIR": str(paths.root),
                "AMPLICONFLOW_PROJECT_DIR": str(project),
                "AMPLICONFLOW_PLAN_FILE": str(paths.provenance / "plan.json"),
                "TMPDIR": str(temporary.root / "qiime2"),
                "TMP": str(temporary.root / "qiime2"),
                "TEMP": str(temporary.root / "qiime2"),
                "JOBLIB_TEMP_FOLDER": str(temporary.root / "joblib"),
                "QIIME_CACHE": str(temporary.root / "qiime2-cache"),
            }
        )
        state["provenance"]["environment"].update(
            {key: env[key] for key in ("TMPDIR", "JOBLIB_TEMP_FOLDER", "QIIME_CACHE")}
        )
        write_run_info(paths.provenance / "run-start.json", state)
        write_run_info(paths.provenance / "run.json", state)
        planned = {item["id"]: item for item in plan["steps"]}
        for active in steps:
            name = active["id"]
            contract = planned[name]
            template = project / "notebooks/templates" / contract["template"]
            active.update(status="running", started_at=utc_now())
            write_run_info(paths.provenance / "run.json", state)
            if not template.is_file():
                raise FileNotFoundError(f"Step template disappeared after preflight: {template}")
            active["input_artifacts"] = verify_bindings(contract["inputs"], paths.root)
            (paths.artifacts / name).mkdir(exist_ok=False)
            execute_notebook(
                [
                    sys.executable,
                    "-m",
                    "papermill",
                    str(template),
                    str(paths.notebooks / template.name),
                    "--parameters_file",
                    str(effective_file),
                    "--kernel",
                    contract["kernel"],
                ],
                cwd=paths.root,
                env=env,
            )
            # Detect accidental mutation of the execution configuration by notebook code.
            if (
                sha256_file(effective_file) != state["effective_parameters_sha256"]
                or sha256_file(paths.parameters / "original.yaml")
                != state["original_parameters_sha256"]
            ):
                raise RuntimeError("Parameter snapshot was modified during execution")
            active["output_artifacts"] = verify_bindings(contract["outputs"], paths.root)
            active.update(status="completed", ended_at=utc_now())
            write_run_info(paths.provenance / "run.json", state)
        active = None
        temporary.cleanup()
        state.update(status="completed", temporary_cleanup="removed")
    except (KeyboardInterrupt, RunCancelled) as error:
        state.update(status="cancelled", error=type(error).__name__)
        if active:
            active.update(status="cancelled", ended_at=utc_now())
        raise
    except Exception as error:
        state.update(status="failed", error=f"{type(error).__name__}: {error}")
        if active:
            active.update(status="failed", ended_at=utc_now())
        raise
    finally:
        for step in steps:
            if step["status"] == "planned":
                step["status"] = "blocked"
        state["ended_at"] = utc_now()
        if "provenance" in state:
            state["provenance"]["status"] = state["status"]
        write_run_info(paths.provenance / "run-end.json", state)
        write_run_info(paths.provenance / "run.json", state)
    print(f"Pipeline completed successfully: {paths.root}", flush=True)
    return paths


def main():
    parser = argparse.ArgumentParser(
        description="Run isolated notebooks in the active environment."
    )
    parser.add_argument("parameters")
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--run-id")
    args = parser.parse_args()

    def cancel(signum, _frame):
        raise RunCancelled(signum)

    previous = signal.signal(signal.SIGTERM, cancel)
    try:
        run_pipeline(args.parameters, args.project_dir, run_id=args.run_id)
    except RunCancelled as error:
        return 128 + error.signum
    except KeyboardInterrupt:
        return 130
    except Exception as error:  # noqa: BLE001 -- CLI boundary; run_pipeline records and re-raises.
        print(f"Pipeline failed: {error}", file=sys.stderr)
        return 1
    finally:
        signal.signal(signal.SIGTERM, previous)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
