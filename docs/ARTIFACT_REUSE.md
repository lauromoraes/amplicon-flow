# Shared artifact reuse

## Status and scope

Cross-experiment reuse is an accepted architectural requirement. This document specifies the strategy; the shared store, configuration, and runtime behavior are not yet implemented.

Use a local or shared-filesystem artifact store independent of experiment outputs and temporary storage. Start with expensive classifiers/reference resources and one validated pipeline step; extend to import, DADA2, and downstream analyses only after their dependency contracts are tested. No database or cloud service is required for the first implementation.

## Step contract and identity

Each eligible step declares its input roles, result-affecting parameters, relevant environment, reusable outputs, validation rules, and report contribution. Reuse is opt-in per step, not inferred from file existence.

Derive a lookup key from a canonical recipe containing:

- hashes of all effective scientific inputs, including consumed metadata, filters, and reference resources;
- effective result-affecting parameters, including defaults and random seeds where applicable;
- relevant tool/plugin versions and container identity;
- a version or digest of the step implementation and its relevant dependencies;
- the recipe schema version.

Names, absolute paths, modification times, experiment identifiers, and QIIME artifact identifiers alone are insufficient evidence of equivalence. Hash file bytes conservatively in the initial implementation; equivalent artifacts with different archive bytes may miss reuse safely. Semantic equivalence is a separate future feature.

Do not invalidate all artifacts for a documentation-only change by using the global Git commit as the sole implementation identity. Retain that commit as provenance, while explicitly tracking changes in scientific code and its dependencies. Parameter exclusions must be justified and tested; uncertain dependencies should invalidate reuse rather than risk an incorrect hit.

The recipe key identifies a computation, not necessarily a unique result. Associate each published result with its own immutable identity and output checksums. A forced recomputation must not overwrite an earlier result with the same recipe, especially for nondeterministic tools.

## Store entries and publication

Each entry contains outputs and a manifest recording recipe/key, checksums, artifact types, completion/validation status, producer execution, tool/database identities, and links to scientific documentation and reporting content. Treat published entries as read-only; consumers must never modify shared files in place.

Write into a private staging area, validate completeness and checksums, then publish atomically. Use a lock per recipe to avoid duplicate work and recheck availability after acquiring it. Readers only accept completed, validated entries. Incomplete, corrupt, incompatible, or unverifiable entries are not cache hits.

Validate the chosen filesystem's locking and atomic-publication behavior before supporting concurrent runs. Lock recovery after interruption must not delete another active producer's files. Staging cleanup and published-artifact deletion have separate policies from pipeline temporary cleanup.

## Consumer policy

Proposed configuration, **not yet accepted by the runtime as an implemented feature**:

```yaml
reuse:
  policy: prefer
  store: /path/to/shared/ampliconflow-artifacts
  publish: true
```

- `prefer`: reuse a matching valid result; otherwise compute.
- `require`: require a matching valid result; fail clearly if none exists.
- `off`: bypass lookup and compute.

Publication is independent of lookup policy: `off` may publish a new immutable result when enabled. Plan per-step overrides and explicit selection of a result when a recipe has multiple candidates. Concrete fields, precedence, defaults, and candidate-selection rules remain to be finalized in the YAML/schema work. Machine-specific store locations must remain external to committed scientific templates.

## Experiment provenance and reporting

Record whether each result was computed or reused, its recipe/result identity, checksum verification, producer execution, and the current consumer execution. The experiment initially references shared files; it must not pretend those files are locally owned or remove them during cleanup.

On a reuse hit, still produce a current-experiment record and report contribution. Label the step as reused and retain the source executed notebook/provenance; do not present an old notebook as freshly executed. Reuse scientific content only when its dependencies match. Rebuild experiment-specific captions, context, grouping, and interpretation when needed rather than copying another experiment's narrative blindly.

Reporting must distinguish deliberately omitted analyses from reused analyses: an omitted analysis has no result section, while a reused analysis can appear with explicit attribution. Reuse does not eliminate the need for QC assessment.

## Retention, export, and Git

Pipeline temporary cleanup must never delete published store entries. Deletion is explicit and checks known experiment references. A shared store may have consumers outside the current project: unknown references must not be interpreted as permission for automatic garbage collection. Retention/registration mechanisms remain to be designed.

Provide a future self-contained experiment export that materializes referenced artifacts, records checksums, and includes provenance/report inputs. Plain references save storage during normal work but are not sufficient for long-term independent archival.

Keep store payloads outside Git. The project `.gitignore` excludes `*.qza` at any depth. Ignore rules do not remove previously tracked files or prevent an explicit `git add -f`; the implemented repository-policy check rejects tracked `.qza` files in structural CI. It does not inspect historical commits or prevent upload before CI runs. Do not rewrite historical commits as part of this strategy.

Producer and consumer executions use distinct `run_id` values under the target [execution contract](EXECUTION_CONTRACT.md). Shared entries remain independent of either run's temporary storage and are never deleted by run cleanup.

## Initial implementation and acceptance

1. Finalize recipe/manifest schemas, step eligibility, policy precedence, and output validation.
2. Implement filesystem lookup, checksum verification, locking, staging, and immutable publication.
3. Integrate classifier reuse and one pipeline step with experiment/report provenance.
4. Test matching inputs, changed inputs/parameters/versions, missing/corrupt/incomplete entries, `require` failure, recomputation, and concurrent producers.
5. Verify that two experiments can share a valid result without copying large payloads, and that either experiment's temporary cleanup leaves it intact.
6. Validate reference tracking and self-contained export before claiming independent archival support.

Tests must verify both correct reuse and safe refusal to reuse. The first scientific validation dataset and eligible pipeline step are still to be selected.
