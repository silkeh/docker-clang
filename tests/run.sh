#!/usr/bin/env bash
set -eou pipefail

cd "$(realpath "$(dirname "$0")")"

# Show version
clang --version

# Compile C
clang test.c -o test && ./test

# Compile C++
clang++ test.cpp -o test && ./test
