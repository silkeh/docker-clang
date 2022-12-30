# Clang / LLVM docker containers
[![docker](https://img.shields.io/docker/pulls/silkeh/clang.svg)](https://hub.docker.com/r/silkeh/clang/)

A collection of images containing official Clang/LLVM releases.
All Docker images are generated in GitLab CI, and can be found [here][artifacts].

The `latest` tag contains the latest stable LLVM version on the latest stable Debian version.
The `dev` tag contains a nightly build of the unstable branch from <https://apt.llvm.org/>.

The versions and contents of the Debian packages are generated based on [config.yaml][],
in which new versions of LLVM and Debian can be added.

[config.yaml]: https://gitlab.com/silkeh/docker-clang/-/blob/master/config.yaml
[pipeline]: https://gitlab.com/silkeh/docker-clang/pipelines/master/latest
[artifacts]: https://gitlab.com/silkeh/docker-clang/-/jobs/artifacts/master/browse/dockerfiles?job=generate

