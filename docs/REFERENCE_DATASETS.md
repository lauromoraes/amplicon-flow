# Reference datasets

## Decision

AmpliconFlow uses two version-pinned QIIME 2 tutorial datasets for the first scientific
acceptance milestone. The machine-readable registry with observed sizes and SHA-256 values is
[`validation/reference-datasets.yaml`](../validation/reference-datasets.yaml). Large source files
are fetched into a local validation workspace; preflight and normal runs never download them.

The QIIME 2 Tutorial Data distribution is listed as BSD-3-Clause in the
[Registry of Open Data on AWS](https://registry.opendata.aws/qiime2/). Each dataset must also cite
its underlying study. Checksums were computed from files retrieved on 2026-08-28. A changed
upstream payload is a review event, not an instruction to update a checksum automatically.

## Primary: Parkinson's mice, QIIME 2 2024.10

This is the first end-to-end acceptance dataset for Prepare Data and Quality Control. It contains
48 demultiplexed single-end FASTQ files in a 21.5 MB archive, corresponding metadata, and a QIIME
manifest. It directly exercises the manifest import contract and `dada2 denoise-single`. The
official tutorial imports `SampleData[SequencesWithQuality]` and uses a truncation length of 150.

Required deterministic normalization:

- verify all three source checksums before extraction;
- safely extract without accepting absolute paths, `..`, links, or overwrites;
- rename the metadata ID header `sample_name` to `sample-id`;
- replace `$PWD` in the manifest with literal absolute paths in the local workspace;
- require exact equality between the 48 metadata and manifest sample IDs.

These transformations change representation, not the samples or scientific data. Normalized files
receive their own checksums in the future acquisition report. The tutorial is historical 2024.10
documentation, so compatibility with the target 2026.7 environment must be demonstrated.

Sources: [QIIME 2 Parkinson's Mouse tutorial](https://docs.qiime2.org/2024.10/tutorials/pd-mice/)
and [Sampson et al. (2016)](https://doi.org/10.1016/j.cell.2016.11.018).

## Secondary: Atacama demultiplexed paired-end, QIIME 2 2024.10

This is the paired-end and explicit-artifact acceptance dataset. The 28.8 MB QIIME artifact has
type `SampleData[PairedEndSequencesWithQuality]`, contains 54 FASTQ pairs, and has official tutorial
outputs for comparison. It supports two tests:

1. Quality Control consumes the checksum-pinned `.qza` directly.
2. A controlled acquisition step exports its paired FASTQ files, creates a V2 manifest, subsets
   the 74-sample source metadata to the artifact's 54 IDs, and runs Prepare Data again.

The official DADA2 exercise trims 13 bases from both directions and uses truncation length 150 for
both. These are baseline decisions, not universal defaults. Export/reimport is not expected to
reproduce archive bytes or UUIDs; acceptance compares type, sample set, reads, and metrics.

Sources: [QIIME 2 Atacama tutorial](https://docs.qiime2.org/2024.10/tutorials/atacama-soils/)
and [Neilson et al. (2017)](https://doi.org/10.1128/mSystems.00195-16).

## Acceptance layers

| Layer | Dataset | Required evidence |
|---|---|---|
| Structural CI | generated tiny fixtures | schema, paths, failures; no QIIME claim |
| Single-end scientific smoke | Parkinson's mice | import, 48 samples, type, DADA2 outputs |
| Paired-end scientific smoke | Atacama | 54 samples, paired type, DADA2 outputs |
| Explicit artifact input | Atacama `.qza` | checksum/type and consumer provenance |
| Legacy comparison | owner-provided experiment | parameter and metric comparison with `microbiom` |

Public datasets validate the workflow but cannot prove equivalence with an unidentified historical
experiment. That final layer requires an owner-selected legacy parameter file and input/result
provenance; sensitive data need not be committed.

## Metrics to lock before execution

- source and normalized-input checksums;
- sample IDs and per-sample input reads;
- effective DADA2 parameters and environment versions;
- per-phase DADA2 read counts and retention proportions;
- output sample count, total frequency, feature count, and representative-sequence count;
- semantic types and checksums for every output;
- predefined tolerances for metrics that can change across QIIME/DADA2 versions.

Exact `.qza` byte equality is not a criterion because UUIDs and provenance differ across legitimate
runs. No tolerance will be chosen after a failure merely to make it pass.
