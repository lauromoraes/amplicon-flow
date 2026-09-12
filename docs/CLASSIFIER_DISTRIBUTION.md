# Distributing QIIME 2 classifiers

Large classifier artifacts are published as GitHub Release assets. They are not committed to Git,
and the local `classifiers/` directory remains ignored. Every pipeline configuration must pin the
release tag, asset filename, and SHA-256 digest.

## Publish a classifier

Install and authenticate the GitHub CLI once:

```bash
gh auth login
```

From the repository checkout on the server that contains the classifier:

```bash
bash scripts/publish-classifier-release.sh \
  /mnt/data/qiime2-classifiers/dev-gtdb-220/16S_GTDB_232.0-v3v4-341f-806r-nb-classifier.qza \
  classifiers-gtdb-232.0
```

The script creates the release when necessary, uploads the original `.qza` plus its checksum file,
and prints an exact download command containing the computed digest. It deliberately refuses to
replace an asset with the same name. Use a new release tag for a changed classifier so published
scientific inputs remain immutable.

The optional third argument selects another repository:

```bash
bash scripts/publish-classifier-release.sh CLASSIFIER.qza TAG OWNER/REPOSITORY
```

## Download reproducibly

Copy the command printed by the publication script. Its form is:

```bash
bash scripts/download-classifier.sh \
  OWNER/REPOSITORY \
  RELEASE_TAG \
  CLASSIFIER.qza \
  EXPECTED_SHA256
```

The default destination is `classifiers/CLASSIFIER.qza`. A fifth argument overrides it:

```bash
bash scripts/download-classifier.sh \
  OWNER/REPOSITORY RELEASE_TAG CLASSIFIER.qza EXPECTED_SHA256 \
  /mnt/data/qiime2-classifiers/CLASSIFIER.qza
```

The download is written to a temporary file in the destination directory, verified, and renamed
atomically. An existing verified file is reused; an existing file with another digest is never
overwritten.

## Record in experiment configuration

Reference the downloaded path in the experiment YAML:

```yaml
taxonomy:
  classifier_file: classifiers/16S_GTDB_232.0-v3v4-341f-806r-nb-classifier.qza
```

Record the release tag, source URL, byte size, SHA-256 digest, database version, amplified region,
primers, QIIME 2 version, and training command in the scientific provenance. The checksum must be
copied into version-controlled configuration or documentation; fetching a checksum dynamically
from the same release does not pin the input.

## Release naming

Recommended conventions:

- release tag: `classifiers-<database>-<database-version>`;
- asset: preserve the descriptive classifier filename;
- changed bytes: publish a new tag rather than replacing the existing asset.

For this artifact, the suggested tag is `classifiers-gtdb-232.0`.
