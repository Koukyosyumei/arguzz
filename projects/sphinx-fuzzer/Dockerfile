FROM debian:bookworm as sphinx

# run docker image in non interactive mode
ENV DEBIAN_FRONTEND noninteractive

# start from root directory
WORKDIR /root/

# install dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential ca-certificates clang cmake curl dialog gcc git \
    jq libgmp-dev libgrpc++-dev libomp-dev libsecp256k1-dev \
    libssl-dev libsodium-dev libpqxx-dev nasm nlohmann-json3-dev  \
    pkg-config protobuf-compiler python3 python3-pip qemu-system \
    ssh uuid-dev vim xz-utils && \
    rm -rf /var/lib/apt/lists/*

# install rust (stable host toolchain; sphinx pins its own via rust-toolchain.toml)
ARG RUST_VERSION="stable"
RUN curl --proto '=https' --retry 10 --retry-connrefused --tlsv1.2 -fsSL https://sh.rustup.rs | \
    bash -s -- -y --profile minimal --default-toolchain=${RUST_VERSION}
ENV PATH="/root/.cargo/bin:${PATH}"

# install sp1up — Sphinx is a fork of SP1 and reuses the
# `riscv32im-succinct-zkvm-elf` target / succinct toolchain.
RUN curl -L https://sp1up.succinct.xyz | bash
ENV PATH="/root/.sp1/bin:${PATH}"
RUN sp1up

# copy selective libraries and projects
COPY ./libs /root/zkvm-fuzzing/libs
COPY ./projects/sphinx-fuzzer /root/zkvm-fuzzing/projects/sphinx-fuzzer

# install project dependencies (system wide)
RUN cd zkvm-fuzzing/projects/sphinx-fuzzer/ && \
    python3 -m pip install -r requirements.txt --break-system-packages && \
    python3 -m pip install . --break-system-packages

# create and change directory to workspace
RUN mkdir -p /root/workspace
WORKDIR /root/workspace
