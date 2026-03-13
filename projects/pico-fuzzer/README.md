# Arguzz Fuzzer for Pico

## Pico Resources
  - https://pico-docs.brevis.network/getting-started/quick-start
  - https://github.com/brevis-network/pico


```bash
pico-fuzzer install --zkvm ./pico --commit-or-branch latticevm
pico-fuzzer run --fault-injection -o output -z ./pico -l arguzz-x-pico.log -v2
```
