# AmpliconFlow

**AmpliconFlow** is a reproducible, notebook-centered workflow for **amplicon sequencing analysis** using **QIIME 2**, **Papermill**, and complementary statistical and functional analysis tools.

The project is designed around a simple principle: analytical notebooks are not disposable wrappers. They are first-class scientific documents that preserve methods, parameters, figures, quality-control decisions, interpretation, provenance, and primary references.

> **Status:** early 2.0 architecture. Analytical steps from the previous project are being migrated progressively and validated one at a time.

The scaffold is in place; analytical notebooks and PDF reporting are not yet implemented. The legacy [microbiom project](https://github.com/lauromoraes/microbiom) remains the functional reference.

## Next milestone and requirements

The next milestone is **contract consolidation, then Prepare Data + QC/DADA2**, validated against a representative legacy experiment. An accepted requirement is an **academic PDF report** covering objectives, methods, rationale, results, interpretation, limitations, references, and provenance for the steps actually executed. Each migrated notebook must contribute structured content; retain the report source and manifest alongside the PDF.

See [architecture and open decisions](docs/ARCHITECTURE.md), the [reporting contract](docs/REPORTING.md), and [migration milestones](docs/MIGRATION_PLAN.md). CLI consolidation, final YAML, supported environments, and the PDF renderer are not yet finalized. The command examples below describe the current scaffold.

## Core design

- Jupyter notebooks remain the primary analytical units.
- Papermill executes parameterized notebook templates.
- Scientific decisions remain visible in the notebooks.
- Reusable infrastructure lives in `src/ampliconflow`.
- Experiment configuration is defined in YAML and validated before execution.
- Each run preserves executed notebooks and computational provenance.
- Planned cross-experiment artifact reuse uses a validated shared store, separate from temporaries; see the [reuse strategy](docs/ARTIFACT_REUSE.md). The store is not yet implemented.
- Standalone notebooks, such as classifier-building workflows, are kept separate from pipeline steps.

## Repository structure

```text
ampliconflow/
├── ampliconflow                 # shell runner / primary repository CLI
├── README.md
├── LICENSE
├── pyproject.toml
│
├── notebooks/
│   ├── templates/               # Papermill pipeline notebooks
│   └── standalone/              # independent scientific utilities
│
├── src/
│   ├── ampliconflow/            # reusable infrastructure
│   └── external/                # R scripts, Dockerfiles, external wrappers
│
├── examples/
│   └── params-example.yaml
│
├── schemas/
│   └── parameters.schema.json
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── ARTIFACT_REUSE.md
│   ├── MIGRATION_PLAN.md
│   ├── REPORTING.md
│   └── NOTEBOOK_STYLE_GUIDE.md
│
└── tests/
```

## Command-line usage

The repository provides an `ampliconflow` runner.

Validate a configuration:

```bash
python -m ampliconflow.cli validate examples/params-example.yaml
```

Run an experiment:

```bash
./ampliconflow params-my-study.yaml rachis-qiime2-2026.7
```

After installing the package in editable mode:

```bash
python -m pip install -e .
```

the Python CLI can also be used as:

```bash
ampliconflow validate examples/params-example.yaml
ampliconflow run params-my-study.yaml rachis-qiime2-2026.7
```

## Temporary storage

A large temporary filesystem can be configured outside the repository:

```bash
export AMPLICONFLOW_TEMP_DIR=/path/to/large/tmp/ampliconflow
```

If it is not defined, the project-local `.tmp/` directory is used.

Temporary files are isolated by experiment. Successful runs clean their temporary directory automatically; failed runs preserve it for debugging.

## Notebook philosophy

Every pipeline notebook should contain:

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

Scientific method calls remain visible in notebooks. Infrastructure-only code should be moved to `src/ampliconflow`.

## Scope

AmpliconFlow is intended specifically for **amplicon sequencing workflows**, including marker-gene analyses such as:

- 16S rRNA;
- ITS;
- 18S rRNA;
- other targeted marker regions.

It is not intended as a shotgun metagenomics workflow.

## Migration strategy

The analytical migration is intentionally incremental:

1. prepare data;
2. quality control / DADA2;
3. rarefaction;
4. metataxonomy;
5. diversity;
6. abundance;
7. LEfSe;
8. PICRUSt2;
9. ANCOM-BC2;
10. reporting.

Each step is migrated only after the preceding architecture and validation tests are stable.

## License

MIT License. See `LICENSE`.
