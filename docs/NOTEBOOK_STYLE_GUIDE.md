# Notebook Style Guide

Each pipeline notebook should follow:

```text
# Step N — Analysis name
## 1. Objective
## 2. Scientific background
## 3. Methodological rationale
## 4. Inputs
## 5. Parameters
## 6. Computational provenance
## 7. Analysis
## 8. Results and quality-control assessment
## 9. Interpretation
## 10. Outputs
## 11. Limitations
## 12. References
```

Each template must contain exactly one code cell tagged `parameters`. Templates committed to Git must have null execution counts, empty outputs, no machine-specific absolute paths, and no `injected-parameters` cells.

Keep method-defining calls visible. Prefer primary scientific publications for methods and databases. State acceptance criteria before presenting diagnostic results whenever practical.

## Reporting contributions

Every migrated pipeline notebook must follow the [academic reporting contract](REPORTING.md). Describe its contribution under Outputs and produce structured methods, effective parameters, observed results, QC assessment, interpretation/limitations, references, and artifact links. This supplements the notebook's scientific narrative rather than replacing it.

Keep methods, measured results, and interpretation distinguishable. Export report figures/tables with captions instead of relying only on inline displays. Record warnings and unmet criteria explicitly; never invent missing results or silently reuse contributions from earlier runs.

## Execution prerequisites

Pipeline templates consume the temporary environment prepared before kernel startup. Standalone notebooks configure their own local environment without requiring the runner. Connect the configured cache path explicitly to relevant scientific calls.

Pipeline templates receive `AMPLICONFLOW_RUN_ID`, `AMPLICONFLOW_RUN_DIR`, and `AMPLICONFLOW_PROJECT_DIR`. Save artifacts, figures, and reports beneath `AMPLICONFLOW_RUN_DIR`; do not reconstruct experiment-wide output paths. Input paths supplied by the runner are normalized relative to the source YAML. The notebook's working directory is the isolated run directory.

`.qza` files are normal scientific inputs/outputs. The project has no extension-based Git or CI restriction; notebooks must not restrict storage or versioning choices. Review artifacts individually for size, provenance, licensing, and sensitive contents.

Validate inputs, software, and versioned container images before analysis. Installation and Docker builds belong to a separate preparation workflow. Record relevant tool, classifier, and reference-database identities for notebook provenance and reporting.

## Reusable artifacts

Use the target [execution contract](EXECUTION_CONTRACT.md) for run identity, prerequisite checks, scientific decision records, and report metadata controls. Record the evidence and rationale for human choices rather than inventing them from parameter values.

Declare whether the step supports [artifact reuse](ARTIFACT_REUSE.md), its scientific input dependencies, result-affecting parameters, implementation identity, and reusable outputs. On a reuse hit, preserve source provenance and produce an explicit current-experiment reuse record/report contribution; never imply that scientific computation ran again. Shared outputs are immutable and must not be removed by notebook cleanup.
