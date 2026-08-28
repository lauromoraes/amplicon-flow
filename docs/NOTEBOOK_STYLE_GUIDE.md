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

Validate inputs, software, and versioned container images before analysis. Installation and Docker builds belong to a separate preparation workflow. Record relevant tool, classifier, and reference-database identities for notebook provenance and reporting.
