import subprocess
import sys
from pathlib import Path

import pytest

from ampliconflow.repository_policy import tracked_qza_files


@pytest.fixture
def repository(tmp_path):
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text("*.qza\n", encoding="utf-8")
    return tmp_path


def force_add(repository, name):
    path = repository / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"test fixture, not a scientific artifact")
    subprocess.run(["git", "add", "-f", "--", name], cwd=repository, check=True)


def test_ignored_untracked_artifact_is_allowed(repository):
    (repository / "untracked.qza").write_bytes(b"fixture")
    force_add(repository, "notes.md")
    assert tracked_qza_files(repository) == []


def test_force_added_artifacts_are_detected_at_any_depth(repository):
    names = ["root.qza", "nested/with space.qza", "nested/with\nnewline.qza"]
    for name in names:
        force_add(repository, name)
    assert tracked_qza_files(repository) == sorted(names)


def test_non_repository_fails_closed(tmp_path):
    with pytest.raises(subprocess.CalledProcessError):
        tracked_qza_files(tmp_path)


def test_subdirectory_check_still_scans_entire_repository(repository):
    force_add(repository, "root.qza")
    subdirectory = repository / "subdirectory"
    subdirectory.mkdir()
    assert tracked_qza_files(subdirectory) == ["root.qza"]


def test_command_exit_status(repository):
    command = [sys.executable, "-m", "ampliconflow.repository_policy", str(repository)]
    assert subprocess.run(command, capture_output=True, check=False).returncode == 0
    force_add(repository, "blocked.qza")
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 1
    assert "blocked.qza" in result.stdout


def test_project_has_no_tracked_qza():
    root = Path(__file__).resolve().parents[1]
    assert tracked_qza_files(root) == []
