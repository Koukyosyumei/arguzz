# sphinx-fuzzer

Arguzz front-end targeting the [Sphinx](https://github.com/argumentcomputer/sphinx) zkVM
(an Argument Computer fork of the Succinct SP1 zkVM).

## Layout

This crate mirrors the layout of `sp1-fuzzer`, retargeted at Sphinx:

- The Sphinx executor lives in `core/src/runtime/mod.rs` (vs. SP1's
  `crates/core/executor/src/executor.rs`).
- The host SDK is `sphinx-sdk` at `sdk/`.
- The guest entrypoint is `sphinx-zkvm` at `zkvm/entrypoint/`.
- Build helpers come from `sphinx-helper` at `helper/` (with `build_program(path)`
  rather than SP1's `build_program_with_args`).

## Usage

Containerized (mirrors the other fuzzers):

```bash
# install (builds the podman image, clones Sphinx, applies fault-injection patches)
./scripts/install.sh

# fuzz
./scripts/explore.sh
```

Or directly via the CLI:

```bash
sphinx-fuzzer install --zkvm ./sphinx --zkvm-modification \
    --commit-or-branch 8a39b951e3ea520e295b693ad38bff6b43a2630c
sphinx-fuzzer run --fault-injection -o output -z ./sphinx -l arguzz-x-sphinx.log -v2 \
    --commit-or-branch 8a39b951e3ea520e295b693ad38bff6b43a2630c
```
