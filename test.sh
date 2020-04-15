#!/usr/bin/env bash
set -eou pipefail

REPO="silkeh/clang"

_run() {
    docker run -v "$PWD/tests:/tests" -it "$@"
}

# Show versions
for f in *.Dockerfile; do
  img="${REPO}:$(basename "$f" .Dockerfile)"
  echo "Image ${img}:"

  # Show version
  _run "${img}" clang --version

  # Compile C
  _run "${img}" clang /tests/test.c -o test

  # Compile C++
  _run "${img}" clang++ tests/test.cpp -o test

  echo
done
