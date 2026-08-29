# syntax=docker/dockerfile:1.7

# QIIME 2 2026.7 workshop image, linux/amd64, resolved on 2026-08-29.
# Override only for an explicit, reviewed base-image update.
ARG QIIME2_BASE_IMAGE=quay.io/qiime2/qiime2-workshop:2026.7@sha256:c901a44adc49201efa78076977bf4cfb845768913f59d5a2cb7883b7e6ec0362
FROM ${QIIME2_BASE_IMAGE}

LABEL org.opencontainers.image.title="AmpliconFlow development environment" \
      org.opencontainers.image.description="QIIME 2 2026.7 workshop plus AmpliconFlow development dependencies" \
      org.opencontainers.image.source="https://github.com/lauromoraes/amplicon-flow" \
      org.opencontainers.image.licenses="MIT"

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/workspace/src

# PATH in the upstream image already targets the rachis-qiime2-2026.7 Conda
# environment. Use python -m pip so additions cannot land in another Python.
COPY docker/requirements-development.txt /tmp/ampliconflow/requirements-development.txt
RUN python -m pip install --upgrade-strategy only-if-needed \
        --requirement /tmp/ampliconflow/requirements-development.txt \
    && python -m pip check

# Install a complete snapshot so repository-relative schemas, notebooks, and
# registries remain usable without a bind mount. Live /workspace/src code takes
# precedence through PYTHONPATH during development.
COPY pyproject.toml README.md LICENSE ampliconflow /opt/ampliconflow/
COPY src /opt/ampliconflow/src
COPY schemas /opt/ampliconflow/schemas
COPY validation /opt/ampliconflow/validation
COPY notebooks /opt/ampliconflow/notebooks
COPY examples /opt/ampliconflow/examples
RUN python -m pip install --no-deps --editable /opt/ampliconflow

COPY docker/smoke_test.py /usr/local/bin/ampliconflow-image-smoke-test
RUN python /usr/local/bin/ampliconflow-image-smoke-test

WORKDIR /workspace

# Retain the upstream workshop CMD, which launches JupyterLab on port 8888.
EXPOSE 8888
