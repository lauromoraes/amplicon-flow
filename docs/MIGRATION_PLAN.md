# Migration plan from microbiom to AmpliconFlow 2.0

The legacy `lauromoraes/microbiom` project remains the comparison baseline. No analytical step has yet been accepted as migrated.

## Milestone 0 — Consolidate contracts

- [x] Create the scaffold, initial YAML/schema, notebook guide, and structural CI workflow.
- [x] Document the academic PDF requirement and semantic [reporting contract](REPORTING.md).
- [x] Document the cross-experiment [artifact reuse strategy](ARTIFACT_REUSE.md).
- [x] Define the target [execution contract](EXECUTION_CONTRACT.md), including run isolation, dependencies, preflight, human decisions, and data safeguards.
- [x] Add a structural CI check rejecting tracked `.qza` files, including force-added artifacts.
- [ ] Validate these documented contracts with the project owner.
- [ ] Finalize YAML/path rules, stable step selection, prerequisites, and rerun behavior.
- [ ] Consolidate the public CLI and validate environment/temporary handling.
- [ ] Implement unique run directories, immutable snapshots, statuses, and run-scoped cleanup.
- [ ] Implement dependency planning and structured preflight/execution-time validation.
- [ ] Implement scientific decision records and explicit metadata-publication controls.
- [ ] Define the concrete report contribution schema and validation.
- [ ] Define reusable-step recipes/manifests, eligibility, policy precedence, and retention/export rules.
- [ ] Implement and test a shared-filesystem store for classifiers and one eligible pipeline step, including invalidation, integrity, concurrent publication, and provenance.
- [ ] Confirm a representative dataset, legacy revision/outputs, environments, and comparison criteria.
- [ ] Re-run structural tests, lint, shell checks, and CLI validation after infrastructure changes.

Documentation checkmarks do not imply executable reporting support or scientific validation. The PDF renderer remains open.

## Milestone 1 — Prepare Data + QC/DADA2

Migrate `01-prepare-data.ipynb`, followed by `02-quality-control.ipynb`, with reporting contributions from the outset. Validate manifest/metadata, imported artifacts, denoising outputs, read retention, ASV counts, and QC diagnostics against the representative legacy experiment. Record expected differences caused by version changes instead of requiring unexplained byte-for-byte identity.

Keep the legacy operational. Advance to subsequent analyses after this pair passes infrastructure and scientific acceptance.

## Acceptance for each notebook

A migrated notebook is accepted only when it:

1. follows the 2.0 notebook structure;
2. has exactly one Papermill `parameters` cell;
3. is output-free as a template;
4. contains no server-specific absolute paths;
5. validates inputs and parameters early;
6. keeps method-defining scientific code visible;
7. includes primary references;
8. documents acceptance criteria;
9. executes on a representative experiment;
10. is compared with the corresponding legacy output using recorded criteria;
11. emits a validated report contribution with traceable results, references, and exported figures/tables where applicable;
12. records relevant input/environment provenance and explicit warnings/limitations;
13. declares reuse eligibility and dependencies, and, if eligible, validates both reuse hits and invalidation while identifying reused results in provenance and reports.

## Migration order

- [ ] 01 Prepare data
- [ ] 02 Quality control / DADA2
- [ ] 03 Rarefaction analysis
- [ ] 04 Metataxonomy
- [ ] 05 Diversity analysis
- [ ] 06 Abundance analysis
- [ ] 07 LEfSe
- [ ] 08 PICRUSt2
- [ ] 09 ANCOM-BC2
- [ ] 10 Academic report aggregation, source/manifest preservation, and PDF rendering

Migrate external components alongside their analytical step, with versioned environments and separate preparation instructions. Use focused changes and review before merging; structural CI does not replace representative scientific execution.
