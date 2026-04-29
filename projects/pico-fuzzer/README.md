# Arguzz Fuzzer for Pico

## Pico Resources
  - https://pico-docs.brevis.network/getting-started/quick-start
  - https://github.com/brevis-network/pico


```bash
pico-fuzzer install --zkvm ./pico --commit-or-branch e09f8d7c4132ac717935896fccf8a713b1fae418
pico-fuzzer run --fault-injection -o output -z ./pico -l arguzz-x-pico.log -v2
```
