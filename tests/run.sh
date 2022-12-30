#!/usr/bin/env bash
set -eou pipefail

cd "$(realpath "$(dirname "$0")")"

version="$1"

# Show version
clang --version

# Check version
exp_version="clang version ${version}"
cur_version="$(clang --version | grep -Po 'clang version .*')"

if [[ "$1" != "dev" ]] && [[ "${cur_version}" != "${exp_version}"* ]]
then
    echo "Incorrect version: ${cur_version}"
    echo "Expected: ${exp_version}"
    exit 1
fi

# Compile C
clang test.c -o test
./test

# Compile C++
clang++ test.cpp -o test
./test

if grep -q 'Debian GNU/Linux 1' /etc/issue
then
    echo "Testing LTO"
    clang++ test.cpp -o test -flto=thin
    ./test
fi
