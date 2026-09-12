#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: bash scripts/publish-classifier-release.sh CLASSIFIER.qza RELEASE_TAG [OWNER/REPOSITORY]" >&2
}

[[ $# -ge 2 && $# -le 3 ]] || { usage; exit 2; }

artifact=$1
tag=$2
repository=${3:-}

[[ -f "$artifact" ]] || { echo "Classifier not found: $artifact" >&2; exit 1; }
[[ "$artifact" == *.qza ]] || { echo "Classifier must have the .qza extension" >&2; exit 1; }
command -v gh >/dev/null || { echo "GitHub CLI (gh) is required" >&2; exit 1; }
command -v sha256sum >/dev/null || { echo "sha256sum is required" >&2; exit 1; }

if [[ -z "$repository" ]]; then
  repository=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
fi

filename=$(basename "$artifact")
digest=$(sha256sum "$artifact" | awk '{print $1}')
size=$(stat --format='%s' "$artifact")
stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT
printf '%s  %s\n' "$digest" "$filename" > "$stage/$filename.sha256"

if gh release view "$tag" --repo "$repository" >/dev/null 2>&1; then
  echo "Using existing release: $tag"
else
  gh release create "$tag"     --repo "$repository"     --title "QIIME 2 classifiers ($tag)"     --notes "Versioned QIIME 2 classifier artifacts. Verify every download with the attached SHA-256 file."
fi

gh release upload "$tag"   "$artifact"   "$stage/$filename.sha256"   --repo "$repository"

printf '\nPublished %s (%s bytes)\nSHA-256: %s\n' "$filename" "$size" "$digest"
printf 'Download with:\n'
printf 'bash scripts/download-classifier.sh %q %q %q %q\n'   "$repository" "$tag" "$filename" "$digest"
