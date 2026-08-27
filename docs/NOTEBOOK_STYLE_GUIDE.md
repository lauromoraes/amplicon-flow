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
