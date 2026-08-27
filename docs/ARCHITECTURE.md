# AmpliconFlow Architecture

## Objective

Separate **scientific workflow content** from **execution infrastructure** without turning notebooks into thin wrappers. The central artifact remains the executed Jupyter notebook.

## Responsibilities

### Notebooks
Contain objective, scientific background, methodological rationale, Papermill parameters, method-defining calls, diagnostics, interpretation, limitations, outputs, and primary references.

### `src/ampliconflow`
Contains infrastructure only: YAML/schema validation, path construction, temporary-environment helpers, provenance collection, and notebook validation utilities.

### `ampliconflow`
Activates Conda, validates configuration, configures temporary storage, selects steps from YAML, runs Papermill, records provenance, and cleans successful-run temporaries.

## Experiment layout

```text
experiments/<experiment>/
├── parameters/
├── provenance/
├── notebooks/
├── artifacts/
├── figures/
└── reports/
```

## Migration rule

A scientific method should remain visible in the notebook. Do not move DADA2/QIIME/statistical logic into infrastructure helpers merely to shorten notebooks.
