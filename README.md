# AmpliconFlow

**AmpliconFlow** is a reproducible, notebook-centered workflow for **amplicon sequencing analysis** using **QIIME 2**, **Papermill**, and complementary statistical and functional analysis tools.

The project is designed around a simple principle: analytical notebooks are not disposable wrappers. They are first-class scientific documents that preserve methods, parameters, figures, quality-control decisions, interpretation, provenance, and primary references.

> **Status:** early 2.0 architecture. Analytical steps from the previous project are being migrated progressively and validated one at a time.

The scaffold and the first Prepare Data notebook are in place; scientific acceptance, later analytical notebooks, and PDF rendering are not yet complete. The legacy [microbiom project](https://github.com/lauromoraes/microbiom) remains the functional reference.

## Next milestone and requirements

The next milestone is **contract consolidation, then Prepare Data + QC/DADA2**, validated against a representative legacy experiment. An accepted requirement is an **academic PDF report** covering objectives, methods, rationale, results, interpretation, limitations, references, and provenance for the steps actually executed. Each migrated notebook must contribute structured content; retain the report source and manifest alongside the PDF.

See [architecture and open decisions](docs/ARCHITECTURE.md), the [reporting contract](docs/REPORTING.md), the [selected reference datasets](docs/REFERENCE_DATASETS.md), and [migration milestones](docs/MIGRATION_PLAN.md). CLI consolidation, final YAML, supported environments, and the PDF renderer are not yet finalized. The command examples below describe the current scaffold.

## Core design

Unique runs, parameter snapshots, lifecycle status, run-scoped temporaries, and the first dependency/preflight contracts are implemented. Prepare Data and Quality Control have explicit artifact contracts; later scientific contracts and recorded decisions remain pending in the [execution contract](docs/EXECUTION_CONTRACT.md). `.qza` files are normal project artifacts: there is no extension-based Git ignore rule or CI prohibition. Contributors may intentionally version suitable fixtures or artifacts, while deciding separately how to store very large data.

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
│   ├── EXECUTION_CONTRACT.md
│   ├── MIGRATION_PLAN.md
│   ├── REFERENCE_DATASETS.md
│   ├── REPORTING.md
│   └── NOTEBOOK_STYLE_GUIDE.md
│
├── validation/
│   └── reference-datasets.yaml # pinned scientific acceptance sources
│
└── tests/
```

## Command-line usage

The repository provides an `ampliconflow` runner.

List the pinned scientific acceptance datasets, or acquire one explicitly into an empty local
destination:

```bash
python -m ampliconflow.cli reference-data list
python -m ampliconflow.cli reference-data fetch pd-mice-2024.10 data/reference/pd-mice-2024.10
```

Acquisition verifies the pinned byte size and SHA-256 of every source, safely extracts supported
archives, normalizes metadata/manifests, records a hashed inventory, and publishes the completed
directory atomically. It never runs automatically during `plan`, `preflight`, or `run`, and it
refuses an existing destination.

Validate a configuration:

```bash
python -m ampliconflow.cli validate examples/params-example.yaml
```

Resolve contracts without accessing data or allocating a run:

```bash
python -m ampliconflow.cli plan examples/params-example.yaml --json
```

Inside the intended activated QIIME 2 environment, perform the read-only preflight:

```bash
python -m ampliconflow.cli preflight params-my-study.yaml
```

Preflight checks the selected templates and active Python/kernel/QIIME/Papermill environment,
metadata and manifest structure/sample correspondence, FASTQ readability/pairing, explicit artifact
hash/type, and storage readiness. It does not install software, pull images, execute notebooks, or
allocate a run. `run` performs this preflight automatically after activating Conda.

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

## Isolated executions

Each invocation creates `experiments/<experiment>/runs/<run_id>/` under the application checkout. The ID combines a UTC timestamp and UUID; an optional `--run-id ID` can be passed to either run command. An existing ID is refused, never overwritten. Existing legacy experiment directories are left untouched.

Each run contains `parameters/original.yaml`, path-normalized `parameters/effective.yaml`, the resolved `provenance/plan.json`, successful `provenance/preflight.json`, SHA-256 hashes and source fingerprints, executed `notebooks/`, `artifacts/`, `figures/`, and `reports/`. `run.json` records current/final status; `run-start.json` and `run-end.json` retain lifecycle snapshots. Failed or cancelled attempts preserve their outputs and diagnostics.

Known input paths (`inputs.metadata_file`, `inputs.manifest_file`, `taxonomy.classifier_file`) and `base_dir` resolve relative to the original YAML, not to the new notebook working directory. This does not relocate the output root: it remains the application checkout for now. Unknown future path fields and scientific defaults require the pending full parameter contract.

Notebook processes start in the run directory and receive `AMPLICONFLOW_RUN_ID`, `AMPLICONFLOW_RUN_DIR`, and `AMPLICONFLOW_PROJECT_DIR`. Templates must save results under the run directory, never reconstruct a shared experiment output path. This is orchestration isolation, not an OS sandbox against notebook code deliberately writing elsewhere.

The initial implementation is tested on Linux/WSL with synthetic notebook executors. Real QIIME 2/Papermill scientific acceptance remains pending; the analytical templates do not exist yet, so preflight rejects the example without allocating a run. Automatic resume/retry linking and the shared reuse store are not implemented. Quality Control can already consume an explicitly supplied, checksum-pinned compatible demultiplexed artifact; this is a controlled input binding, not automatic cache discovery.

## Temporary storage

A large temporary filesystem can be configured outside the repository:

```bash
export AMPLICONFLOW_TEMP_DIR=/path/to/large/tmp/ampliconflow
```

If it is not defined, the project-local `.tmp/` directory is used.

Temporary files use `<temp-base>/<experiment>/<run_id>/`. Successful runs remove only their owned directory after checking its ownership marker; failed/cancelled runs preserve it. Other runs, experiment outputs, and shared artifacts are not cleaned. SIGINT/SIGTERM are recorded as cancellation; an uncatchable kill or power loss can leave the last `running` status for manual investigation.

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
