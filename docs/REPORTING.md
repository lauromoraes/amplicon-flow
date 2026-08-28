# Academic reporting

## Status and objective

Academic PDF reporting is an accepted AmpliconFlow 2.0 requirement, not an implemented feature. It must combine objectives, methodology, methodological rationale, scientific references, and the results actually obtained in an experiment.

This document defines the semantic contribution expected from each step. Concrete field names, serialization, validation schema, and rendering engine remain open. Quarto, Pandoc/LaTeX, or other renderers are not yet selected dependencies.

## Responsibilities

1. Each executed notebook produces scientific outputs and an explicit structured report contribution.
2. An aggregator validates contributions and combines them with run parameters and provenance.
3. A renderer produces the PDF and preserves its source and manifest.

The report is not simply a PDF export of notebook cells. Scientific calls and explanations stay visible in notebooks; aggregation and rendering belong to infrastructure. Do not reconstruct scientific meaning from arbitrary notebook outputs only at the end.

## Per-step semantic contract

Every migrated step must describe and eventually emit:

| Element | Expected content |
| --- | --- |
| Identity and execution | Stable step identity, experiment/execution association, status, timestamps. |
| Objective and methods | Objective, methodology, rationale, assumptions, effective parameters. |
| Inputs and provenance | Input/artifact references, software and database/classifier identity, link to run provenance. |
| Results | Observed metrics and findings, units and sample/group scope where relevant. |
| Figures and tables | Exported file references, captions, producing step. |
| Quality assessment | Acceptance criteria, observed diagnostics, warnings, outcome or need for human review. |
| Interpretation and limitations | Output-grounded interpretation, caveats, unresolved questions. |
| References | Traceable primary scientific citations and persistent identifiers where available. |
| Outputs | Resulting artifacts and executed notebook references. |

Elements may be explicitly not applicable with a reason. Missing content must never become invented results. Distinguish measured values from interpretation and retain warnings. File references should be portable, and execution association must prevent mixing contributions from earlier runs.

### First migration examples

- **Prepare Data:** manifest/metadata checks, sample/read layout, sample counts, imported artifacts, excluded inputs and reasons where applicable.
- **QC/DADA2:** effective parameters and rationale, read-retention statistics, merging/chimera diagnostics, ASV counts, sequence-length summaries, figures, and QC limitations.

These are content expectations, not fixed field names or universal thresholds. Establish comparison criteria for the representative experiment before accepting migration.

## Aggregation and deliverables

Include only analyses actually executed. Do not create empty LEfSe/PICRUSt2 sections when those steps were omitted. Failed or incomplete runs must never be represented as complete successful analyses; support for partial PDFs remains open.

An analysis whose validated outputs were explicitly reused is not an omitted analysis. Include it with a clear reused designation, recipe/result identity, original producer execution, and current consumer provenance. Generate a current-experiment contribution without presenting a source notebook as newly executed or blindly copying experiment-specific interpretation. See [Artifact reuse](ARTIFACT_REUSE.md).

Separate Methods, Results, and Interpretation. Include study/input context, computational provenance, limitations, references, and useful appendices. Preserve commit identity, parameter-file hash, relevant software/plugin versions, database/classifier identity, parameters, executed steps, and timestamps.

The scaffold currently reserves `experiments/<experiment>/reports/`. Under the target [execution contract](EXECUTION_CONTRACT.md), outputs belong in `experiments/<experiment>/runs/<run_id>/reports/`, so reports from repeated attempts cannot overwrite each other. Report metadata must follow an explicit publication allowlist, and scientific decisions must link to their supporting diagnostics.

Planned outputs in the run's report directory:

- `academic-report.pdf`;
- regenerable/editable report source, in a format still to be selected;
- report manifest linking contributions, figures/tables, source data, and execution provenance.

These are logical names. Resolve versioning/overwrite rules with the execution contract so earlier runs are not lost or mixed.

## Acceptance

- Every migrated analytical step has a validated contribution linked to its execution.
- Reported metrics, figures, and tables agree with executed notebooks and exported outputs.
- Omitted steps, failures, missing required contributions, and QC warnings are handled explicitly.
- Citations and artifact references resolve; retained report inputs, source, and manifest permit regeneration without rerunning scientific analyses.
- Inspect the PDF for readable figures/tables, citations, pagination, and clipped content.

Define the concrete schema before accepting the first migration. Implement full aggregation and PDF rendering in the reporting milestone, but require contributions from the first analytical step onward.
