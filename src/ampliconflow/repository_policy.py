"""Repository hygiene checks; no scientific artifacts should be tracked by Git."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


def tracked_qza_files(repository: str | Path) -> list[str]:
    """Inspect the Git index, including force-added and staged files."""
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--full-name", "-z", "--", ":/"],
        cwd=repository,
        check=True,
        capture_output=True,
    )
    return sorted(
        {os.fsdecode(path) for path in result.stdout.split(b"\0") if path.endswith(b".qza")}
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Reject tracked .qza artifacts.")
    parser.add_argument("repository", nargs="?", default=".", type=Path)
    args = parser.parse_args()
    try:
        paths = tracked_qza_files(args.repository)
    except (OSError, subprocess.CalledProcessError) as error:
        parser.exit(2, f"Could not inspect the Git index: {error}\n")
    if paths:
        print("Tracked .qza files are not allowed; store artifacts outside Git:")
        for path in paths:
            print(f"  {path!r}")
        return 1
    print("Repository artifact policy passed: no tracked .qza files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
