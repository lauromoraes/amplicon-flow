import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_development_image_is_pinned_and_uses_the_qiime_python():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "quay.io/qiime2/qiime2-workshop:2026.7@sha256:" in dockerfile
    assert "python -m pip install" in dockerfile
    assert "python -m pip check" in dockerfile
    assert "latest" not in dockerfile.lower()
    assert "curl" not in dockerfile and "wget" not in dockerfile


def test_direct_development_requirements_are_exact_and_unique():
    lines = [
        line.strip()
        for line in (ROOT / "docker/requirements-development.txt").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    assert lines == sorted(lines, key=str.casefold)
    assert all(line.count("==") == 1 for line in lines)
    names = [line.split("==", 1)[0].lower() for line in lines]
    assert len(names) == len(set(names))
    assert {"biopython", "papermill", "statannotations"} <= set(names)


def test_image_smoke_test_is_syntax_valid_and_checks_inherited_packages():
    path = ROOT / "docker/smoke_test.py"
    source = path.read_text(encoding="utf-8")
    ast.parse(source, filename=str(path))
    assert '"biom"' in source
    assert '"jupyterlab"' in source
    assert '"dada2", "demux"' in source
