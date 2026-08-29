# Execution, dependencies, and preflight

## Status

Run isolation is implemented: exclusive `run_id` directories, original/effective parameter snapshots with hashes, source fingerprints, lifecycle/step status, run-scoped temporary ownership, and SIGINT/SIGTERM handling. Prepare Data and Quality Control now have explicit versioned contracts, deterministic dependency planning, and preflight/execution-time artifact checks. Prepare Data has its first executable notebook and mandatory report contribution; scientific execution in QIIME 2 remains pending. The shell activates Conda; Python owns orchestration. Tests use simulated scientific execution, not a validated QIIME 2 run. Later-step contracts, container checks, decision recording, and scientific fixtures remain pending. The project imposes no Git restriction based on the `.qza` extension.

## Experiment versus run

An experiment identifies a study/configuration context; a `run_id` identifies one execution attempt. Execution creates a new unique run without overwriting previous attempts, even when parameters are unchanged. Explicit existing IDs are refused. Reuse, retry linking, and automatic resume are not implemented; future retries should link to their preceding attempt without rewriting its records.

Implemented layout:

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

The runner reads the source YAML once, writes snapshots exclusively in the new run, and passes only the effective snapshot to Papermill. It checks snapshot hashes after each notebook to detect accidental mutation. These are application-level write-once snapshots, not filesystem-enforced immutable files. Effective parameters currently normalize known paths but do not materialize unknown notebook defaults. Provenance includes source hashes for the bootstrap, package Python files, template notebooks, schema files, and package metadata; it does not snapshot every dependency or external tool.

Validation errors and ID collisions are rejected before allocation. Once allocated, ordinary execution/setup failures receive a failed final record where the filesystem remains writable. Uncatchable termination, storage failure, or power loss cannot guarantee a final record; investigate a lingering `running` status rather than assuming completion. Interrupted allocation may leave a reserved ID that must not be reused silently.

Use run-scoped temporaries, not only experiment-scoped temporaries, to isolate concurrent attempts. Shared reusable artifacts live outside this lifecycle. Cleanup operates only on owned run temporary paths, after success; failures preserve diagnostics. Interrupted runs remain identifiable and are never silently reported as successful.

Initial state vocabulary: runs are planned, running, completed, failed, or cancelled; steps additionally distinguish reused and blocked. An omitted step is not a successful or reused step. An unmet scientific review gate blocks downstream work until explicitly resolved rather than being silently accepted as success. Exact storage schema and interruption recovery are implementation decisions.

## Step dependencies

Define a registry with stable step identifiers independent of execution position. Each entry declares input roles/types, required predecessor outputs or explicitly supplied compatible artifacts, result-affecting parameters, outputs, execution environment, QC criteria, reporting contribution, and reuse eligibility.

Resolve the selected steps into a dependency-valid plan before computation. Reject unknown steps, duplicates, cycles, missing inputs, incompatible artifacts, and ambiguous input providers. Do not silently add unrequested scientific analyses. An isolated step is valid only if all prerequisites are supplied explicitly or resolved through validated reuse. Outputs from unexecuted predecessors cannot be presumed to exist.

Resolve input paths relative to the YAML file's directory unless absolute. Resolve configured output/store roots once, then record portable logical references alongside local execution paths. These rules supersede the scaffold's implicit working-directory assumptions once implemented; the schema must make them explicit.

Implemented now: known input fields, explicit artifact paths, and `base_dir` resolve relative to the original YAML; run outputs remain under the application checkout. Prepare Data produces `demultiplexed_sequences`; Quality Control requires it and produces `table`, `representative_sequences`, and `denoising_stats`. An unselected producer must be replaced by an explicit compatible artifact with a required SHA-256. Ambiguous providers are rejected. The planner topologically orders only selected steps and never adds an analysis. Contracts for later steps fail as unsupported rather than being guessed.

Notebooks run with the run directory as their working directory and receive `AMPLICONFLOW_RUN_ID`, `AMPLICONFLOW_RUN_DIR`, `AMPLICONFLOW_PROJECT_DIR`, and `AMPLICONFLOW_PLAN_FILE`. All migrated templates must use the declared output locations. This is not an OS-level sandbox: arbitrary notebook code can still write elsewhere.

## Preflight and execution-time checks

Preflight produces structured errors, warnings, and a resolved plan before starting expensive scientific work:

- Validate configuration, identifiers, paths, readable input files, sample IDs, sequencing layout, paired-read consistency, and manifest/metadata correspondence. Extra/missing samples require an explicit policy; never silently discard them.
- Validate requested tools/plugins, environment identity, notebook kernel, reference resources, and required prebuilt container images. Do not install dependencies or build images during preflight.
- Check output/temp/store permissions, free space, and overlapping/unsafe cleanup paths. Free-space estimates are advisory unless a known minimum is configured; they do not guarantee sufficient space for an entire run.
- Resolve reuse candidates and verify required integrity/compatibility. `require` fails if no valid candidate exists. Do not compute keys for future inputs that have not yet been generated.
- Validate scientific decision requirements and metadata-publication policy.

Outputs produced later in the run are checked immediately before their consumers execute. Revalidate relevant input integrity, resources, and reuse assumptions at execution time: preflight cannot guarantee that files or shared resources remain unchanged. A validation-only command must not run notebooks, publish artifacts, or allocate a scientific run; bounded write probes, if needed, must be explicitly identified and cleaned up.

Implemented preflight is read-only and validates metadata/manifest structure, exact sample-set correspondence, FASTQ readability and pairing, template validity, active Python/kernel/Papermill/QIIME environment and DADA2 availability, explicit artifact checksum/declared semantic type, and output/temp readiness. It persists the successful report and resolved plan only after preflight, when the run is allocated. QIIME archive inspection validates the archive identity and declared type, not its complete scientific payload. FASTQ content, external-artifact sample correspondence, containers, reference databases, and scientific thresholds remain later checks and are reported as limitations rather than overclaimed.

## Human scientific decisions

Record decisions such as truncation lengths, rarefaction depth, sample exclusion, and comparison/reference groups. Each decision record links its run/step, selected value, rationale, supporting diagnostic/artifact checksums, actor, timestamp, and whether it was manually supplied or derived by a documented rule.

Do not fabricate rationale for a supplied parameter. Missing required review creates a blocked/pending-review outcome. Changing a decision creates a new attempt or downstream execution record and invalidates affected reuse recipes; do not edit historical decisions. The initial implementation can consume explicit decision records from configuration without requiring a new interactive UI.

## Dataset and scientific validation

Select a small public or synthetic dataset with documented origin/license, stable acquisition reference, checksums, marker/read layout, metadata dictionary, legacy revision/environment, and expected acceptance criteria. Commit only redistributable, reviewed fixtures; whether a `.qza` belongs in Git depends on its purpose, size, license, and sensitivity rather than its extension. Large raw or generated data can still use external storage when appropriate. Dataset selection remains open.

Separate structural tests (fast CI, no QIIME installation) from scientific integration runs in a pinned environment. Compare semantic outputs and scientific metrics rather than requiring identical archive bytes. Define tolerances before reviewing results and document version-driven differences. Cover sample mismatch, invalid parameters, failed/interrupted execution, repeated run isolation, dependencies, and reuse invalidation in addition to a successful example.

## Privacy and repository hygiene

Do not publish arbitrary input metadata, credentials, absolute host paths, or participant identifiers in logs/reports by default. Define an explicit allowlist for report metadata; use pseudonymous sample labels where appropriate. Local raw inputs and detailed provenance may still contain sensitive data and require restricted storage. Hashes and pseudonyms alone do not guarantee anonymity. Review notebooks, captions, manifests, and report exports before sharing; this is not yet an implemented redaction guarantee.

The project does not ignore or reject files merely because their extension is `.qza`. Such artifacts may be committed when useful for development or scientific validation. Contributors remain responsible for reviewing file size, provenance, redistribution rights, and sensitive contents. Runtime output directories such as `experiments/`, and general local data directories such as `data/` and `classifiers/`, remain ignored because of their role and expected volume—not because they may contain `.qza` files.

## Implementation order

1. Implement run identity, exclusive directory creation, immutable snapshots, and run-scoped cleanup with tests.
2. Implement the registry/dependency plan and YAML path/parameter contract. **Initial Prepare Data/QC scope complete.**
3. Implement preflight and execution-time validation with structured diagnostics. **Initial Prepare Data/QC scope complete; extend with each migrated step.**
4. Connect decision records, report contributions, and shared-artifact provenance.
5. Validate Prepare Data + QC/DADA2 on the selected scientific fixture.
