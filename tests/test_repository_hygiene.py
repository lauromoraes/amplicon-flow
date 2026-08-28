import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_qza_is_not_excluded_by_project_gitignore(tmp_path):
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / ".gitignore").write_bytes((ROOT / ".gitignore").read_bytes())
    subprocess.run(["git", "init", "--quiet"], cwd=repository, check=True)
    artifact = repository / "fixture.qza"
    artifact.write_bytes(b"small intentional fixture")

    result = subprocess.run(
        ["git", "check-ignore", "--quiet", artifact.name], cwd=repository, check=False
    )

    assert result.returncode == 1
