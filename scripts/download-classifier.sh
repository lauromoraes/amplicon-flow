#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: bash scripts/download-classifier.sh OWNER/REPOSITORY RELEASE_TAG ASSET.qza SHA256 [DESTINATION]" >&2
}

[[ $# -ge 4 && $# -le 5 ]] || { usage; exit 2; }

repository=$1
tag=$2
filename=$3
expected_sha256=${4,,}
destination=${5:-classifiers/$filename}

[[ "$repository" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] ||
  { echo "Invalid repository: $repository" >&2; exit 2; }
[[ "$filename" =~ ^[A-Za-z0-9._+-]+\.qza$ ]] ||
  { echo "Invalid classifier filename: $filename" >&2; exit 2; }
[[ "$expected_sha256" =~ ^[0-9a-f]{64}$ ]] ||
  { echo "SHA-256 must contain exactly 64 hexadecimal characters" >&2; exit 2; }

if [[ -e "$destination" ]]; then
  current_sha256=$(sha256sum "$destination" | awk '{print $1}')
  if [[ "$current_sha256" == "$expected_sha256" ]]; then
    echo "Classifier already present and verified: $destination"
    exit 0
  fi
  echo "Destination exists with a different checksum: $destination" >&2
  exit 1
fi

parent=$(dirname "$destination")
mkdir -p "$parent"
partial=$(mktemp "$parent/.classifier-download.XXXXXX")
trap 'rm -f -- "$partial"' EXIT
url="https://github.com/$repository/releases/download/$tag/$filename"

echo "Downloading $url"
if command -v curl >/dev/null; then
  curl --fail --location --retry 5 --retry-all-errors --output "$partial" "$url"
elif command -v wget >/dev/null; then
  wget --tries=5 --continue --output-document="$partial" "$url"
else
  echo "curl or wget is required" >&2
  exit 1
fi

actual_sha256=$(sha256sum "$partial" | awk '{print $1}')
if [[ "$actual_sha256" != "$expected_sha256" ]]; then
  echo "Checksum mismatch" >&2
  echo "Expected: $expected_sha256" >&2
  echo "Actual:   $actual_sha256" >&2
  exit 1
fi

mv -- "$partial" "$destination"
trap - EXIT
echo "Classifier downloaded and verified: $destination"
