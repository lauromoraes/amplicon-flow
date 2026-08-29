# Development image

## Purpose and identity

The repository `Dockerfile` defines the development and scientific-integration image for
AmpliconFlow. It extends the official QIIME 2 workshop image for release 2026.7 and pins its
linux/amd64 digest, rather than following a mutable tag. This keeps QIIME 2, Rachis, DADA2, the
QIIME plugins, JupyterLab, and the base analytical stack aligned with the upstream distribution.

The workshop base already supplies JupyterLab and `biom-format`, plus pandas, SciPy,
scikit-learn, matplotlib, and seaborn. AmpliconFlow adds exact direct versions of Biopython,
Papermill, statannotations, pytest, and Ruff. `statannotations` is the PyPI distribution/import
name; it is the maintained package commonly intended by “statsannot”. Pip uses the default
`only-if-needed` upgrade strategy, so already compatible scientific packages from QIIME are kept
while genuinely missing dependencies are added. The build then runs `pip check`; any incompatible
environment fails explicitly. A smoke test imports the required libraries and confirms the QIIME
`demux` and `dada2` plugins. The image installs a complete package/repository snapshot while
`PYTHONPATH=/workspace/src` gives a bind-mounted checkout precedence during development.

## Build and verify

From the repository root:

```bash
docker build --tag ampliconflow-dev:qiime2-2026.7 .
docker run --rm ampliconflow-dev:qiime2-2026.7 \
  python /usr/local/bin/ampliconflow-image-smoke-test
```

The upstream image is approximately 3 GB compressed, so the first pull/build can take time and
substantial local storage. A base-image update is a reviewed dependency change: update both the
tag/digest and package compatibility evidence; never pass an unreviewed `latest` image.

## Interactive development

Linux/macOS shell syntax:

```bash
docker run --rm -it \
  --publish 127.0.0.1:8888:8888 \
  --mount type=bind,source="$PWD",target=/workspace \
  ampliconflow-dev:qiime2-2026.7
```

The inherited command starts JupyterLab. Binding only to `127.0.0.1` avoids exposing the
token-free upstream workshop server to the network.

Run the repository CLI or tests instead of JupyterLab by overriding the command:

```bash
docker run --rm -it \
  --mount type=bind,source="$PWD",target=/workspace \
  ampliconflow-dev:qiime2-2026.7 \
  python -m pytest -q
```

Mount datasets separately and read-only where possible. Do not bake reference datasets,
experiment inputs, `.qza` artifacts, credentials, or sensitive metadata into the image. Docker
build context exclusions do not change Git policy: the project still has no extension-based Git
restriction for `.qza` files.

## Current host prerequisite

Docker commands require access to the daemon socket. On WSL, verify that Docker Desktop WSL
integration is enabled for the active distribution, or configure a native daemon and ensure the
current user has legitimate socket access. Do not work around the problem by making the socket
world-writable. After daemon access is restored, build the image and run Prepare Data against the
pinned reference datasets before claiming scientific acceptance.
