import json
import os
import signal
import subprocess
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
import yaml

from ampliconflow import runner
from ampliconflow.cli import build_parser, cmd_run, cmd_validate
from ampliconflow.paths import create_run_paths
from ampliconflow.planning import build_plan
from ampliconflow.runs import reserve_temporary

ROOT = Path(__file__).resolve().parents[1]


def scientific_stubs(folder):
    (folder / "ipykernel.py").write_text("__version__ = 'fixture'\n", encoding="utf-8")
    qiime = folder / "qiime2"
    qiime.mkdir(exist_ok=True)
    (qiime / "__init__.py").write_text("__version__ = 'fixture'\n", encoding="utf-8")
    (qiime / "sdk.py").write_text(
        "class PluginManager:\n    def __init__(self): self.plugins = {'dada2': object()}\n",
        encoding="utf-8",
    )
    jupyter = folder / "jupyter_client"
    jupyter.mkdir(exist_ok=True)
    (jupyter / "__init__.py").write_text("", encoding="utf-8")
    (jupyter / "kernelspec.py").write_text(
        "import sys\nclass KernelSpecManager:\n"
        "    def get_kernel_spec(self, name):\n"
        "        return type('Spec', (), {'argv': [sys.executable]})()\n",
        encoding="utf-8",
    )


def qza_bytes(semantic_type):
    import io
    from uuid import uuid4

    identifier = str(uuid4())
    target = io.BytesIO()
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr(
            f"{identifier}/metadata.yaml",
            f"uuid: {identifier}\ntype: {semantic_type}\nformat: FixtureFormat\n",
        )
    return target.getvalue()


@pytest.fixture
def project(tmp_path, monkeypatch):
    project = tmp_path / "application"
    (project / "schemas").mkdir(parents=True)
    (project / "schemas/parameters.schema.json").write_bytes(
        (ROOT / "schemas/parameters.schema.json").read_bytes()
    )
    templates = project / "notebooks/templates"
    templates.mkdir(parents=True)
    notebook = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}
        },
        "cells": [
            {
                "cell_type": "code",
                "execution_count": None,
                "outputs": [],
                "metadata": {"tags": ["parameters"]},
                "source": "experiment_name = None",
            }
        ],
    }
    for name in ("01-prepare-data.ipynb", "02-quality-control.ipynb"):
        (templates / name).write_text(json.dumps(notebook), encoding="utf-8")
    config = tmp_path / "config"
    config.mkdir()
    source = config / "params.yaml"
    (config / "meta.tsv").write_text("sample-id\tgroup\ns1\ta\n", encoding="utf-8")
    fastq_f = config / "s1_R1.fastq.gz"
    fastq_r = config / "s1_R2.fastq.gz"
    fastq_f.write_bytes(b"fixture")
    fastq_r.write_bytes(b"fixture")
    (config / "manifest.csv").write_text(
        f"sample-id,absolute-filepath,direction\ns1,{fastq_f},forward\ns1,{fastq_r},reverse\n",
        encoding="utf-8",
    )
    source.write_text(
        yaml.safe_dump(
            {
                "experiment_name": "study",
                "base_dir": ".",
                "inputs": {"metadata_file": "meta.tsv", "manifest_file": "manifest.csv"},
                "sequencing": {"read_layout": "paired-end"},
                "pipeline": {"steps": ["prepare-data", "quality-control"]},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("AMPLICONFLOW_TEMP_DIR", raising=False)
    monkeypatch.setattr(runner, "collect_run_info", lambda **_: {"environment": {}})
    monkeypatch.setattr(
        runner,
        "require_preflight",
        lambda parameters, *_args, **_kwargs: {
            "ok": True,
            "errors": [],
            "warnings": [],
            "checks": {},
            "plan": build_plan(parameters),
        },
    )
    monkeypatch.setattr(runner, "verify_bindings", lambda *_args, **_kwargs: {})
    return project, source


def state(paths):
    return json.loads((paths.provenance / "run.json").read_text())


def fake_notebook(command, *, cwd, env):
    assert cwd == Path(env["AMPLICONFLOW_RUN_DIR"])
    assert Path(env["TMPDIR"]).is_dir()
    Path(command[4]).write_text("executed", encoding="utf-8")
    (cwd / "artifacts/result.qza").write_bytes(b"user artifact fixture")


def test_repeated_runs_preserve_outputs_and_snapshots(project, monkeypatch):
    root, source = project
    monkeypatch.setattr(runner, "execute_notebook", fake_notebook)
    first = runner.run_pipeline(source, root)
    before = {
        str(p.relative_to(first.root)): p.read_bytes() for p in first.root.rglob("*") if p.is_file()
    }
    second = runner.run_pipeline(source, root)
    assert first.run_id != second.run_id
    assert first.root.parent == root / "experiments/study/runs"
    assert before == {
        str(p.relative_to(first.root)): p.read_bytes() for p in first.root.rglob("*") if p.is_file()
    }
    assert (second.parameters / "original.yaml").read_bytes() == source.read_bytes()
    effective = yaml.safe_load((second.parameters / "effective.yaml").read_text())
    assert effective["inputs"]["metadata_file"] == str(source.parent / "meta.tsv")
    assert state(second)["status"] == "completed"
    assert not Path(state(second)["temporary_dir"]).exists()
    assert (second.artifacts / "result.qza").exists()


@pytest.mark.parametrize("identifier", [".", "..", "../escape", "/tmp", "", "a/b"])
def test_unsafe_identifiers_rejected(tmp_path, identifier):
    with pytest.raises(ValueError):
        create_run_paths(tmp_path, identifier)
    with pytest.raises(ValueError):
        create_run_paths(tmp_path, "study", identifier)
    assert not (tmp_path / "experiments").exists()


def test_existing_id_is_not_overwritten(project, monkeypatch):
    root, source = project
    monkeypatch.setattr(runner, "execute_notebook", fake_notebook)
    first = runner.run_pipeline(source, root, run_id="same")
    previous = (first.provenance / "run.json").read_bytes()
    with pytest.raises(FileExistsError):
        runner.run_pipeline(source, root, run_id="same")
    assert (first.provenance / "run.json").read_bytes() == previous


def test_concurrent_runs_are_disjoint(project, monkeypatch):
    root, source = project
    monkeypatch.setattr(runner, "execute_notebook", fake_notebook)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(runner.run_pipeline, source, root) for _ in range(2)]
        runs = [future.result() for future in futures]
    assert len({paths.root for paths in runs}) == 2
    assert all(state(paths)["status"] == "completed" for paths in runs)


def test_concurrent_explicit_id_has_only_one_owner(project, monkeypatch):
    root, source = project
    monkeypatch.setattr(runner, "execute_notebook", fake_notebook)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(runner.run_pipeline, source, root, run_id="shared-id") for _ in range(2)
        ]
        outcomes = [future.exception() for future in futures]
    assert sum(error is None for error in outcomes) == 1
    assert sum(isinstance(error, FileExistsError) for error in outcomes) == 1
    info = json.loads((root / "experiments/study/runs/shared-id/provenance/run.json").read_text())
    assert info["status"] == "completed"


def test_invalid_parameters_do_not_allocate_run(project):
    root, source = project
    parameters = yaml.safe_load(source.read_text())
    parameters["experiment_name"] = ".."
    source.write_text(yaml.safe_dump(parameters), encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid parameter"):
        runner.run_pipeline(source, root)
    assert not (root / "experiments").exists()


@pytest.mark.parametrize(
    "error, expected",
    [
        (RuntimeError("notebook failed"), "failed"),
        (KeyboardInterrupt(), "cancelled"),
        (runner.RunCancelled(signal.SIGTERM), "cancelled"),
    ],
)
def test_failure_and_cancellation_preserve_temporary(project, monkeypatch, error, expected):
    root, source = project

    def fail(*_args, **_kwargs):
        raise error

    monkeypatch.setattr(runner, "execute_notebook", fail)
    with pytest.raises(type(error)):
        runner.run_pipeline(source, root, run_id="attempt")
    info = json.loads((root / "experiments/study/runs/attempt/provenance/run.json").read_text())
    assert info["status"] == expected
    assert info["steps"][0]["status"] == expected
    assert info["steps"][1]["status"] == "blocked"
    assert Path(info["temporary_dir"]).is_dir()


def test_missing_template_records_failed_attempt(project):
    root, source = project
    (root / "notebooks/templates/01-prepare-data.ipynb").unlink()
    with pytest.raises(FileNotFoundError):
        runner.run_pipeline(source, root, run_id="missing")
    info = json.loads((root / "experiments/study/runs/missing/provenance/run-end.json").read_text())
    assert info["status"] == "failed"


def test_source_yaml_changes_do_not_affect_snapshot(project, monkeypatch):
    root, source = project
    original = source.read_bytes()

    def mutate_source(command, **kwargs):
        source.write_text("changed after snapshot", encoding="utf-8")
        fake_notebook(command, **kwargs)

    monkeypatch.setattr(runner, "execute_notebook", mutate_source)
    paths = runner.run_pipeline(source, root)
    assert (paths.parameters / "original.yaml").read_bytes() == original
    assert state(paths)["status"] == "completed"


def test_single_selected_step_uses_stable_number(project, monkeypatch):
    root, source = project
    parameters = yaml.safe_load(source.read_text())
    parameters["pipeline"]["steps"] = ["quality-control"]
    artifact = source.parent / "demux.qza"
    artifact.write_bytes(b"planning fixture")
    parameters["inputs"].pop("manifest_file")
    parameters["inputs"]["artifacts"] = {
        "demultiplexed_sequences": {"path": "demux.qza", "sha256": "0" * 64}
    }
    source.write_text(yaml.safe_dump(parameters), encoding="utf-8")
    monkeypatch.setattr(runner, "execute_notebook", fake_notebook)
    paths = runner.run_pipeline(source, root)
    assert (paths.notebooks / "02-quality-control.ipynb").exists()


def test_symlink_output_ancestor_rejected(tmp_path):
    external = tmp_path / "external"
    external.mkdir()
    project = tmp_path / "project"
    project.mkdir()
    (project / "experiments").symlink_to(external, target_is_directory=True)
    with pytest.raises(ValueError):
        create_run_paths(project, "study")
    assert list(external.iterdir()) == []


def test_cleanup_checks_owner_and_preserves_other_runs(tmp_path):
    first = create_run_paths(tmp_path, "study")
    second = create_run_paths(tmp_path, "study")
    one = reserve_temporary(tmp_path / ".tmp", "study", first)
    two = reserve_temporary(tmp_path / ".tmp", "study", second)
    one.cleanup()
    assert two.root.exists()
    (two.root / ".ampliconflow-owner.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError):
        two.cleanup()
    assert two.root.exists()


def test_temporary_collision_and_output_overlap_rejected(tmp_path):
    paths = create_run_paths(tmp_path, "study", "fixed")
    temporary = reserve_temporary(tmp_path / ".tmp", "study", paths)
    with pytest.raises(FileExistsError):
        reserve_temporary(tmp_path / ".tmp", "study", paths)
    with pytest.raises(ValueError):
        reserve_temporary(paths.root, "study", paths)
    assert temporary.root.exists()


def test_cli_resolves_source_before_changing_directory(project, monkeypatch):
    _root, source = project
    monkeypatch.chdir(source.parent)
    seen = []
    monkeypatch.setattr(
        "ampliconflow.cli.os.execvpe", lambda _file, command, _env: seen.append(command)
    )
    args = build_parser().parse_args(["run", "params.yaml", "env", "--run-id", "chosen"])
    cmd_run(args)
    assert seen[0][2] == str(source)
    assert seen[0][-2:] == ["--run-id", "chosen"]


def test_validate_does_not_allocate_run(project, monkeypatch):
    root, source = project
    monkeypatch.setattr("ampliconflow.cli._repo_root", lambda: root)
    args = build_parser().parse_args(["validate", str(source)])
    assert cmd_validate(args) == 0
    assert not (root / "experiments").exists()


def test_real_subprocess_receives_run_environment(project, tmp_path, monkeypatch):
    root, source = project
    parameters = yaml.safe_load(source.read_text())
    parameters["pipeline"]["steps"] = ["prepare-data"]
    source.write_text(yaml.safe_dump(parameters), encoding="utf-8")
    stub = tmp_path / "stub"
    stub.mkdir()
    (stub / "papermill.py").write_text(
        "import os, pathlib, sys, uuid, zipfile\n"
        "__version__ = 'fixture'\n"
        "root = pathlib.Path(os.environ['AMPLICONFLOW_RUN_DIR'])\n"
        "assert pathlib.Path.cwd() == root\n"
        "assert pathlib.Path(os.environ['TMPDIR']).is_dir()\n"
        "pathlib.Path(sys.argv[2]).write_text('executed')\n"
        "(root / 'artifacts' / 'allowed.qza').write_bytes(b'user output')\n",
        encoding="utf-8",
    )
    with (stub / "papermill.py").open("a", encoding="utf-8") as handle:
        handle.write(
            "identifier = str(uuid.uuid4())\n"
            "target = root / 'artifacts/prepare-data/demultiplexed_sequences.qza'\n"
            "with zipfile.ZipFile(target, 'w') as z:\n"
            " z.writestr(identifier + '/metadata.yaml', f'uuid: {identifier}\\ntype: SampleData[PairedEndSequencesWithQuality]\\nformat: FixtureFormat\\n')\n"
        )
    scientific_stubs(stub)
    monkeypatch.setenv("PYTHONPATH", str(stub) + os.pathsep + os.environ.get("PYTHONPATH", ""))
    # User repositories may already track .qza: the runtime never invokes development policy.
    subprocess.run(["git", "init", "--quiet", str(root)], check=True)
    (root / "user-input.qza").write_bytes(b"fixture")
    subprocess.run(["git", "add", "user-input.qza"], cwd=root, check=True)
    paths = runner.run_pipeline(source, root)
    assert state(paths)["status"] == "completed"
    assert (paths.artifacts / "allowed.qza").read_bytes() == b"user output"


def test_execute_notebook_propagates_nonzero_status(tmp_path):
    with pytest.raises(subprocess.CalledProcessError):
        runner.execute_notebook(
            [sys.executable, "-c", "raise SystemExit(7)"], cwd=tmp_path, env=os.environ.copy()
        )


def test_sigterm_cli_cancels_child_and_records_status(project, tmp_path):
    root, source = project
    stub = tmp_path / "signal-stub"
    stub.mkdir()
    ready = tmp_path / "child-ready"
    (stub / "papermill.py").write_text(
        "import os, pathlib, time\n"
        "__version__ = 'test-fixture'\n"
        "if __name__ == '__main__':\n"
        f"    pathlib.Path({str(ready)!r}).write_text(str(os.getpid()))\n"
        "    time.sleep(30)\n",
        encoding="utf-8",
    )
    scientific_stubs(stub)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(stub) + os.pathsep + str(ROOT / "src")
    command = [
        sys.executable,
        "-m",
        "ampliconflow.runner",
        str(source),
        "--project-dir",
        str(root),
        "--run-id",
        "cancel-test",
    ]
    process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 10
        while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        assert ready.exists(), "Test notebook did not start"
        process.terminate()
        process.communicate(timeout=10)
        assert process.returncode == 143
        info = json.loads(
            (root / "experiments/study/runs/cancel-test/provenance/run.json").read_text()
        )
        assert info["status"] == "cancelled"
        assert Path(info["temporary_dir"]).exists()
        with pytest.raises(ProcessLookupError):
            os.kill(int(ready.read_text()), 0)
    finally:
        if process.poll() is None:
            process.terminate()
            process.communicate(timeout=10)


def test_mutating_parameter_snapshot_fails_run(project, monkeypatch):
    root, source = project

    def mutate(command, **kwargs):
        fake_notebook(command, **kwargs)
        Path(command[command.index("--parameters_file") + 1]).write_text(
            "changed", encoding="utf-8"
        )

    monkeypatch.setattr(runner, "execute_notebook", mutate)
    with pytest.raises(RuntimeError, match="snapshot was modified"):
        runner.run_pipeline(source, root, run_id="mutation")
    info = json.loads((root / "experiments/study/runs/mutation/provenance/run.json").read_text())
    assert info["status"] == "failed"
    assert Path(info["temporary_dir"]).exists()


def test_legacy_outputs_are_untouched(project, monkeypatch):
    root, source = project
    legacy = root / "experiments/study/artifacts"
    legacy.mkdir(parents=True)
    old = legacy / "old.qza"
    old.write_bytes(b"legacy artifact")
    monkeypatch.setattr(runner, "execute_notebook", fake_notebook)
    runner.run_pipeline(source, root)
    assert old.read_bytes() == b"legacy artifact"


def test_shell_bootstrap_uses_isolated_runner(project, tmp_path):
    root, source = project
    parameters = yaml.safe_load(source.read_text())
    parameters["pipeline"]["steps"] = ["prepare-data"]
    source.write_text(yaml.safe_dump(parameters), encoding="utf-8")
    (root / "ampliconflow").write_bytes((ROOT / "ampliconflow").read_bytes())
    conda = tmp_path / "conda"
    (conda / "etc/profile.d").mkdir(parents=True)
    (conda / "etc/profile.d/conda.sh").write_text(
        'conda() { export CONDA_DEFAULT_ENV="$2"; }\n', encoding="utf-8"
    )
    stub = tmp_path / "shell-stub"
    stub.mkdir()
    (stub / "papermill.py").write_text(
        "import os, pathlib, sys, uuid, zipfile\n"
        "__version__ = 'fixture'\n"
        "if __name__ == '__main__':\n"
        " assert os.environ['CONDA_DEFAULT_ENV'] == 'test-env'\n"
        " pathlib.Path(sys.argv[2]).write_text('executed')\n"
        " root = pathlib.Path(os.environ['AMPLICONFLOW_RUN_DIR'])\n"
        " identifier = str(uuid.uuid4())\n"
        " with zipfile.ZipFile(root / 'artifacts/prepare-data/demultiplexed_sequences.qza', 'w') as z:\n"
        "  z.writestr(identifier + '/metadata.yaml', f'uuid: {identifier}\\ntype: SampleData[PairedEndSequencesWithQuality]\\nformat: FixtureFormat\\n')\n",
        encoding="utf-8",
    )
    scientific_stubs(stub)
    env = os.environ.copy()
    env["CONDA_BASE"] = str(conda)
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env["PATH"]
    env["PYTHONPATH"] = str(stub) + os.pathsep + str(ROOT / "src")
    result = subprocess.run(
        ["bash", str(root / "ampliconflow"), "params.yaml", "test-env", "--run-id", "shell"],
        cwd=source.parent,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    info = json.loads((root / "experiments/study/runs/shell/provenance/run.json").read_text())
    assert info["status"] == "completed"
    assert info["provenance"]["status"] == "completed"
