#!/usr/bin/env bash
set -eou pipefail

REPO="silkeh/clang"

# Build images
for f in *.Dockerfile; do
  docker build . -f "$f" -t "${REPO}:$(basename "$f" .Dockerfile)"
done
