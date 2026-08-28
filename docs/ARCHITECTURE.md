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

## Baseline and current status

The legacy [microbiom project](https://github.com/lauromoraes/microbiom) remains the functional reference during incremental migration. AmpliconFlow focuses on amplicon sequencing, not shotgun metagenomics.

The scaffold provides a shell runner, Python CLI, initial YAML/schema, basic provenance, temporary-directory helpers, a notebook template, and structural CI. Analytical steps and academic reporting are not yet implemented. The following sections describe the target, not completed functionality.

## Accepted requirements

- Preserve notebooks and Papermill as the scientific execution model.
- Generate an academic PDF with objectives, methodology, rationale, results, interpretation, limitations, references, and provenance. Each migrated step contributes explicitly; see [Academic reporting](REPORTING.md).
- Select steps through validated YAML without editing the runner.
- Keep machine-specific paths outside scientific templates and prepare pipeline temporaries before kernel startup. Standalone resource-building notebooks manage their own local temporary space.
- Preserve executed notebooks and execution parameters/provenance. Clean owned temporary data only after success and retain it on failure.
- Keep the legacy workflow operational while validating migrated steps against representative legacy outputs.

## CLI and YAML consolidation

The target public interface is `ampliconflow validate ...` and `ampliconflow run ...`. Currently the shell runner and installed Python command share a name. Choose an internal renamed shell runner or Python orchestration in a separate implementation change; neither option is finalized here.

The current YAML/schema is a bootstrap. Before migrating the first notebook, define path-resolution rules, manifest/metadata validation, sequencing layout, per-step parameters, and required fields for selected steps. Also define prerequisite artifacts, rerun/overwrite behavior, preservation of earlier execution records, and reporting metadata.

Step identity must remain stable when selecting subsets. Review the current runner's positional notebook numbering as part of this contract. Resume/start/stop controls remain possible extensions, not implemented requirements.

## Environment policy

Prepare dependencies separately from analysis. Use versioned Docker images rather than `latest`, and record resolved image digests when available. Notebooks check prerequisites and explain how to prepare missing tools; they should not download/build tools during analysis. Migrate external R scripts, Dockerfiles, and wrappers alongside their analytical step in `src/external`.

Extend basic provenance with relevant plugin/tool versions, container identity, classifier/reference database identity, effective parameters, executed steps, and timestamps. The previously discussed QIIME 2/Rachis 2026.7 and Python 3.12 environment is a candidate validation baseline, not a newly imposed version pin.

Pipeline notebooks inherit temporary settings; standalone classifier-building notebooks must work without the runner. `QIIME_CACHE` is a project convention for passing a path, not an automatic QIIME 2 configuration: scientific calls must explicitly consume it through the appropriate option/API. Validate cleanup targets and ownership before deletion.

## Open decisions

- Final YAML/schema, path rules, prerequisites, and rerun semantics.
- Internal orchestration behind the single public CLI.
- Concrete report contribution schema/serialization and PDF renderer.
- Representative dataset, legacy baseline, comparison tolerances, and supported environments.

Keep CI lightweight and structural. Scientific acceptance requires a separate representative execution; see [Migration milestones](MIGRATION_PLAN.md).
