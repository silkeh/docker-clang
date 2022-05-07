#!/usr/bin/env bash
set -eou pipefail

REPO="silkeh/clang"

# Show versions
for f in *.Dockerfile; do
  img="${REPO}:$(basename "$f" .Dockerfile)"
  echo "Image ${img}:"

  docker run -v "$PWD:/build" -it "${img}" /build/tests/run.sh

  echo
done
