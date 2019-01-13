#!/usr/bin/env bash
set -eou pipefail

# Versions using the old versioning scheme
OLD_VERSIONS="2.9 3.0 3.1 3.2 3.3 3.4.2 3.5.2 3.6.2 3.7.1 3.8.1 3.9.1"

# Versions using the new versioning scheme
NEW_VERSIONS="4.0.1 5.0.2 6.0.1 7.0.1"

# Create a Dockerfile from template
_create() {
  v="$1"
  r="$2"

  mkdir -p "${r}"
  cp -a "Dockerfile.template" "${r}/Dockerfile"
  cp -a "install.sh"          "${r}/install.sh"

  sed -i "s/{release}/$r/g" "${r}/Dockerfile"
  sed -i "s/{version}/$v/g" "${r}/Dockerfile"
}

# Get latest version
latest=$(<<< "${NEW_VERSIONS}" awk '{print $NF}')

# Create Dockerfiles for the old versions
for v in $OLD_VERSIONS; do
  rel=$(<<<$v grep -Po '[0-9]\.[0-9]')
  _create "$v" "${rel}"
done

# Create Dockerfiles for the new versions
for v in $NEW_VERSIONS; do
  rel=$(<<<$v cut -d. -f1)
  _create "$v" "${rel}"

  # Copy Dockerfile for latest version
  if [ "$v" == "$latest" ]; then
    cp "${rel}/Dockerfile" "./Dockerfile"
  fi
done
