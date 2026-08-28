# Execution, dependencies, and preflight

## Status

This is the target contract for the next infrastructure implementation. Run isolation, dependency resolution, preflight, decision recording, and scientific fixtures are not implemented yet. The current shell runner still writes directly under the experiment directory. The repository artifact-policy check is implemented separately and runs in structural CI.

## Experiment versus run

An experiment identifies a study/configuration context; a `run_id` identifies one execution attempt. Every invocation that executes or reuses scientific steps creates a new unique run. Do not overwrite a previous attempt, even when parameters are unchanged. A retry links to its preceding attempt without rewriting its records. Automatic resume remains out of scope for the initial implementation.

Target layout:

```text
experiments/<experiment>/runs/<run_id>/
├── parameters/
├── provenance/
├── notebooks/
├── artifacts/
├── figures/
└── reports/
```

Store the original parameter snapshot and normalized effective parameters, their hashes, step plan, timestamps, and status. Never accept `.`/`..`, path traversal, or identifiers resolving outside the owned root. Allocate run directories exclusively so a collision cannot overwrite another run. Record working-tree changes as well as commit identity; a commit alone cannot identify uncommitted scientific code.

Use run-scoped temporaries, not only experiment-scoped temporaries, to isolate concurrent attempts. Shared reusable artifacts live outside this lifecycle. Cleanup operates only on owned run temporary paths, after success; failures preserve diagnostics. Interrupted runs remain identifiable and are never silently reported as successful.

Initial state vocabulary: runs are planned, running, completed, failed, or cancelled; steps additionally distinguish reused and blocked. An omitted step is not a successful or reused step. An unmet scientific review gate blocks downstream work until explicitly resolved rather than being silently accepted as success. Exact storage schema and interruption recovery are implementation decisions.

## Step dependencies

Define a registry with stable step identifiers independent of execution position. Each entry declares input roles/types, required predecessor outputs or explicitly supplied compatible artifacts, result-affecting parameters, outputs, execution environment, QC criteria, reporting contribution, and reuse eligibility.

Resolve the selected steps into a dependency-valid plan before computation. Reject unknown steps, duplicates, cycles, missing inputs, incompatible artifacts, and ambiguous input providers. Do not silently add unrequested scientific analyses. An isolated step is valid only if all prerequisites are supplied explicitly or resolved through validated reuse. Outputs from unexecuted predecessors cannot be presumed to exist.

Resolve input paths relative to the YAML file's directory unless absolute. Resolve configured output/store roots once, then record portable logical references alongside local execution paths. These rules supersede the scaffold's implicit working-directory assumptions once implemented; the schema must make them explicit.

## Preflight and execution-time checks

Preflight produces structured errors, warnings, and a resolved plan before starting expensive scientific work:

- Validate configuration, identifiers, paths, readable input files, sample IDs, sequencing layout, paired-read consistency, and manifest/metadata correspondence. Extra/missing samples require an explicit policy; never silently discard them.
- Validate requested tools/plugins, environment identity, notebook kernel, reference resources, and required prebuilt container images. Do not install dependencies or build images during preflight.
- Check output/temp/store permissions, free space, and overlapping/unsafe cleanup paths. Free-space estimates are advisory unless a known minimum is configured; they do not guarantee sufficient space for an entire run.
- Resolve reuse candidates and verify required integrity/compatibility. `require` fails if no valid candidate exists. Do not compute keys for future inputs that have not yet been generated.
- Validate scientific decision requirements and metadata-publication policy.

Outputs produced later in the run are checked immediately before their consumers execute. Revalidate relevant input integrity, resources, and reuse assumptions at execution time: preflight cannot guarantee that files or shared resources remain unchanged. A validation-only command must not run notebooks, publish artifacts, or allocate a scientific run; bounded write probes, if needed, must be explicitly identified and cleaned up.

## Human scientific decisions

Record decisions such as truncation lengths, rarefaction depth, sample exclusion, and comparison/reference groups. Each decision record links its run/step, selected value, rationale, supporting diagnostic/artifact checksums, actor, timestamp, and whether it was manually supplied or derived by a documented rule.

Do not fabricate rationale for a supplied parameter. Missing required review creates a blocked/pending-review outcome. Changing a decision creates a new attempt or downstream execution record and invalidates affected reuse recipes; do not edit historical decisions. The initial implementation can consume explicit decision records from configuration without requiring a new interactive UI.

## Dataset and scientific validation

Select a small public or synthetic dataset with documented origin/license, stable acquisition reference, checksums, marker/read layout, metadata dictionary, legacy revision/environment, and expected acceptance criteria. Keep large FASTQ and all `.qza` outputs outside Git; commit only safe small text fixtures, acquisition instructions, and expected summaries. Dataset selection remains open.

Separate structural tests (fast CI, no QIIME installation) from scientific integration runs in a pinned environment. Compare semantic outputs and scientific metrics rather than requiring identical archive bytes. Define tolerances before reviewing results and document version-driven differences. Cover sample mismatch, invalid parameters, failed/interrupted execution, repeated run isolation, dependencies, and reuse invalidation in addition to a successful example.

## Privacy and repository hygiene

Do not publish arbitrary input metadata, credentials, absolute host paths, or participant identifiers in logs/reports by default. Define an explicit allowlist for report metadata; use pseudonymous sample labels where appropriate. Local raw inputs and detailed provenance may still contain sensitive data and require restricted storage. Hashes and pseudonyms alone do not guarantee anonymity. Review notebooks, captions, manifests, and report exports before sharing; this is not yet an implemented redaction guarantee.

The `.gitignore` excludes `.qza` files. `python -m ampliconflow.repository_policy` additionally inspects the Git index and fails for tracked `.qza` paths, including force-added files, without reading their payloads. Structural CI runs it and the associated tests. It checks the current index, not historical commits or external storage; CI flags a violation but cannot prevent a local commit or remote upload by itself. Requiring a passing check for merge needs repository branch-protection configuration, not changed here.

## Implementation order

1. Implement run identity, exclusive directory creation, immutable snapshots, and run-scoped cleanup with tests.
2. Implement the registry/dependency plan and YAML path/parameter contract.
3. Implement preflight and execution-time validation with structured diagnostics.
4. Connect decision records, report contributions, and shared-artifact provenance.
5. Validate Prepare Data + QC/DADA2 on the selected scientific fixture.
