from pathlib import Path

import nbformat


def test_template_notebooks_are_clean_and_parameterized():
    root = Path(__file__).resolve().parents[1]
    notebooks = sorted((root / "notebooks/templates").glob("*.ipynb"))
    assert notebooks
    for path in notebooks:
        nb = nbformat.read(path, as_version=4)
        params = []
        injected = []
        for cell in nb.cells:
            if cell.cell_type == "code":
                assert cell.execution_count is None and cell.outputs == []
            tags = cell.metadata.get("tags", [])
            if "parameters" in tags:
                params.append(cell)
            if "injected-parameters" in tags:
                injected.append(cell)
        assert len(params) == 1, path
        assert not injected, path
