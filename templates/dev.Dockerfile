FROM debian:{debian_version}-slim as intermediate

# Install dependencies
RUN apt-get -qq update; \
    apt-get install -qqy --no-install-recommends \
        gnupg2 wget ca-certificates apt-transport-https \
        autoconf automake cmake dpkg-dev file make patch libc6-dev

# Set repository key
RUN wget -nv -O - https://apt.llvm.org/llvm-snapshot.gpg.key | apt-key add -

# Install
RUN echo "deb http://apt.llvm.org/{debian_version}/ llvm-toolchain-{debian_version} main" \
        > /etc/apt/sources.list.d/llvm.list; \
    apt-get -qq update && \
    apt-get install -qqy -t llvm-toolchain-{debian_version} {packages} && \
    for f in /usr/lib/llvm-{version}/bin/*; do ln -sf "$f" /usr/bin; done && \
    rm -rf /var/lib/apt/lists/*

FROM intermediate as test

COPY tests /tests

RUN /tests/run.sh {version}

FROM intermediate as final
