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


def test_prepare_data_notebook_exposes_scientific_contract():
    root = Path(__file__).resolve().parents[1]
    path = root / "notebooks/templates/01-prepare-data.ipynb"
    notebook = nbformat.read(path, as_version=4)
    markdown = "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "markdown")
    code = "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "code")
    for section in range(1, 13):
        assert f"## {section}." in markdown
    assert "Artifact.import_data" in code
    assert "SingleEndFastqManifestPhred33V2" in code
    assert "PairedEndFastqManifestPhred33V2" in code
    assert "demux_actions.summarize" in code
    assert "filter_samples" not in code
    assert "trim_" not in code
    assert "/mnt/" not in code and "/home/" not in code
    for cell in notebook.cells:
        if cell.cell_type == "code":
            compile(cell.source, f"{path}:{cell.id}", "exec")
